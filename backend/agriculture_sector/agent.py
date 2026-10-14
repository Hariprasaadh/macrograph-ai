"""Agriculture reasoning over MCP evidence, with deterministic domain routing."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import httpx

from core.protocols.mcp.client import MCPClientWrapper
from core.config import settings
from .mcp_server import mcp_server
from .models import AgricultureFinding, AgricultureObservation, AgricultureQuery, AgricultureResult, SourceError, WeatherObservation

logger = logging.getLogger(__name__)

_SERVICE_KEYWORDS = {
    "get_crop_production": ("crop production", "foodgrain production", "crop output"),
    "get_crop_yield": ("yield",), "get_crop_area": ("area", "sowing", "acreage"),
    "get_production_trend": ("production changed", "output weakened"),
    "get_state_crop_production": ("which states", "highest", "most rice"),
    "get_mandi_price": ("price", "prices", "mandi", "agmarket", "agmarknet", "agri market",
                         "agricultural market", "mandi api", "wholesale", "rate", "cost"),
    "get_mandi_price_trend": ("prices changed", "prices increasing", "price trend", "price surge", "mandi trend"),
    "compare_mandi_prices": ("compare markets", "cross-market", "cheapest", "cheapest mandi"),
    "get_market_arrivals": ("arrivals", "arrival"), "get_msp": ("msp", "minimum support price"),
    "get_msp_history": ("msp history", "historical msp"),
    "get_msp_gap": ("above msp", "below msp", "versus msp", "msp-price gap"),
    "get_rainfall": ("rainfall", "rain"), "get_rainfall_anomaly": ("normal", "deficien", "anomaly"),
    "get_monsoon_status": ("monsoon",), "get_weather_history": ("weather history", "historical rainfall"),
    "get_fertilizer_consumption": ("fertilizer", "fertiliser"),
    "get_irrigation_area": ("irrigation",), "get_agriculture_scheme": ("scheme", "policy"),
}
_CROP_TERMS = (
    "wheat", "rice", "paddy", "onion", "tomato", "potato", "cotton", "maize",
    "sugarcane", "soybean", "pulses", "gram", "mustard", "garlic", "ginger",
    "chilli", "turmeric", "ragi", "millet", "jowar", "bajra",
)

_WEATHER_TERMS = (
    "weather", "rainfall", "rain", "temperature", "humidity", "wind", "precipitation",
    "soil moisture", "soil temperature", "evapotranspiration", "et0", "forecast",
)
_HISTORICAL_WEATHER_TERMS = (
    "yesterday", "last week", "previous week", "last month", "previous month",
    "past ", "historical", "weather history", "this month", "this week",
)
_WEATHER_LOCATION_STOP_WORDS = (
    " yesterday", " today", " tomorrow", " last week", " previous week", " this week",
    " last month", " previous month", " this month", " past ", " forecast", " during ",
)


def _is_weather_query(query: str) -> bool:
    q = query.casefold()
    return any(term in q for term in _WEATHER_TERMS)


def _is_rainfall_only(query: str) -> bool:
    q = query.casefold()
    return any(term in q for term in ("rainfall", "precipitation")) and not any(
        term in q for term in ("temperature", "wind", "humidity", "et0", "evapotranspiration"))


def _resolve_weather_dates(query: str, today: date | None = None) -> tuple[date, date] | None:
    q = query.casefold()
    current = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if "yesterday" in q:
        day = current - timedelta(days=1)
        return day, day
    if "last week" in q or "previous week" in q:
        return current - timedelta(days=7), current - timedelta(days=1)
    if "this week" in q:
        return current - timedelta(days=current.weekday()), current
    if "last month" in q or "previous month" in q:
        first = current.replace(day=1)
        end = first - timedelta(days=1)
        return end.replace(day=1), end
    if "this month" in q:
        return current.replace(day=1), current
    match = re.search(r"(?:past|last)\s+(\d+)\s+days?", q)
    if match:
        return current - timedelta(days=int(match[1])), current - timedelta(days=1)
    if "today" in q:
        return current, current
    return None


def _extract_weather_location(query: str) -> str | None:
    """Extract the user-supplied place without substituting a default region."""
    text = query.strip().rstrip("?.!")
    match = re.search(r"\bweather\s+(?:forecast\s+)?(?:in|for)\s+(.+)$", text, re.IGNORECASE)
    if not match:
        match = re.search(r"^(.+?)\s+weather(?:\s+forecast)?(?:\s+.*)?$", text, re.IGNORECASE)
    if not match:
        match = re.search(r"\b(?:rainfall|rain|temperature|humidity|wind)\s+(?:in|for)\s+(.+)$", text, re.IGNORECASE)
    if not match:
        return None
    location = match.group(1).strip(" ,")
    location = re.split(
        r"\s+(?:for|during|over)\s+(?:the\s+)?(?:last|past)\s+\d+\s+days?\b",
        location, maxsplit=1, flags=re.IGNORECASE,
    )[0].strip(" ,")
    lowered = location.casefold()
    for stop in _WEATHER_LOCATION_STOP_WORDS:
        index = lowered.find(stop)
        if index >= 0:
            location = location[:index].strip(" ,")
            lowered = location.casefold()
    return location or None


def _extract_crop_name(query: str) -> str | None:
    text = query.strip().rstrip("?.!")
    match = re.search(
        r"\bproduction(?:\s+trend)?\s+(?:of|for)\s+(.+?)(?:\s+(?:in|from|over|for)\b|$)",
        text, re.IGNORECASE,
    )
    if not match:
        # Strip request wording so it cannot become part of the crop filter.
        text = re.sub(
            r"^(?:(?:show|give|display|find|list|what\s+is|how\s+(?:has|have|did))\s+)+"
            r"(?:me\s+)?(?:(?:the|available|historical|latest|annual|all|retrieved)\s+)*",
            "", text, flags=re.IGNORECASE,
        )
        match = re.search(r"^(.+?)\s+production\b", text, re.IGNORECASE)
    if not match:
        return None
    crop = match.group(1).strip(" ,")
    crop = re.sub(r"^(?:latest|historical|annual|the)\s+", "", crop, flags=re.IGNORECASE)
    crop = re.sub(r"\s+(?:trend|history)$", "", crop, flags=re.IGNORECASE).strip()
    if crop.casefold() in {"major crops", "crops", "all crops", "crop"}:
        return None
    return crop.title()


def _is_crop_data_query(query: str) -> bool:
    """Recognize crop-data requests even when users omit the word production."""
    q = query.casefold()
    if "production" in q or "crop output" in q:
        return True
    crop_mentioned = any(re.search(r"\b" + re.escape(crop) + r"s?\b", q) for crop in _CROP_TERMS)
    data_wording = any(term in q for term in ("data", "figure", "observation", "record", "latest", "available"))
    other_indicator = any(term in q for term in ("price", "yield", "area", "rain", "weather", "msp"))
    return crop_mentioned and data_wording and not other_indicator


def _extract_history_years(query: str) -> int | None:
    match = re.search(r"(?:last|past|over the last)\s+(\d+)\s+y(?:ears?|eras?)", query.casefold())
    return int(match[1]) if match else None


def _extract_production_years(query: str) -> tuple[int, int] | None:
    match = re.search(
        r"(?:from\s+|between\s+)?(\d{4})(?:-\d{2})?\s+(?:to|through|and)\s+(\d{4})(?:-\d{2})?",
        query.casefold(),
    )
    if match:
        return int(match[1]), int(match[2])
    match = re.search(r"\b(\d{4})\s*[-–]\s*(\d{4})\b", query)
    if match:
        return int(match[1]), int(match[2])
    return None


def select_agriculture_tools(query: str) -> set[str]:
    q = query.casefold()
    # Pure out-of-domain requests never trigger agriculture data fetches.
    excluded = ("cpi", "wpi", "gdp", "gva", "repo", "bank credit", "nifty", "sensex", "trade balance", "fiscal deficit")
    agricultural_context = any(word in q for word in (
        "agmarket", "agmarknet", "agri market", "agriculture api", "agricultural market",
        "crop", "mandi", "wheat", "rice", "onion", "tomato", "potato", "vegetable",
        "rainfall", "agriculture", "msp", "supply"))
    if any(word in q for word in excluded) and not agricultural_context:
        return set()
    if any(term in q for term in ("rainfall", "rain")) and any(
        term in q for term in ("normal", "deficien", "anomaly")) and _resolve_weather_dates(query) is None:
        return {"get_rainfall_anomaly"}
    if _is_weather_query(query):
        historical = _resolve_weather_dates(query) is not None or any(
            term in q for term in _HISTORICAL_WEATHER_TERMS)
        forecast = "forecast" in q or any(term in q for term in ("tomorrow", "next week", "next month"))
        if forecast and not historical:
            return {"get_weather_forecast"}
        if historical:
            return {"get_historical_weather"}
        return {"get_current_weather"}
    if (re.search(r"\b(?:list|show)\b.*\b(?:available\s+)?crops?\b", q)
            or re.search(r"\bwhat\s+are\b.*\b(?:available\s+)?crops?\b", q)) and "production" not in q:
        return {"get_crop_list"}
    crop = _extract_crop_name(query)
    known_crop = any(re.search(r"\b" + re.escape(term) + r"s?\b", q) for term in _CROP_TERMS)
    production_intent = _is_crop_data_query(query)
    if production_intent and (crop or known_crop or "crop" in q or "crops" in q):
        if any(term in q for term in ("changed", "change", "trend", "historical", "history", "from ")) or _extract_history_years(query):
            return {"get_production_trend"}
        return {"get_crop_production"}
    selected = {tool for tool, words in _SERVICE_KEYWORDS.items() if any(word in q for word in words)}
    if any(w in q for w in ("agmarket", "agmarknet")):
        selected.add("get_mandi_price")
    if "msp" in q or "minimum support price" in q:
        selected.discard("get_mandi_price")
        if any(word in q for word in ("above", "below", "versus", "gap", "compare")):
            selected.add("get_msp_gap")
        if any(word in q for word in ("history", "historical", "changed")):
            selected.add("get_msp_history")
    if any(word in q for word in ("production", "output")) and any(word in q for word in ("chang", "trend", "weaken", "growth")):
        selected.add("get_production_trend")
    if any(word in q for word in (
        "wheat", "rice", "paddy", "onion", "tomato", "potato", "cotton", "maize",
        "sugarcane", "soybean", "pulses", "gram", "mustard", "garlic", "ginger",
        "chilli", "turmeric")) and any(word in q for word in ("production", "output")):
        selected.add("get_crop_production")
    if any(word in q for word in ("price", "mandi")) and "msp" not in q and any(word in q for word in ("chang", "trend", "increas", "ris", "last")):
        selected.add("get_mandi_price_trend")
    if ("why" in q and any(word in q for word in ("price", "supply"))) or "supply-side" in q:
        selected.update({"get_mandi_price_trend", "get_market_arrivals", "get_crop_production", "get_rainfall_anomaly"})
    if "get_rainfall_anomaly" in selected and not any(word in q for word in ("rain", "monsoon", "supply", "why")):
        selected.remove("get_rainfall_anomaly")
    for rich, basic in (("get_production_trend", "get_crop_production"), ("get_state_crop_production", "get_crop_production"),
                        ("get_mandi_price_trend", "get_mandi_price"), ("get_msp_history", "get_msp"),
                        ("get_msp_gap", "get_msp"), ("get_rainfall_anomaly", "get_rainfall"),
                        ("get_weather_history", "get_rainfall")):
        if rich in selected:
            selected.discard(basic)
    if not selected and any(word in q for word in ("agricultur", "crop", "foodgrain", "supply")):
        selected.update({"get_crop_production", "get_rainfall", "get_mandi_price"})
    return selected


def query_parameters(query: str, parameters: dict[str, Any] | None = None) -> AgricultureQuery:
    """Use explicit parameters first; infer only entity names literally present in text."""
    parameters = {k: v for k, v in (parameters or {}).items() if k in AgricultureQuery.model_fields}
    q = query.casefold()
    crop_names = _CROP_TERMS
    crop = next((name.title() for name in crop_names if re.search(r"\b" + name + r"s?\b", q)), None)
    crop = crop or _extract_crop_name(query)
    if crop:
        parameters.setdefault("crop", crop)
        parameters.setdefault("commodity", crop)
    history_years = _extract_history_years(query)
    if history_years:
        parameters.setdefault("history_years", history_years)
    year_range = _extract_production_years(query)
    if year_range:
        parameters.setdefault("start_year", year_range[0])
        parameters.setdefault("end_year", year_range[1])
    elif not history_years:
        explicit_years = re.findall(r"\b((?:19|20)\d{2})\b", query)
        if len(explicit_years) == 1:
            parameters.setdefault("period", explicit_years[0])
    if _is_crop_data_query(query):
        parameters.setdefault("intent", "crop_production_history" if history_years or any(
            term in q for term in ("historical", "trend", "history", "from ")) else "crop_production")
    states = ("Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
              "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
              "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
              "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
              "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi")
    for state in states:
        if state.casefold() in q:
            parameters.setdefault("state", state)
            break
    district = re.search(
        r"\b(?:district(?:\s+of)?|for)\s+([A-Z][A-Za-z .'-]*?)\s+in\s+((?:19|20)\d{2})\b",
        query,
    )
    if district:
        parameters.setdefault("district", district[1].strip())
    if "state" not in parameters:
        for alias, state in (("tamilnadu", "Tamil Nadu"), ("tn", "Tamil Nadu")):
            if re.search(r"\b" + alias + r"\b", q):
                parameters.setdefault("state", state)
                break
    if "state" not in parameters and "district" not in parameters:
        place_match = re.search(r"\b(?:in|at)\s+([A-Za-z][A-Za-z .'-]*?)\s*[?.!]*$", query, re.IGNORECASE)
        if place_match:
            place = place_match.group(1).strip().title()
            if place.casefold() not in {"india", "the country", "the state"} and not re.fullmatch(r"\d{4}", place):
                parameters.setdefault("district", place)
    city_states = {
        "Mumbai": "Maharashtra", "Delhi": "Delhi", "Bangalore": "Karnataka",
        "Bengaluru": "Karnataka", "Chennai": "Tamil Nadu", "Kolkata": "West Bengal",
        "Hyderabad": "Telangana", "Pune": "Maharashtra", "Ahmedabad": "Gujarat",
        "Jaipur": "Rajasthan", "Surat": "Gujarat", "Nashik": "Maharashtra",
    }
    for city, city_state in city_states.items():
        if re.search(r"\b" + city.casefold() + r"\b", q):
            parameters.setdefault("city", city)
            if any(word in q for word in ("mandi", "market", "price", "arrival")):
                parameters.setdefault("district", city)
                parameters.setdefault("state", city_state)
            break
    if _is_weather_query(query):
        if _is_rainfall_only(query):
            parameters.setdefault("intent", "rainfall_only")
        location = _extract_weather_location(query)
        if location:
            parameters.setdefault("location", location)
        period = _resolve_weather_dates(query)
        if period:
            parameters.setdefault("start_date", period[0])
            parameters.setdefault("end_date", period[1])
    days = re.search(r"(?:last|past)\s+(\d+)\s+days?", q)
    if days:
        parameters.setdefault("days", int(days[1]))
    if "forecast" in q or "tomorrow" in q or "next week" in q:
        coming = re.search(r"next\s+(\d+)\s+days?", q)
        if coming:
            parameters.setdefault("days", int(coming[1]))
        elif "tomorrow" in q:
            parameters.setdefault("days", 2)
        elif "next week" in q:
            parameters.setdefault("days", 8)
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", query)
    if len(dates) == 1:
        parameters.setdefault("period", dates[0])
    elif len(dates) >= 2:
        parameters.setdefault("start_date", dates[0])
        parameters.setdefault("end_date", dates[1])
    return AgricultureQuery.model_validate(parameters)


def _citation(record: Any) -> dict[str, Any]:
    if isinstance(record, AgricultureObservation):
        return record.citation()
    return {**record.model_dump(mode="json"), "source_authority": record.source,
            "retrieval_url": record.source_url, "document_title": record.dataset,
            "table_reference": record.dataset, "observation_period": record.period,
            "fetched_at": record.retrieved_at.isoformat()}


def _scope_label(record: Any) -> str:
    values = (
        getattr(record, "crop", None) or getattr(record, "commodity", None),
        getattr(record, "state", None), getattr(record, "district", None),
        getattr(record, "season", None),
        getattr(record, "market", None), getattr(record, "city", None),
        getattr(record, "fertilizer", None), getattr(record, "measure", None),
        getattr(record, "irrigation_source", None),
        getattr(record, "location", None),
    )
    return " / ".join(str(value) for value in values if value) or "Reported scope"


def _number(value: float) -> str:
    """Readable display precision; canonical values remain unrounded in evidence."""
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _production_year_window(query: str | None = None) -> tuple[int, int]:
    """Keep production answers within the current year and preceding six years."""
    current_year = datetime.now(ZoneInfo("Asia/Kolkata")).year
    default_min = current_year - 6
    if query:
        year_range = _extract_production_years(query)
        if year_range:
            return max(default_min, year_range[0]), min(current_year, year_range[1])
        history_years = _extract_history_years(query)
        if history_years:
            return max(default_min, current_year - history_years + 1), current_year
    return default_min, current_year


def _table_cell(value: Any) -> str:
    """Keep source-provided labels from breaking Markdown tables or links."""
    return re.sub(r"\s+", " ", str(value)).replace("|", "\\|").strip()


def _window_change(result: AgricultureResult, latest: AgricultureObservation) -> dict[str, Any] | None:
    """Compare the first and last compatible records for a trend headline."""
    if result.tool not in {"get_production_trend", "get_mandi_price_trend", "get_msp_history"}:
        return None
    keys = ("kind", "crop", "commodity", "state", "district", "market", "variety", "grade",
            "season", "unit", "frequency", "dataset", "source")
    compatible = [record for record in result.records if isinstance(record, AgricultureObservation)
                  and all(getattr(record, key, None) == getattr(latest, key, None) for key in keys)]
    if len(compatible) < 2:
        return None
    first = min(compatible, key=lambda record: record.period)
    last = max(compatible, key=lambda record: record.period)
    if first.period == last.period:
        return None
    delta = last.value - first.value
    percent = delta / first.value * 100 if first.value else None
    return {
        "indicator": "window_change", "value": delta, "unit": last.unit,
        "percentage_change": percent, "from_period": first.period, "period": last.period,
        "evidence": [first.citation(), last.citation()],
    }


def _production_tavily_rows(query: str, web_results: list[dict[str, str]]) -> list[dict[str, str]]:
    """Extract dated production figures and label whether the excerpt matches the requested place."""
    scope = query_parameters(query)
    requested_year = scope.period if scope.period and re.fullmatch(r"\d{4}", scope.period) else None
    min_year, max_year = _production_year_window(query)
    if requested_year and not min_year <= int(requested_year) <= max_year:
        return []
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    quantity = re.compile(
        r"(?<![\w.])([\d,]+(?:\.\d+)?)\s*(million(?:\s+metric)?\s+tonnes?|"
        r"lakh(?:\s+metric)?\s+tonnes?|thousand\s+tonnes?|crore\s+tonnes?|"
        r"million\s+bales?|lakh\s+bales?|thousand\s+bales?|000\s+bales?|"
        r"lmt|mmt|mt|tonnes?|tons?|bales?)\b",
        re.IGNORECASE,
    )
    year_pattern = re.compile(r"\b((?:19|20)\d{2}(?:[-/](?:\d{2}|20\d{2}))?)\b")
    crop_pattern = re.compile(
        r"\b(rice|paddy|wheat|ragi|millet|jowar|bajra|maize|corn|sugarcane|cotton|"
        r"soybean|mustard|onion|tomato|potato|gram|chickpea|lentil|turmeric|chilli|garlic)\b",
        re.IGNORECASE,
    )

    def is_request_scope(sentence: str, title: str = "", url: str = "") -> bool:
        lowered_sentence = sentence.casefold()
        lowered_title = title.casefold()
        if scope.district:
            place = re.escape(scope.district.casefold())
            title_supports_scope = bool(re.search(rf"\b{place}\b", lowered_title)
                                        and re.search(r"\b(?:production|produced|output|harvest)\b", lowered_title)
                                        and any(term in lowered_title for term in crop_terms))
            return bool(re.search(rf"\b{place}\b", lowered_sentence) or title_supports_scope)
        if scope.state:
            state = re.escape(scope.state.casefold())
            title_supports_scope = bool(re.search(rf"\b{state}\b", lowered_title)
                                        and re.search(r"\b(?:production|produced|output|harvest)\b", lowered_title)
                                        and any(term in lowered_title for term in crop_terms))
            return bool(re.search(rf"\b{state}\b", lowered_sentence) or title_supports_scope)
        return True

    for item in web_results:
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        excerpt = str(item.get("excerpt") or "")
        text = f"{title}. {excerpt}"
        lowered = text.casefold()
        crop_terms = {scope.crop.casefold()} if scope.crop else set()
        if scope.crop and scope.crop.casefold() == "rice":
            crop_terms.update({"paddy"})
        if crop_terms and not any(term in lowered for term in crop_terms):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
            if not any(term in sentence.casefold() for term in crop_terms):
                continue
            if not re.search(r"\bproduction\b|\bproduced\b|\boutput\b|\bharvest\b", sentence, re.IGNORECASE):
                continue
            sentence_lower = sentence.casefold()
            if re.search(r"\b(?:sold|sale|allocated|allocation|procured|purchased|exported|imported|"
                         r"consumed|consumption|stock|e-auction|distilleries|ethanol|milled rice)\b",
                         sentence_lower):
                continue
            season_match = re.search(r"\b(kharif|rabi|zaid|summer|winter)\b", sentence, re.IGNORECASE)
            district_match = re.search(r"\bdistrict\s+(?:of\s+)?([A-Z][A-Za-z .'-]+)", sentence)
            reported_district = (scope.district if scope.district and is_request_scope(sentence, title, url)
                                 else district_match[1].strip(" .,;") if district_match else "Not stated")
            is_official = any(domain in url.casefold() for domain in (
                "pib.gov.in", "agricoop.nic.in", "desagri.gov.in", "data.gov.in", "mospi.gov.in"))
            years = list(year_pattern.finditer(sentence))
            production_years = [year for year in years if "-" in year.group(1) or "/" in year.group(1)] or years
            crop_mentions = list(crop_pattern.finditer(sentence))
            quantity_matches = list(quantity.finditer(sentence))
            year_assignments: dict[int, list[re.Match[str]]] = {}
            for year_match in production_years:
                nearest_index = min(
                    range(len(quantity_matches)),
                    key=lambda index: max(quantity_matches[index].start() - year_match.end(),
                                          year_match.start() - quantity_matches[index].end(), 0),
                ) if quantity_matches else None
                if nearest_index is not None:
                    year_assignments.setdefault(nearest_index, []).append(year_match)
            for match_index, match in enumerate(quantity_matches):
                if crop_mentions:
                    nearest_crop = min(crop_mentions, key=lambda crop_match: min(
                        abs(match.start() - crop_match.end()), abs(crop_match.start() - match.end())))
                    if nearest_crop.group(1).casefold() not in crop_terms:
                        continue
                assigned_years = year_assignments.get(match_index, [])
                if not assigned_years:
                    continue
                closest_year = min(assigned_years, key=lambda year: min(
                    abs(match.start() - year.end()), abs(year.start() - match.end())))
                row_period = closest_year.group(1)
                row_year = int(row_period[:4])
                period_end = row_year
                if len(row_period) > 4:
                    suffix = row_period[5:]
                    period_end = int(str(row_year)[:2] + suffix) if len(suffix) == 2 else int(suffix)
                if (not min_year <= row_year <= max_year or period_end > max_year
                        or (requested_year and row_year != int(requested_year))):
                    continue
                before_quantity = sentence[max(0, match.start() - 36):match.start()].casefold()
                if re.search(r"\b(?:increase|increase of|increased by|rise of|higher by|decrease of|"
                             r"decreased by|lower by)\s*$", before_quantity):
                    continue
                yearless_scope_match = is_request_scope(sentence, title, url)
                geography_label = ", ".join(value for value in (scope.district, scope.state) if value) \
                    or "Geography not stated in the excerpt"
                if not yearless_scope_match:
                    combined_scope = f"{sentence} {title} {url}".casefold()
                    source_state = next((state for state in (
                        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
                        "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
                        "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
                        "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
                        "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi")
                        if re.search(rf"\b{re.escape(state.casefold())}\b", combined_scope)), None)
                    if source_state and scope.district:
                        geography_label = f"{source_state}-wide context; not specific to the requested district"
                    elif re.search(r"\bindia\b|\bnational(?:ly)?\b|\ball-india\b", combined_scope):
                        geography_label = "India-wide context; not specific to the requested area"
                    else:
                        geography_label = "Broader source context; not specific to the requested area"
                unit = re.sub(r"\s+", " ", match.group(2)).strip()
                indicator = ("Organic cotton production" if scope.crop and scope.crop.casefold() == "cotton"
                             and re.search(r"\borganic\b", sentence[max(0, match.start() - 80):match.start()],
                                           re.IGNORECASE)
                             else "Crop production")
                dedupe_key = (url, row_period, match.group(1), unit, geography_label, indicator)
                if dedupe_key in seen:
                    continue
                label = ("Published official forecast" if is_official and re.search(
                    r"\bforecast\b|\bforecasted\b", sentence_lower) else
                    "Published forecast" if re.search(r"\bforecast\b|\bforecasted\b", sentence_lower) else
                    "Published official estimate" if is_official else "Published source claim")
                rows.append({"title": title or url, "url": url, "published_date": item.get("published_date", ""),
                             "year": row_period, "indicator": indicator,
                             "year_start": str(row_year), "value": match.group(1), "unit": unit,
                             "excerpt": sentence.strip(), "district": reported_district,
                             "season": season_match[1].title() if season_match else "Not stated",
                             "geography": geography_label, "scope_match": yearless_scope_match,
                             "label": label})
                seen.add(dedupe_key)
    return rows


def _relevant_tavily_excerpts(query: str, web_results: list[dict[str, str]]) -> list[dict[str, str]]:
    scope = query_parameters(query)
    requested_year = scope.period if scope.period and re.fullmatch(r"\d{4}", scope.period) else None
    min_year, max_year = _production_year_window(query)
    relevant = []
    for item in web_results:
        excerpt = str(item.get("excerpt") or "")
        for sentence in re.split(r"(?<=[.!?])\s+|\n", excerpt):
            lowered = sentence.casefold()
            crop_present = not scope.crop or scope.crop.casefold() in lowered or (
                scope.crop.casefold() == "rice" and "paddy" in lowered)
            if not crop_present or not re.search(
                    r"\bproduction\b|\bproduced\b|\boutput\b|\bharvest\b|\byield\b", lowered):
                continue
            years = list(re.finditer(r"\b((?:19|20)\d{2})(?:[-/](?:\d{2}|20\d{2}))?\b", sentence))
            year_starts = [match.group(1) for match in years]
            matching_years = [year for year in year_starts if min_year <= int(year) <= max_year
                              and (not requested_year or year == requested_year)]
            all_years_in_range = all(min_year <= int(year) <= max_year for year in year_starts)
            if matching_years and all_years_in_range:
                relevant.append(item | {"relevant_excerpt": sentence.strip(),
                                         "relevant_year": matching_years[0]})
                break
    return relevant


def _production_report(query: str, results: list[AgricultureResult],
                       web_results: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    scope = query_parameters(query)
    min_year, max_year = _production_year_window(query)
    requested_year = scope.period if scope.period and re.fullmatch(r"\d{4}", scope.period) else None
    trend_query = bool(re.search(r"\b(trend|historical|history|changed|change over time)\b", query, re.IGNORECASE))
    latest_query = not requested_year and not trend_query
    structured = [record for result in results for record in result.records
                  if result.tool in {"get_crop_production", "get_production_trend"}
                  and isinstance(record, AgricultureObservation)]
    structured = [record for record in structured
                  if re.match(r"\d{4}", record.period)
                  and min_year <= int(record.period[:4]) <= max_year]
    if requested_year:
        structured = [record for record in structured if record.period.startswith(requested_year)]
    structured.sort(key=lambda record: record.period, reverse=True)
    published = _production_tavily_rows(query, web_results)
    published.sort(key=lambda row: (
        bool(row.get("scope_match")), int(row.get("year_start", "0")),
        str(row.get("published_date") or ""),
    ), reverse=True)
    related_excerpts = _relevant_tavily_excerpts(query, web_results)
    published_for_scope = [row for row in published if row.get("scope_match")]
    broader_published = [row for row in published if not row.get("scope_match")]
    published_years = [int(row.get("year_start", row["year"])) for row in published]
    structured_years = [int(record.period[:4]) for record in structured
                        if re.match(r"\d{4}", record.period)]
    government_is_old = bool(structured_years) and max(structured_years) < min_year
    publication_is_newer = bool(published_years and structured_years
                                and max(published_years) > max(structured_years))
    citations: list[dict[str, Any]] = []
    lines = ["## Agriculture diagnostic", ""]
    crop = scope.crop or (structured[0].crop if structured else "requested crop")
    geography = ", ".join(value for value in (scope.district, scope.state) if value) or "the geography stated by the sources"
    displayed_periods = sorted(set(record.period for record in structured)
                               | {row["year"] for row in published_for_scope})
    period = requested_year or (", ".join(displayed_periods) if displayed_periods else "the periods shown below")
    if latest_query and government_is_old and publication_is_newer:
        lines.append(f"**Answer:** The newest relevant published {crop} production figure found for {geography} "
                     f"is from {max(published_years)}; older structured observations are shown as historical context.")
    elif latest_query and government_is_old:
        lines.append(f"**Answer:** The structured records available for {crop} in {geography} are historical "
                     f"(latest returned year: {max(structured_years)}). No newer source-backed figure was found "
                     "in the retrieved publication excerpts.")
    elif structured or published_for_scope:
        lines.append(f"**Answer:** Available {crop} production observations for {geography} are for {period}.")
    elif broader_published:
        lines.append(f"**Answer:** Recent source-reported {crop} figures are available as broader context; "
                     f"the excerpts below do not establish that these figures apply specifically to {geography}.")
    elif related_excerpts:
        lines.append(f"**Answer:** Recent source-reported {crop} production details were found in Tavily publications. "
                     f"The excerpts below provide broader context for {geography}; they support a location-specific "
                     "conclusion only when the source explicitly identifies that location.")
    else:
        if requested_year and not min_year <= int(requested_year) <= max_year:
            lines.append(f"**Answer:** I can show production figures only from {min_year} through {max_year}; "
                         f"no figures are shown for {requested_year}.")
        else:
            lines.append(f"**Answer:** The latest source checks returned no figure that can be attributed to "
                         f"{geography} within {min_year}–{max_year}. No older figure is substituted.")

    if structured:
        historical_label = (f" (historical context; latest returned year {max(structured_years)})"
                            if latest_query and government_is_old else "")
        lines.extend(["", f"### Structured government observations{historical_label}", "",
                      "| Crop / indicator | State / district | Year | Season | Production | Unit | Source |",
                      "|---|---|---:|---|---:|---|---|"])
        for record in structured:
            citation = _citation(record)
            citation["citation_id"] = len(citations) + 1
            citations.append(citation)
            where = " / ".join(value for value in (record.state, record.district) if value) or "Not stated"
            season = record.season or "Not stated"
            lines.append(f"| {_table_cell(record.crop)} / {_table_cell(record.indicator)} | {_table_cell(where)} | "
                         f"{_table_cell(record.period)} | {_table_cell(season)} | {record.value:g} | "
                         f"{_table_cell(record.unit)} | [{_table_cell(record.source)}]({record.source_url}) [{len(citations)}] |")
    if published:
        lines.extend(["", "### Published source figures", "",
                      "These are publication claims or estimates, not raw structured dataset observations.", "",
                      "| Crop / indicator | Scope | District | Year | Season | Published figure | Source |",
                      "|---|---|---|---:|---|---:|---|"])
        for row in published:
            citation_id = len(citations) + 1
            citations.append({"citation_id": citation_id, "source_agent": "agriculture_sector",
                              "source_authority": row["title"], "document_title": row["title"],
                              "source_url": row["url"], "retrieval_url": row["url"],
                              "source_category": "tavily", "published_figure": row["value"],
                              "unit": row["unit"], "observation_period": row["year"],
                              "publication_date": row.get("published_date") or None,
                              "source_note": row["label"] + ("; broader context, not requested-area data"
                                                             if not row.get("scope_match") else "")})
            source_title = row["title"]
            if row.get("published_date"):
                source_title += f" (published {row['published_date'][:10]})"
            lines.append(f"| {_table_cell(crop)} / {_table_cell(row.get('indicator', 'Crop production'))} "
                         f"({_table_cell(row['label'])}) | "
                         f"{_table_cell(row.get('geography', geography))} | "
                         f"{_table_cell(row.get('district', 'Not stated'))} | {_table_cell(row['year'])} | "
                         f"{_table_cell(row.get('season', 'Not stated'))} | "
                         f"{_table_cell(row['value'])} {_table_cell(row['unit'])} | "
                         f"[{_table_cell(source_title)}]({row['url']}) [{citation_id}] |")
    if related_excerpts and not published:
        lines.extend(["", "### Related Tavily publication details", "",
                      "These source excerpts are useful context; they do not establish a district-level observation "
                      "unless the scope is stated in the excerpt.", "",
                      "| Year | Source-reported detail | Source |",
                      "|---:|---|---|"])
        for item in related_excerpts:
            citation_id = len(citations) + 1
            title, url = item.get("title") or "Source", item.get("url") or ""
            citations.append({"citation_id": citation_id, "source_agent": "agriculture_sector",
                              "source_authority": title, "document_title": title,
                              "source_url": url, "retrieval_url": url,
                              "source_category": "tavily", "observation_period": item.get("relevant_year"),
                              "source_note": "Relevant publication excerpt; geographic scope not inferred"})
            lines.append(f"| {_table_cell(item.get('relevant_year', 'Not stated'))} | "
                         f"{_table_cell(item.get('relevant_excerpt', ''))} | [{_table_cell(title)}]({url}) [{citation_id}] |")
    lines.extend(["", "### Explanation", ""])
    periods = sorted({record.period for record in structured})
    evidence_years = set(periods) | {row.get("year_start", row["year"]) for row in published}
    if len(evidence_years) == 1 and trend_query:
        lines.append("The available figures cover one year, so they do not establish a multi-year trend.")
    elif len(periods) == 1 and len(structured) > 1:
        high = max(structured, key=lambda record: record.value)
        low = min(structured, key=lambda record: record.value)
        def place_label(record: AgricultureObservation) -> str:
            place = record.district or record.state or "reported area"
            return f"{place} ({record.season})" if record.season else place
        high_place, low_place = place_label(high), place_label(low)
        if high_place != low_place:
            lines.append(f"Within the listed {high.crop} observations, {high_place} has the highest "
                         f"reported production and {low_place} the lowest. These are differences across "
                         "the listed districts or seasons for the same reported period, not a time trend "
                         "or a statewide total.")
    elif len(periods) > 1:
        coverage: dict[str, set[tuple[Any, ...]]] = {}
        for record in structured:
            coverage.setdefault(record.period, set()).add((record.state, record.district, record.season))
        comparable = (len({(record.unit, record.source) for record in structured}) == 1
                      and len({frozenset(items) for items in coverage.values()}) == 1)
        if comparable:
            if trend_query:
                lines.append("The structured observations cover multiple periods with a consistent reported scope; "
                             "any comparisons should be read at that scope.")
        else:
            if trend_query:
                lines.append("Coverage differs by geography, season, unit, or source; these records should not be "
                             "combined into a single trend or total.")
        for result in results:
            if result.tool != "get_production_trend" or not result.records:
                continue
            change = _window_change(result, result.records[-1])
            if change:
                percent = (f" ({abs(change['percentage_change']):.2f}%)"
                           if change.get("percentage_change") is not None else "")
                direction = "increased" if change["value"] > 0 else "decreased" if change["value"] < 0 else "was unchanged"
                lines.append(f"For comparable source observations, production {direction} by "
                             f"{_number(abs(change['value']))} {change['unit']}{percent} from "
                             f"{change['from_period']} to {change['period']}; this change is calculated "
                             "from the cited values.")
    elif published:
        by_year: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for row in published:
            comparison_key = (row["year"], row.get("geography", ""))
            by_year.setdefault(comparison_key, set()).add((row["value"], row["unit"]))
        disagreements = {key: figures for key, figures in by_year.items() if len(figures) > 1}
        if disagreements:
            labels = ", ".join(f"{year} ({place})" for year, place in sorted(disagreements))
            lines.append(f"The cited publications report different production figures for {labels}. "
                         "They are separate source-reported estimates; the available excerpts do not establish "
                         "that they use the same scope or definition, so they should not be combined or treated "
                         "as interchangeable.")
        else:
            lines.append("The table contains publication-reported figures. Read each figure with its cited "
                         "source and stated period; the excerpts do not support comparisons beyond those details.")
        if broader_published and not published_for_scope:
            lines.append("These figures describe the broader geography stated in the table. They cannot be used "
                         f"to compare districts in {geography} or establish a {geography}-specific production trend.")
        if trend_query:
            lines.append("These publication figures do not provide multiple comparable periods for the same "
                         "geography, season, unit, and source, so they do not establish a year-over-year trend.")
    elif periods and not trend_query and len(periods) == 1 and len(structured) <= 1:
        lines.append("The table reports the source observation for the selected crop and geography.")
    elif not periods and not published and related_excerpts:
        lines.append("The excerpts provide source context but do not support a district comparison or a year-over-year trend.")
    elif not periods and not published:
        lines.append("The response is limited to source-backed figures and details returned for the requested period and scope.")
    if published and structured:
        lines.append("Structured observations and published estimates are shown separately because their "
                     "periods or coverage may differ.")
    if citations:
        lines.extend(["", "### Sources", "", "Source links and available observation metadata are attached to each table row."])
    return "\n".join(lines), citations


def _display_records(result: AgricultureResult) -> list[Any]:
    """Keep the report compact; full records remain attached as A2A evidence."""
    if result.tool in {"get_production_trend", "get_msp_history"}:
        return result.records if len(result.records) <= 20 else [*result.records[:5], *result.records[-15:]]
    if result.records and getattr(result.records[-1], "frequency", "").casefold() == "daily":
        if result.tool in {"get_mandi_price_trend", "get_production_trend", "get_msp_history"} \
                and len(result.records) > 10:
            # The headline compares the full returned window. Show its starting
            # observation as well as the latest nine so both cited endpoints
            # are visible in the compact evidence table.
            return [result.records[0], *result.records[-9:]]
        return result.records[-10:]
    return result.records[-5:]


def _friendly_error(message: str) -> str:
    if "API_KEY" in message:
        return "A source API key is required for verified live access."
    if "Required source scope is missing" in message:
        return message + ". Add it to the query, for example a state for CEDA prices."
    if "resource mappings" in message:
        return "No verified Data.gov.in dataset mapping is configured for this indicator."
    if "Live mode" in message or "not configured" in message:
        return "The required source is not configured in verified live mode."
    return message


def _report(query: str, results: list[AgricultureResult],
            web_results: list[dict[str, str]] | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Build a readable report where every displayed number has a numbered citation."""
    if any(result.tool in {"get_crop_production", "get_production_trend"} for result in results):
        return _production_report(query, results, web_results or [])
    if any(result.tool == "get_crop_list" for result in results):
        records = [record for result in results for record in result.records]
        names = [getattr(record, "name", "") for record in records if getattr(record, "name", "")]
        citations = [_citation(record) for record in records]
        state = query_parameters(query).state
        heading = f"**Crops in the FAOSTAT catalog (requested state: {state}):** " if state else "**Available crops:** "
        caveat = (f"\n\nThis is FAOSTAT's crop-item catalog, not evidence that each listed crop is grown in {state}. "
                  "Use the state-specific source excerpts below for crops explicitly reported there.") if state else ""
        report = ("## Agriculture diagnostic\n\n" + heading + ", ".join(names) +
                  "\n\nSource: FAOSTAT QCL item catalog." + caveat)
        state_results = web_results or []
        if state and state_results:
            report += (f"\n\n### Published crop context for {state}\n\n"
                       "These are source excerpts. They support a state-specific crop claim only when the excerpt "
                       "names the state and crop.")
            for item in state_results[:4]:
                title, url = item.get("title") or "Source", item.get("url") or ""
                excerpt = item.get("excerpt") or ""
                citation_id = len(citations) + 1
                citations.append({"citation_id": citation_id, "source_agent": "agriculture_sector",
                                  "source_authority": title, "document_title": title, "source_url": url,
                                  "retrieval_url": url, "source_category": "tavily",
                                  "source_note": "Search excerpt; scope must be verified in the linked source"})
                report += f"\n\n- {excerpt} [{title}]({url}) [{citation_id}]"
        return report, citations
    if any(result.tool == "get_current_weather" for result in results):
        records = [record for result in results for record in result.records
                   if isinstance(record, WeatherObservation)]
        if not records:
            details = "; ".join(error.message for result in results for error in result.errors)
            return "## Agriculture diagnostic\n\n**Current weather unavailable.** " + details, []
        first = records[0]
        citations = [{**record.citation(), "citation_id": index}
                     for index, record in enumerate(records, 1)]
        lines = ["## Agriculture diagnostic", "", f"**Location:** {first.display_name or first.location}",
                 f"**Observation time:** {first.period}", "", "### Current observations", "",
                 "| Metric | Value |", "|---|---:|"]
        lines.extend(f"| {record.indicator} | {_number(record.value)} {record.unit} [{index}] |"
                     for index, record in enumerate(records, 1))
        lines.extend(["", "Open-Meteo values represent the selected reference coordinate.",
                      "", "### Provenance", "", f"Source: {first.source}; API: {first.source_url}; "
                      f"retrieved {first.retrieved_at.isoformat()}."])
        return "\n".join(lines), citations
    if any(result.tool in {"get_historical_weather", "get_agriculture_weather", "get_weather_forecast"}
           for result in results):
        return _weather_report(query, results)
    citations: list[dict[str, Any]] = []
    citation_ids: dict[str, int] = {}

    def add_citation(record: Any) -> int:
        citation = _citation(record)
        key = citation.get("provenance_hash") or "|".join(str(citation.get(field)) for field in (
            "source", "dataset", "indicator", "period", "value", "unit"))
        if key not in citation_ids:
            citation_ids[key] = len(citations) + 1
            citation["citation_id"] = citation_ids[key]
            citations.append(citation)
        return citation_ids[key]

    displayed: list[tuple[int, Any]] = []
    for result in results:
        for record in _display_records(result):
            displayed.append((add_citation(record), record))

    answers: list[str] = []
    for result in results:
        if not result.records:
            continue
        if result.tool == "get_msp":
            latest = max(result.records, key=lambda record: record.period)
            active = next((record for record in result.records
                           if "Active Rabi marketing season" in (record.source_note or "")), None)
            latest_ref = add_citation(latest)
            if active and active.period != latest.period:
                active_ref = add_citation(active)
                answers.append(
                    f"The active Rabi marketing season MSP for {active.crop} is "
                    f"{_number(active.value)} {active.unit} in {active.period} [{active_ref}]. "
                    f"The next approved season, {latest.period}, is "
                    f"{_number(latest.value)} {latest.unit} [{latest_ref}]."
                )
            else:
                answers.append(f"The source reports {latest.crop} MSP of "
                               f"{_number(latest.value)} {latest.unit} for "
                               f"Rabi marketing season {latest.period} [{latest_ref}].")
            continue
        if result.tool in {"get_crop_production", "get_production_trend"} and not any(
            getattr(query_parameters(query), field) for field in ("state", "district")
        ):
            counts: dict[str, int] = {}
            for record in result.records:
                counts[record.period] = counts.get(record.period, 0) + 1
            scope = ", ".join(f"{year}: {count}" for year, count in sorted(counts.items()))
            answers.append(
                f"The {result.records[0].crop} resource contains district-season observations "
                f"for the retrieved years ({scope}). These counts are calculated from the returned rows. "
                "Coverage differs across years, so these rows do not establish a comparable "
                "all-India production trend. See the individual observations below."
            )
            continue
        if result.tool in {"get_mandi_price", "get_mandi_price_trend"} and not query_parameters(query).market:
            latest_period = max(record.period for record in result.records)
            rows = [record for record in result.records if record.period == latest_period]
            answers.append(
                f"The latest returned {rows[0].commodity} mandi date is {latest_period}, with "
                f"{len(rows)} market observations. Their source-reported modal prices span "
                f"{_number(min(r.value for r in rows))} to {_number(max(r.value for r in rows))} "
                f"{rows[0].unit}; market, variety and grade can differ. "
                "Choose a market for a like-for-like price trend."
            )
            continue
        latest = result.records[-1]
        latest_ref = add_citation(latest)
        window_change = _window_change(result, latest) if isinstance(latest, AgricultureObservation) else None
        changes = ([window_change] if window_change else
                   [item for item in result.derived if item.get("value") is not None])
        if changes:
            change = changes[-1]
            evidence_refs: list[int] = []
            for item in change.get("evidence", []):
                match = next((record for record in result.records
                              if getattr(record, "period", None) == item.get("period")
                              and getattr(record, "value", None) == item.get("value")), None)
                if match is not None:
                    evidence_refs.append(add_citation(match))
            direction = ("increased" if change["value"] > 0
                         else "decreased" if change["value"] < 0 else "was unchanged")
            percent = change.get("percentage_change")
            pct_text = f" ({abs(percent):.2f}%)" if percent is not None else ""
            refs = "".join(f"[{ref}]" for ref in evidence_refs or [latest_ref])
            movement = ("was unchanged" if change["value"] == 0 else
                        f"{direction} by {_number(abs(change['value']))} {change['unit']}{pct_text}")
            answers.append(
                f"{latest.indicator} for {_scope_label(latest)} {movement}, from "
                f"{change.get('from_period')} to {change['period']}. {refs}"
            )
        elif isinstance(latest, AgricultureObservation):
            answers.append(
                f"Latest returned {latest.indicator.lower()} for {_scope_label(latest)} is "
                f"{_number(latest.value)} {latest.unit} in {latest.period}. [{latest_ref}]"
            )
        else:
            description = getattr(latest, "monsoon_status", None) or getattr(latest, "description", "reported")
            answers.append(f"{getattr(latest, 'indicator', result.tool)} for {latest.period}: "
                           f"{description}. [{latest_ref}]")

    lines = ["## Agriculture diagnostic", ""]
    if any(result.tool == "get_historical_weather" for result in results):
        if query_parameters(query).start_date and query_parameters(query).end_date:
            start = query_parameters(query).start_date
            end = query_parameters(query).end_date
            lines.extend([f"**Interpreted period:** {start:%d %b %Y} - {end:%d %b %Y}", ""])
    if answers:
        lines.extend([
            "**Answer:** " + " ".join(answers), "",
            "### Evidence", "",
            "| Ref | Indicator | Scope | Observation | Period |",
            "|---:|---|---|---:|---|",
        ])
        for ref, record in displayed:
            value = getattr(record, "value", None)
            observation = (f"{_number(value)} {record.unit}" if value is not None else
                           getattr(record, "monsoon_status", None)
                           or getattr(record, "description", "Reported"))
            lines.append(f"| [{ref}] | {getattr(record, 'indicator', record.kind)} | "
                         f"{_scope_label(record)} | {observation} | {record.period} |")
        lines.extend([
            "", "### Provenance", "",
            "Each numbered reference identifies the exact observation, source authority, dataset, "
            "Agriculture MCP tool, upstream tool, filters, URL, period, retrieval time, and provenance hash.",
        ])
        first = next((record for result in results for record in result.records), None)
        if first and first.source_category in {"data_gov", "pib"}:
            periods = sorted({record.period for result in results for record in result.records})
            params = query_parameters(query)
            requested = (params.period or (f"{params.start_year} to {params.end_year}"
                         if params.start_year or params.end_year else
                         f"last {params.history_years} years" if params.history_years else "latest available"))
            lines.extend([f"- Dataset: {first.dataset}", f"- Publisher: {first.source}",
                          f"- Resource URL: {first.source_url}",
                          f"- Requested period: {requested}; actual: {periods[0]} to {periods[-1]}",
                          f"- Retrieved: {first.retrieved_at.isoformat()}",
                          f"- Source fields: {first.source_filters.get('source_fields', {})}",
                          "- Table observations are source-reported; changes and ratios are calculated."])
    else:
        requested = ", ".join(result.tool.removeprefix("get_").replace("_", " ") for result in results)
        if results and all(result.tool in {"get_msp", "get_msp_history", "get_msp_gap"}
                           for result in results):
            lines.extend(["**MSP data unavailable.** The official MSP release did not return "
                          "a verified observation for this request. See the source error below."])
        else:
            lines.extend([
                "**Result: data unavailable.** No verified observation was returned, so no numeric answer was generated.",
                "", f"Requested data: {requested or 'no matching Agriculture dataset'}.",
            ])

    notes = sorted({
        getattr(record, "source_note", None)
        for result in results for record in result.records
        if getattr(record, "source_note", None)
    })
    if notes:
        lines.extend(["", "### Limitations"])
        lines.extend(f"- {note}" for note in notes)
    if citations and any(term in query.casefold() for term in ("why", "despite", "supply")):
        lines.append("- Co-movement is descriptive and does not by itself establish causality.")
    return "\n".join(lines), citations


def _weather_report(query: str, results: list[AgricultureResult]) -> tuple[str, list[dict[str, Any]]]:
    citations: list[dict[str, Any]] = []
    records = [record for result in results for record in result.records
               if isinstance(record, WeatherObservation)]
    if not records:
        errors = "; ".join(error.message for result in results for error in result.errors)
        return ("## Agriculture diagnostic\n\n**Weather data unavailable.** "
                + (errors or "Open-Meteo returned no dated observations.")), citations

    citation_ids: dict[str, int] = {}

    def add(record: WeatherObservation) -> int:
        citation = record.citation()
        key = citation.get("provenance_hash") or repr(citation)
        if key not in citation_ids:
            citation_ids[key] = len(citations) + 1
            citation["citation_id"] = citation_ids[key]
            citations.append(citation)
        return citation_ids[key]

    groups: dict[str, dict[str, tuple[WeatherObservation, int]]] = {}
    for record in records:
        groups.setdefault(record.period, {})[record.metric] = (record, add(record))
    first = records[0]
    period = query_parameters(query)
    lines = [
        "## Agriculture diagnostic", "", f"**Location:** {first.display_name or first.location}",
        f"**Reference point:** {first.latitude}, {first.longitude}", f"**Source:** {first.source}",
    ]
    if period.start_date and period.end_date:
        lines.append(f"**Interpreted period:** {period.start_date:%d %b %Y} - {period.end_date:%d %b %Y}")
    rainfall_only = _is_rainfall_only(query)
    lines.extend(["", "### Daily observations", ""])
    lines.extend(["| Date | Rainfall |", "|---|---:|"] if rainfall_only else [
        "| Date | Min Temp | Max Temp | Rainfall | Wind | ET0 |",
        "|---|---:|---:|---:|---:|---:|"])
    for day in sorted(groups):
        values = groups[day]

        def cell(metric: str, unit: str) -> str:
            item = values.get(metric)
            if not item:
                return "Unavailable"
            record, reference = item
            return f"{_number(record.value)} {unit} [{reference}]"

        if rainfall_only:
            lines.append(f"| {day} | {cell('precipitation', 'mm')} |")
        else:
            lines.append(
                f"| {day} | {cell('temperature_min', '°C')} | {cell('temperature_max', '°C')} | "
                f"{cell('precipitation', 'mm')} | {cell('wind_speed_max', 'km/h')} | {cell('et0', 'mm')} |"
            )
    lines.extend(["", "Weather values represent the selected reference coordinate, not a city-wide aggregate.",
                  "", "### Provenance", "",
                  "Each reference identifies the Open-Meteo observation, date, coordinate, and retrieval metadata."])
    return "\n".join(lines), citations


async def _tavily_fallback(query: str) -> list[dict[str, str]] | None:
    """Find source excerpts when structured observations are unavailable."""
    key = settings.TVLY_KEY_1.get_secret_value() or os.getenv("TVLY_KEY_1", "")
    if not key:
        logger.warning("Agriculture Tavily fallback is unavailable: API key is not configured")
        return None
    msp_request = bool(re.search(r"\bmsp\b|minimum support price", query, re.IGNORECASE))
    scope = query_parameters(query)
    search_query = query + " India official source"
    current_msp = msp_request and bool(re.search(r"\bcurrent\b|\blatest\b", query, re.IGNORECASE))
    if current_msp:
        today = datetime.now(ZoneInfo("Asia/Kolkata"))
        season_start = today.year + (1 if today.month >= 9 else 0)
        season = f"{season_start}-{str(season_start + 1)[-2:]}"
        scope = query_parameters(query)
        crop = scope.crop or scope.commodity or "crop"
        season_query = f"India {crop} minimum support price rabi marketing season {season}"
        searches = [
            (season_query, {"include_domains": ["pib.gov.in"]}, season),
            (season_query, {}, season),
            (search_query, {"include_domains": ["pib.gov.in"]}, None),
            (search_query, {}, None),
        ]
    elif "crops" in query.casefold() and scope.state:
        crop_search = f"crops grown cultivated major crops {scope.state} agriculture government"
        searches = [(crop_search, {"include_domains": ["gov.in", "nic.in", "pib.gov.in"]}, None),
                    (crop_search, {}, None)]
    elif _is_crop_data_query(query):
        crop = scope.crop or "crop"
        geography = " ".join(value for value in (scope.district, scope.state) if value)
        min_year, max_year = _production_year_window(query)
        years = f"{min_year} {max_year}"
        official_domains = ["data.gov.in", "desagri.gov.in", "pib.gov.in", "mospi.gov.in"]
        if scope.district:
            targeted = f"{crop} production {scope.district} district {years} official data"
            comparison = f"{scope.district} {crop} yield production district-wise {years} India"
            broad = f"{scope.state or 'India'} {crop} production estimates {years} official"
        elif scope.state:
            targeted = f"{scope.state} {crop} production estimates district-wise {years} official"
            comparison = f"{scope.state} {crop} production {years} agriculture department"
            broad = f"India {crop} production estimates {years} official"
        else:
            targeted = f"India {crop} latest production estimate {years} official"
            comparison = f"India {crop} production crop year {years} government report"
            broad = f"{crop} production dataset India {years}"
        searches = [(targeted, {"include_domains": official_domains}, None),
                    (comparison, {}, None), (broad, {}, None)]
    else:
        searches = ([(search_query, {"include_domains": ["pib.gov.in"]}, None),
                     (search_query, {}, None)] if msp_request else [(search_query, {}, None)])
    entries: list[Any] = []
    production_request = _is_crop_data_query(query)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for term, options, required_season in searches:
                response = await client.post("https://api.tavily.com/search", json={
                    "api_key": key, "query": term[:240],
                    "search_depth": "advanced", "max_results": 5, "include_answer": False,
                    **options,
                })
                response.raise_for_status()
                found = response.json().get("results", [])
                if required_season and isinstance(found, list):
                    found = [item for item in found if isinstance(item, dict) and required_season in
                               (str(item.get("title") or "") + " " + str(item.get("content") or ""))]
                if production_request and isinstance(found, list):
                    entries.extend(found)
                    continue
                entries = found
                if entries:
                    break
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        logger.warning("Agriculture Tavily fallback failed: %s", type(exc).__name__)
        return None
    results = []
    seen_urls: set[str] = set()
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        content = str(item.get("content") or "").strip()
        if url.startswith("https://") and content and url not in seen_urls:
            results.append({"title": str(item.get("title") or url)[:180],
                            "url": url, "excerpt": content[:500],
                            "published_date": str(item.get("published_date") or "")[:32],
                            "score": str(item.get("score") or "")})
            seen_urls.add(url)
    if _is_crop_data_query(query):
        location = (scope.district or scope.state or "").casefold()
        official_hosts = ("data.gov.in", "desagri.gov.in", "pib.gov.in", "mospi.gov.in", ".gov.in", ".nic.in")
        results.sort(key=lambda row: (
            bool(location and location in (row["title"] + " " + row["excerpt"]).casefold()),
            any(host in row["url"].casefold() for host in official_hosts),
            float(row.get("score") or 0),
        ), reverse=True)
        return results[:12]
    return results


def _comparable_production_trend(structured: list[dict[str, Any]],
                                 published: list[dict[str, Any]]) -> bool:
    """Return true only when the evidence contains multiple periods for the same series."""
    structured_groups: dict[tuple[Any, ...], set[str]] = {}
    for row in structured:
        key = tuple(row.get(field) for field in (
            "indicator", "kind", "crop", "commodity", "state", "district", "season", "unit",
            "source", "source_category", "dataset"))
        structured_groups.setdefault(key, set()).add(str(row.get("period", "")))
    if any(len(periods - {""}) > 1 for periods in structured_groups.values()):
        return True
    publication_groups: dict[tuple[Any, ...], set[str]] = {}
    for row in published:
        key = (row.get("indicator"), row.get("geography"), row.get("district"), row.get("season"),
               row.get("unit"), row.get("url"))
        publication_groups.setdefault(key, set()).add(str(row.get("year_start") or row.get("year") or ""))
    return any(len(periods - {""}) > 1 for periods in publication_groups.values())


async def _llm_explanation(query: str, evidence: dict[str, Any]) -> str | None:
    """Interpret supplied evidence only; the raw evidence is rendered separately."""
    from core.orchestrator.llm_client import llm_client
    if not llm_client._get_api_key():
        return None
    if ((evidence.get("publication_evidence") or evidence.get("source_excerpts"))
            and not evidence.get("structured_observations")):
        system_prompt = (
            "Format a concise, polished explanation of the Tavily publication evidence supplied in JSON. "
            "The report table and excerpts preserve the source's exact values, units, periods, scope, and citations; "
            "do not alter them. Describe the source-reported pattern using only the indicator labels "
            "and scope actually present. Explicitly distinguish national or state-wide context from district data. "
            "Do not describe production figures as yield or area, and do not merge organic and total production. "
            "Describe a year-over-year trend only when comparable_trend_supported is true. Use two clear sentences. "
            "Do not claim missing data, methodology, verification, or causes unless the evidence states it."
        )
    else:
        system_prompt = (
            "Explain what the agricultural observations show in two specific plain sentences. "
            "For district or state records, identify which reported observations are relatively higher or lower "
            "when the evidence supports that comparison. "
            "Mention crop, geography, and season where useful. Do not spend the explanation saying "
            "whether data was found or merely restating that coverage is limited. Never say that data, "
            "figures, records, or observations are unavailable or missing. When a publication figure is "
            "for a broader geography, explain what that figure describes and what comparisons its scope "
            "does not support; do not turn that scope limitation into a claim that the requested area's "
            "data is absent. Discuss a trend only if comparable_trend_supported is true. Do not repeat numbers, "
            "dates, percentages, prices, or citation markers; the evidence table supplies those exactly. "
            "Use only the indicator labels present in the evidence. Do not claim yield, cultivated area, or "
            "organic production unless that indicator appears in the evidence. Do not claim a lack of verification, "
            "methodology, or regional breakdown unless the evidence states that. Do not infer causation or add facts."
        )
    try:
        answer = await llm_client.complete(
            "Question: " + query + "\nAs-of date: "
            + datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
            + "\nEvidence (JSON): " + json.dumps(evidence, default=str)[:14000],
            system_prompt,
        )
    except Exception as exc:
        logger.warning("Agriculture LLM explanation failed: %s", type(exc).__name__)
        return None
    if not answer.strip() or answer == llm_client._unavailable_notice():
        return None
    has_search_excerpts = bool(evidence.get("web_excerpts") or evidence.get("source_excerpts"))
    has_broader_publications = any(
        not item.get("scope_match") for item in evidence.get("publication_evidence", [])
    )
    search_context_only = has_search_excerpts and not evidence.get("structured_observations")
    if (has_broader_publications or search_context_only) and re.search(
        r"\b(?:no|none|not (?:available|found|returned|present))\s+(?:[a-z -]+\s+)?"
        r"(?:data|figures?|records?|observations?|evidence|(?:data\s+)?pattern|trend|comparison)\b",
        answer,
        re.IGNORECASE,
    ):
        return None
    evidence_text = json.dumps(evidence, default=str).casefold()
    if re.search(r"\byield\b", answer, re.IGNORECASE) and not re.search(r"\byield\b", evidence_text):
        return None
    if re.search(r"\borganic\b", answer, re.IGNORECASE) and not re.search(r"\borganic\b", evidence_text):
        return None
    if (re.search(r"\b(?:trend|increased|decreased|rose|fell|growth|declined|year.over.year)\b",
                  answer, re.IGNORECASE)
            and not evidence.get("comparable_trend_supported")):
        return None
    unsafe = bool(re.search(r"\d|₹|%|\[\d+\]", answer)) or bool(
        has_search_excerpts and re.search(r"\b(?:current|latest|most recent)\b", answer, re.IGNORECASE))
    if unsafe:
        try:
            answer = await llm_client.complete(
                "Rewrite this explanation without numbers, dates, prices, percentages or citation markers. "
                "Explain the concrete data pattern. Do not add claims about verification, methodology, "
                "regional coverage, or why figures differ unless the evidence explicitly says so. "
                "Question: " + query + "\nEvidence: " + json.dumps(evidence, default=str)[:14000],
                "You explain source observations carefully in two plain sentences. "
                "Compare named places or source figures where supported, and do not invent context. "
                "Search excerpts are unverified source leads. Do not add factual claims.",
            )
        except Exception:
            return None
        if answer == llm_client._unavailable_notice() or re.search(r"\d|₹|%|\[\d+\]", answer) or (
            has_search_excerpts and re.search(
                r"\b(?:current|latest|most recent)\b", answer, re.IGNORECASE)
        ):
            return None
    answer = re.sub(r"【web_excerpts\[(\d+)\]】", lambda match: f"[{int(match[1]) + 1}]", answer)
    return answer.strip()


def _finding(result: AgricultureResult) -> AgricultureFinding:
    sentences = []
    for record in result.records[-5:]:
        if isinstance(record, AgricultureObservation):
            location = " / ".join(str(v) for v in (
                record.crop or record.commodity, record.state, record.market,
                getattr(record, "city", None), getattr(record, "fertilizer", None),
                getattr(record, "measure", None), getattr(record, "irrigation_source", None),
            ) if v)
            sentences.append(f"{record.indicator} ({location or 'reported scope'}): {record.value:g} {record.unit} "
                             f"for {record.period} [Agriculture; {record.mcp_tool}; {record.source}; {record.dataset}].")
            if record.source_note:
                sentences.append(record.source_note)
        else:
            text = getattr(record, "description", None) or getattr(record, "monsoon_status", "")
            sentences.append(f"{text} ({record.period}; {record.source}; {record.dataset}).")
    if len(result.records) > 5:
        sentences.append("Showing the latest five returned observations; the full evidence is attached.")
    for item in result.derived[-3:]:
        if "value" in item:
            sentences.append(f"{item['indicator']}: {item['value']:.2f} {item['unit']} "
                             f"for {item['period']} (calculated from the cited observations).")
            if item.get("percentage_change") is not None:
                sentences.append(f"Change from {item['from_period']} to {item['period']}: "
                                 f"{item['percentage_change']:.2f}%.")
        elif "ranking" in item:
            ranked = ", ".join(str(row.get("market") or row.get("state")) for row in item["ranking"])
            sentences.append(f"Ranking of returned comparable observations: {ranked}.")
    if not sentences:
        sentences.append("No matching sourced observations are available.")
    return AgricultureFinding(
        indicator=result.tool, finding=" ".join(sentences), evidence=result.records,
        source=[_citation(r) for r in _display_records(result)], status=result.status,
        confidence="sourced_observations" if result.records else "insufficient_evidence",
        analytics=result.derived,
    )


async def agriculture_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", ""))
    selected = select_agriculture_tools(query)
    scope = query_parameters(query, state.get("parameters"))
    protocol = MCPClientWrapper(mcp_server)
    names = sorted(selected)
    if scope.crop or _is_crop_data_query(query):
        logger.info("Crop query: query=%r crop=%r intent=%r tools=%s range=%s-%s",
                    query, scope.crop, scope.intent, names, scope.start_year or scope.start_date,
                    scope.end_year or scope.end_date)
    # Weather observations are not crop-specific. Keep actual geography intact.
    def arguments(name: str) -> dict:
        scoped = scope.model_dump(mode="json", exclude_none=True)
        if any(part in name for part in ("rainfall", "monsoon", "weather", "irrigation", "fertilizer", "scheme")):
            scoped.pop("crop", None)
            scoped.pop("commodity", None)
        if name in {"get_current_weather", "get_weather_forecast", "get_historical_weather", "get_agriculture_weather"}:
            scoped["location"] = scoped.get("location") or scoped.get("city") or scoped.get("state")
            scoped.pop("city", None)
            scoped.pop("state", None)
        elif "city" in scoped:
            scoped.pop("city")
        return {"query": scoped}
    outputs = await asyncio.gather(
        *(protocol.call_tool_async(name, arguments(name)) for name in names),
        return_exceptions=True,
    )
    findings, errors, freshness, context, results = [], [], {}, {}, []
    for name, output in zip(names, outputs):
        try:
            if isinstance(output, Exception):
                raise output
            result = AgricultureResult.model_validate(output)
        except Exception:
            result = AgricultureResult(tool=name, status="error")
            errors.append(f"{name}: Agriculture MCP request failed")
        if name == "get_historical_weather" and _is_rainfall_only(query) and result.records:
            result.records = [record for record in result.records
                              if isinstance(record, WeatherObservation) and record.metric == "precipitation"]
            if not result.records:
                result.status = "unavailable"
                result.errors.append(SourceError(source="weather_mcp", code="missing_data",
                                                 message="No precipitation observations were returned"))
        finding = _finding(result)
        results.append(result)
        findings.append(finding.model_dump(mode="json"))
        errors.extend(f"{name}: {e.source}: {e.message}" for e in result.errors)
        freshness[name] = (
            "cached" if any(r.freshness == "cached" for r in result.records)
            else "source_snapshot" if any(r.freshness == "source_snapshot" for r in result.records)
            else "retrieved_live" if result.records else "unavailable"
        )
        if result.records:
            record = result.records[-1]
            context[name] = {"period": record.period, "value": getattr(record, "value", None),
                             "finding": finding.finding, "records": result.model_dump(mode="json")["records"]}
    min_year, max_year = _production_year_window(query)
    stale = any(
        result.records and result.tool in {"get_crop_production", "get_production_trend",
                                           "get_crop_area", "get_crop_yield"}
        and max(int(record.period[:4]) for record in result.records if record.period[:4].isdigit())
        < min_year
        for result in results
    )
    for result in results:
        if result.tool not in {"get_crop_production", "get_production_trend"}:
            continue
        original_records = result.records
        result.records = [record for record in original_records
                          if record.period[:4].isdigit()
                          and min_year <= int(record.period[:4]) <= max_year]
        if len(result.records) != len(original_records):
            result.derived = []
        if not result.records:
            result.status = "unavailable"
            context.pop(result.tool, None)
            freshness[result.tool] = "unavailable"
        else:
            finding = _finding(result)
            context[result.tool] = {"period": result.records[-1].period,
                                    "value": getattr(result.records[-1], "value", None),
                                    "finding": finding.finding,
                                    "records": result.model_dump(mode="json")["records"]}
        logger.info("Fresh crop result after %s-%s filter: tool=%s count=%d periods=%s matching_crop=%r",
                    min_year, max_year, result.tool, len(result.records),
                    sorted({record.period for record in result.records}), scope.crop)
    findings = [_finding(result).model_dump(mode="json") for result in results]
    raw_records = [record.model_dump(mode="json", exclude_none=True)
                   for result in results for record in result.records]
    incomplete = any(result.status in {"partial", "unavailable", "error"} for result in results)
    production_tools = {"get_crop_production", "get_production_trend"}
    official_production_records = [
        record for result in results if result.tool in production_tools for record in result.records
        if record.source_category in {"mospi", "data_gov"}
    ]
    production_query = any(result.tool in production_tools for result in results)
    if production_query:
        # Tavily is a fallback only after the official sources return no in-scope observations.
        needs_tavily = not official_production_records
    else:
        needs_tavily = bool(names and (not raw_records or stale or incomplete or
                                       ("get_crop_list" in names and scope.state)))
    web_results = []
    tavily_failed = False
    if needs_tavily:
        logger.info("No sufficient in-range structured data; invoking Tavily fallback for query=%r", query)
        tavily_response = await _tavily_fallback(query)
        tavily_failed = tavily_response is None
        web_results = tavily_response or []
    if any(result.tool in {"get_crop_production", "get_production_trend"} for result in results):
        web_results = [item for item in web_results
                       if _production_tavily_rows(query, [item])
                       or _relevant_tavily_excerpts(query, [item])]
    if needs_tavily:
        freshness["tavily_search"] = (
            "search_failed" if tavily_failed else "retrieved_live" if web_results
            else "searched_no_qualifying_results"
        )
        logger.info("Tavily fallback status=%s qualifying_results=%d",
                    freshness["tavily_search"], len(web_results))
    report, citations = _report(query, results, web_results)
    if tavily_failed and any(result.tool in {"get_crop_production", "get_production_trend"}
                             for result in results):
        report += ("\n\n**Search limitation:** The structured data had no observations in the requested year range, "
                   "and the live Tavily search could not be completed. No unverified figure is substituted.")
    elif needs_tavily and not web_results and any(
            result.tool in {"get_crop_production", "get_production_trend"} for result in results):
        report += ("\n\nTavily was searched, but its results contained no production detail in the requested "
                   "year range that could be tied to this crop. No older figure is substituted.")
    if web_results:
        safe_publication_context = []
        for item in web_results:
            relevant_item = _relevant_tavily_excerpts(query, [item])
            if relevant_item:
                excerpt = relevant_item[0].get("relevant_excerpt", "")
            else:
                accepted_rows = _production_tavily_rows(query, [item])
                excerpt = accepted_rows[0].get("excerpt", "") if accepted_rows else ""
            safe_publication_context.append({key: item.get(key) for key in ("title", "url")}
                                            | {"excerpt": excerpt})
        context["tavily_search"] = {"results": safe_publication_context}
        freshness["tavily_search"] = "retrieved_live"
    if (raw_records or web_results) and "get_crop_list" not in names:
        shown = raw_records if len(raw_records) <= 30 else [*raw_records[:15], *raw_records[-15:]]
        compact = [{key: row[key] for key in (
            "period", "value", "unit", "crop", "commodity", "state", "district",
            "market", "season", "indicator", "kind", "metric", "source", "source_category",
            "dataset", "source_note") if row.get(key) is not None}
            for row in shown]
        publication_evidence = _production_tavily_rows(query, web_results)
        explanation_evidence = {
            "structured_observations": compact,
            "publication_evidence": publication_evidence,
            "source_excerpts": [{"title": item.get("title"), "url": item.get("url"),
                                 "excerpt": item.get("relevant_excerpt"),
                                 "published_date": item.get("published_date")}
                                for item in _relevant_tavily_excerpts(query, web_results)],
            "dataset_titles": sorted({row.get("dataset", "") for row in raw_records}),
            "total_observation_count": len(raw_records),
            "comparable_trend_supported": _comparable_production_trend(compact, publication_evidence),
            "coverage_note": "Only make comparisons when year, geography, season, unit, and source support them.",
        }
        explanation = await _llm_explanation(query, explanation_evidence)
        if explanation:
            if any(result.tool in {"get_crop_production", "get_production_trend"} for result in results):
                source_heading = "\n\n### Sources"
                if source_heading in report:
                    report = report.replace(source_heading, "\n\n" + explanation + source_heading, 1)
                else:
                    report += "\n\n" + explanation
            else:
                report += "\n\n### Explanation\n\n" + explanation
    if not names:
        report = ("## Agriculture diagnostic\n\n**Out of scope.** Agriculture covers crops, mandi prices, "
                  "MSP, rainfall, agricultural inputs, and schemes. No data tool was called.")
    status = "unavailable" if not citations else "partial" if errors or not raw_records or stale else "completed"
    return {
        "agriculture_sector_analysis": report, "agriculture_sector_data": context,
        "agriculture_sector_citations": citations, "agriculture_sector_freshness": freshness,
        "agriculture_sector_errors": errors, "agriculture_sector_findings": findings,
        "agriculture_sector_status": status,
    }
