"""Agriculture reasoning over MCP evidence, with deterministic domain routing."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from core.protocols.mcp.client import MCPClientWrapper
from .mcp_server import mcp_server
from .models import AgricultureFinding, AgricultureObservation, AgricultureQuery, AgricultureResult, WeatherObservation

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


def _resolve_weather_dates(query: str, today: date | None = None) -> tuple[date, date] | None:
    q = query.casefold()
    current = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if "yesterday" in q:
        day = current - timedelta(days=1)
        return day, day
    if "last week" in q or "previous week" in q:
        return current - timedelta(days=6), current
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
        return current - timedelta(days=int(match[1]) - 1), current
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
    lowered = location.casefold()
    for stop in _WEATHER_LOCATION_STOP_WORDS:
        index = lowered.find(stop)
        if index >= 0:
            location = location[:index].strip(" ,")
            lowered = location.casefold()
    return location or None


def _extract_crop_name(query: str) -> str | None:
    text = query.strip().rstrip("?.!")
    match = re.search(r"(?:^|\b)production\s+of\s+(.+?)(?:\s+(?:in|from|over|for)\b|$)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"^(.+?)\s+production\b", text, re.IGNORECASE)
    if not match:
        return None
    crop = match.group(1).strip(" ,")
    crop = re.sub(r"^(?:latest|historical|annual|the)\s+", "", crop, flags=re.IGNORECASE)
    crop = re.sub(r"\s+(?:trend|history)$", "", crop, flags=re.IGNORECASE).strip()
    if crop.casefold() in {"major crops", "crops", "all crops", "crop"}:
        return None
    return crop.title()


def _extract_history_years(query: str) -> int | None:
    match = re.search(r"(?:last|past|over the last)\s+(\d+)\s+years?", query.casefold())
    return int(match[1]) if match else None


def _extract_production_years(query: str) -> tuple[int, int] | None:
    match = re.search(r"(?:from\s+)?(\d{4})(?:-\d{2})?\s+to\s+(\d{4})(?:-\d{2})?", query.casefold())
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
    if re.search(r"\blist\s+of\s+(?:major\s+)?crops?\b", q) and "production" not in q:
        return {"get_crop_list"}
    crop = _extract_crop_name(query)
    production_intent = "production" in q or "crop output" in q
    if production_intent and (crop or "crop" in q or "crops" in q):
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
    crop = _extract_crop_name(query)
    if crop:
        parameters.setdefault("crop", crop)
        parameters.setdefault("commodity", crop)
    for crop in ("wheat", "rice", "paddy", "onion", "tomato", "potato", "cotton", "maize", "sugarcane", "soybean", "pulses", "gram", "mustard", "garlic", "ginger", "chilli", "turmeric"):
        if re.search(r"\b" + crop + r"s?\b", q):
            parameters.setdefault("crop", crop)
            parameters.setdefault("commodity", crop)
            break
    if not parameters.get("commodity") and not parameters.get("crop"):
        if any(w in q for w in ("agmarket", "agmarknet", "mandi")):
            parameters.setdefault("crop", "onion")
            parameters.setdefault("commodity", "onion")
    history_years = _extract_history_years(query)
    if history_years:
        parameters.setdefault("history_years", history_years)
    year_range = _extract_production_years(query)
    if year_range:
        parameters.setdefault("start_year", year_range[0])
        parameters.setdefault("end_year", year_range[1])
    if "production" in q or "crop output" in q:
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
    if "state" not in parameters:
        for alias, state in (("tamilnadu", "Tamil Nadu"), ("tn", "Tamil Nadu")):
            if re.search(r"\b" + alias + r"\b", q):
                parameters.setdefault("state", state)
                break
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
        getattr(record, "market", None), getattr(record, "city", None),
        getattr(record, "fertilizer", None), getattr(record, "measure", None),
        getattr(record, "irrigation_source", None),
        getattr(record, "location", None),
    )
    return " / ".join(str(value) for value in values if value) or "Reported scope"


def _number(value: float) -> str:
    """Readable display precision; canonical values remain unrounded in evidence."""
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _window_change(result: AgricultureResult, latest: AgricultureObservation) -> dict[str, Any] | None:
    """Compare the first and last compatible records for a trend headline."""
    if result.tool not in {"get_production_trend", "get_mandi_price_trend", "get_msp_history"}:
        return None
    keys = ("kind", "crop", "commodity", "state", "district", "market", "variety",
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


def _display_records(result: AgricultureResult) -> list[Any]:
    """Keep the report compact; full records remain attached as A2A evidence."""
    if result.tool in {"get_production_trend", "get_msp_history"}:
        return result.records
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


def _report(query: str, results: list[AgricultureResult]) -> tuple[str, list[dict[str, Any]]]:
    """Build a readable report where every displayed number has a numbered citation."""
    if any(result.tool == "get_crop_list" for result in results):
        records = [record for result in results for record in result.records]
        names = [getattr(record, "name", "") for record in records if getattr(record, "name", "")]
        citations = [_citation(record) for record in records]
        return ("## Agriculture diagnostic\n\n**Available crops:** " + ", ".join(names) +
                "\n\nSource: FAOSTAT QCL item catalog."), citations
    if any(result.tool in {"get_historical_weather", "get_agriculture_weather"} for result in results):
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
    else:
        requested = ", ".join(result.tool.removeprefix("get_").replace("_", " ") for result in results)
        lines.extend([
            "**Result: data unavailable.** No verified observation was returned, so no numeric answer was generated.",
            "", f"Requested data: {requested or 'no matching Agriculture dataset'}.",
        ])

    issues = [
        f"{result.tool.replace('_', ' ')} - {error.source}: {_friendly_error(error.message)}"
        for result in results for error in result.errors
    ]
    notes = sorted({
        getattr(record, "source_note", None)
        for result in results for record in result.records
        if getattr(record, "source_note", None)
    })
    if issues or notes:
        lines.extend(["", "### Limitations"])
        lines.extend(f"- {note}" for note in notes)
        lines.extend(f"- {issue}" for issue in issues)
    if citations and any(term in query.casefold() for term in ("why", "despite", "supply")):
        lines.append("- Co-movement is descriptive and does not by itself establish causality.")
    return "\n".join(lines), citations


def _weather_report(query: str, results: list[AgricultureResult]) -> tuple[str, list[dict[str, Any]]]:
    citations: list[dict[str, Any]] = []
    records = [record for result in results for record in result.records
               if isinstance(record, WeatherObservation)]
    if not records:
        errors = " ".join(error.message for result in results for error in result.errors)
        return ("## Agriculture diagnostic\n\n**Weather data unavailable.** "
                f"Open-Meteo returned no observations. {errors}"), citations

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
    lines.extend(["", "### Daily observations", "",
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

        lines.append(
            f"| {day} | {cell('temperature_min', '°C')} | {cell('temperature_max', '°C')} | "
            f"{cell('precipitation', 'mm')} | {cell('wind_speed_max', 'km/h')} | {cell('et0', 'mm')} |"
        )
    lines.extend(["", "Weather values represent the selected reference coordinate; they are not a Tamil Nadu-wide aggregate.",
                  "", "### Provenance", "",
                  "Each reference identifies the Open-Meteo observation, date, coordinate, and retrieval metadata."])
    return "\n".join(lines), citations


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
    if scope.crop or "production" in query.casefold():
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
        if name in {"get_crop_production", "get_production_trend"}:
            logger.info("Crop result: tool=%s count=%d periods=%s matching_crop=%r",
                        name, len(result.records), [record.period for record in result.records],
                        scope.crop)
    report, citations = _report(query, results)
    if not names:
        report = ("## Agriculture diagnostic\n\n**Out of scope.** Agriculture covers crops, mandi prices, "
                  "MSP, rainfall, agricultural inputs, and schemes. No data tool was called.")
    status = "unavailable" if not citations else "partial" if errors else "completed"
    return {
        "agriculture_sector_analysis": report, "agriculture_sector_data": context,
        "agriculture_sector_citations": citations, "agriculture_sector_freshness": freshness,
        "agriculture_sector_errors": errors, "agriculture_sector_findings": findings,
        "agriculture_sector_status": status,
    }
