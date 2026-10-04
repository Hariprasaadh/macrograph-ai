"""Normalize source-specific rows and compute strictly aligned comparisons."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import duckdb

from .client import SourcePayload, SourceUnavailable, reject_sample_data
from .models import (
    AgricultureObservation, AgricultureQuery, AgricultureScheme, CropArea, CropListObservation, CropProduction,
    CropYield, FertilizerObservation, IrrigationObservation, MandiPrice, MarketArrival,
    MonsoonObservation, MSPObservation, RainfallObservation, WeatherObservation,
)


def _rows(data: Any) -> list[dict]:
    reject_sample_data(data)
    if isinstance(data, list):
        if not all(isinstance(row, dict) for row in data):
            raise ValueError("Expected object rows")
        return data
    if isinstance(data, dict):
        if data.get("status") in {"error", "unavailable"} or data.get("error"):
            raise SourceUnavailable("Upstream source returned unavailable")
        for key in ("records", "data", "results", "prices", "observations"):
            if key in data:
                return _rows(data[key])
        # Open-Meteo daily arrays must carry actual dates and units.
        if "daily" in data:
            daily = data["daily"]
            dates, values = daily.get("time", []), daily.get("precipitation_sum", [])
            if len(dates) != len(values):
                raise ValueError("Weather arrays have different lengths")
            return [
                {"period": day, "value": value,
                 "unit": data.get("daily_units", {}).get("precipitation_sum"),
                 "frequency": "daily", "city": data.get("city")}
                for day, value in zip(dates, values)
            ]
        if any(k in data for k in ("value", "modal_price", "production", "msp", "rainfall", "name", "monsoon_status")):
            return [data]
    raise ValueError("Unrecognized source payload; configure field mapping for this dataset")


def _get(row: dict, *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return None


def _period(value: Any) -> str:
    if value is None:
        raise ValueError("Observation period missing")
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    if not text or text.lower() in {"unknown", "current", "latest", "n/a"}:
        raise ValueError("Observation period missing")
    return text


def _parse(payload: SourcePayload, tool: str, model: type, aliases: tuple[str, ...]) -> list:
    output = []
    for original in _rows(payload.data):
        row = {**original}
        for canonical, upstream in payload.binding.fields.items():
            if upstream in original:
                row[canonical] = original[upstream]
        provenance = {
            "source": row.get("source") or payload.source,
            "source_category": payload.category,
            "source_url": row.get("source_url") or payload.binding.source_url,
            "dataset": payload.binding.dataset, "mcp_tool": tool,
            "upstream_tool": payload.binding.tool, "retrieved_at": payload.retrieved_at,
            "source_filters": payload.binding.arguments,
            "data_vintage": _get(row, "data_vintage", "last_updated"),
            "freshness": row.get("freshness", "retrieved_live"),
        }
        fields = {key: value for key, value in row.items() if key in model.model_fields}
        fields.pop("kind", None)
        fields.update(provenance)
        fields["period"] = _period(_get(row, "period", "arrival_date", "date", "year", "financial_year"))
        if issubclass(model, AgricultureObservation):
            value = _get(row, "value", *aliases)
            if isinstance(value, bool) or value is None:
                raise ValueError("Numeric observation missing")
            fields["value"] = float(str(value).replace(",", ""))
            fields["indicator"] = row.get("indicator") or tool.removeprefix("get_").replace("_", " ")
            fields["unit"] = row.get("unit") or payload.binding.unit
            fields["frequency"] = row.get("frequency") or payload.binding.frequency
        else:
            fields.setdefault("indicator", tool.removeprefix("get_").replace("_", " "))
            if "indicator" not in model.model_fields:
                fields.pop("indicator", None)
        output.append(model.model_validate(fields))
    return output


def parse_mandi_response(payload: SourcePayload, tool: str = "get_mandi_price") -> list[MandiPrice]:
    rows = []
    for original in _rows(payload.data):
        row = {**original}
        modal = row.get("modal_price")
        try:
            modal_value = float(str(modal).replace(",", ""))
        except (TypeError, ValueError):
            modal_value = None
        if modal_value is not None:
            for bound in ("min_price", "max_price"):
                value = row.get(bound)
                try:
                    bound_value = float(str(value).replace(",", ""))
                except (TypeError, ValueError):
                    bound_value = None
                if bound_value is not None and (
                    bound == "min_price" and bound_value > modal_value or
                    bound == "max_price" and bound_value < modal_value
                ):
                    # Some AgMarket rows contain contradictory range bounds.
                    # Keep the modal observation and omit only the invalid bound.
                    row[bound] = None
        rows.append(row)
    normalized = payload.model_copy(update={"data": rows})
    return _parse(normalized, tool, MandiPrice, ("modal_price",))


def parse_crop_production_response(payload: SourcePayload, tool: str = "get_crop_production") -> list[CropProduction]:
    return _parse(payload, tool, CropProduction, ("production",))


def parse_crop_list_response(payload: SourcePayload, tool: str = "get_crop_list") -> list[CropListObservation]:
    return _parse(payload, tool, CropListObservation, ())


def parse_msp_response(payload: SourcePayload, tool: str = "get_msp") -> list[MSPObservation]:
    return _parse(payload, tool, MSPObservation, ("msp",))


def parse_rainfall_response(payload: SourcePayload, tool: str = "get_rainfall") -> list[RainfallObservation]:
    # The supplied weather MCP emits dated prose, not JSON. Parse only its
    # historical daily rows, never averages, soil estimates or season heuristics.
    if isinstance(payload.data, str) and payload.binding.tool == "get_historical_weather_india":
        header = re.search(r"Historical Weather for (.+?) \(Last", payload.data)
        if not header:
            raise SourceUnavailable("Weather MCP returned no historical observations", "missing_data")
        location = header.group(1)
        rows = []
        for line in payload.data.splitlines():
            match = re.match(
                r"^(\d{4}-\d{2}-\d{2}):[^|]*\|[^|]*\|[^|]*?(\d+(?:\.\d+)?)mm\s*\|",
                line,
            )
            if match:
                rows.append({"period": match[1], "value": match[2], "unit": "mm", "frequency": "daily",
                             "city": location.split(",")[0].strip(), "indicator": "Daily precipitation",
                             "source_note": "Open-Meteo archive precipitation (rain and snow), not IMD station rainfall; "
                                            "city/grid scope: " + location + ". Null daily readings are omitted."})
        payload = payload.model_copy(update={"data": rows})
    return _parse(payload, tool, RainfallObservation, ("rainfall", "rainfall_mm", "precipitation_sum"))


def parse_weather_response(payload: SourcePayload, tool: str) -> list[WeatherObservation]:
    if isinstance(payload.data, dict) and payload.data.get("success") is False:
        detail = payload.data.get("details") or payload.data.get("error") or "Open-Meteo request failed"
        raise SourceUnavailable(str(detail), "source_error")
    return _parse(payload, tool, WeatherObservation, ("value",))


def parse_monsoon_response(payload: SourcePayload, tool: str = "get_monsoon_status") -> list[MonsoonObservation]:
    if "imd" not in payload.source.lower() and "meteorological" not in payload.source.lower():
        raise SourceUnavailable("Official monsoon status requires an IMD source, not a season heuristic", "unsupported")
    return _parse(payload, tool, MonsoonObservation, ())


def parse_fertilizer_response(payload: SourcePayload, tool: str = "get_fertilizer_consumption") -> list[FertilizerObservation]:
    return _parse(payload, tool, FertilizerObservation, ("consumption",))


def parse_irrigation_response(payload: SourcePayload, tool: str = "get_irrigation_area") -> list[IrrigationObservation]:
    return _parse(payload, tool, IrrigationObservation, ("irrigated_area",))


PARSERS = {
    "crop_production": parse_crop_production_response,
    "crop_list": parse_crop_list_response,
    "crop_yield": lambda p, t: _parse(p, t, CropYield, ("yield",)),
    "crop_area": lambda p, t: _parse(p, t, CropArea, ("area",)),
    "mandi_price": parse_mandi_response,
    "market_arrivals": lambda p, t: _parse(p, t, MarketArrival, ("arrivals",)),
    "msp": parse_msp_response,
    "rainfall": parse_rainfall_response,
    "weather_current": lambda p, t: parse_weather_response(p, t),
    "weather_forecast": lambda p, t: parse_weather_response(p, t),
    "weather_historical": lambda p, t: parse_weather_response(p, t),
    "weather_agriculture": lambda p, t: parse_weather_response(p, t),
    "monsoon": parse_monsoon_response,
    "fertilizer": parse_fertilizer_response,
    "irrigation": parse_irrigation_response,
    "scheme": lambda p, t: _parse(p, t, AgricultureScheme, ()),
}


def filter_records(records: list, query: AgricultureQuery) -> list:
    """Enforce user scope even when a provider ignores its filters."""
    selected = []
    for record in records:
        matches = True
        for key in ("crop", "commodity", "state", "district", "market", "variety", "city", "period"):
            requested = getattr(query, key)
            if requested is None:
                continue
            actual = getattr(record, key, None)
            # Crop and commodity are equivalent only for scope filtering, not analytics joins.
            if actual is None and key in {"crop", "commodity"}:
                actual = getattr(record, "crop" if key == "commodity" else "commodity", None)
            if actual is None or str(actual).casefold() != requested.casefold():
                matches = False
        if query.scheme and (not isinstance(record, AgricultureScheme) or query.scheme.casefold() not in record.name.casefold()):
            matches = False
        if query.start_date or query.end_date:
            try:
                day = datetime.strptime(record.period, "%Y-%m-%d").date()
            except ValueError:
                matches = False
            else:
                if query.start_date and day < query.start_date or query.end_date and day > query.end_date:
                    matches = False
        if matches:
            selected.append(record)
    return sorted(selected, key=lambda r: r.period)[-query.limit:]


def series_changes(records: list[AgricultureObservation]) -> list[dict]:
    """DuckDB lag per exact series; label interval change, never assume YoY/MoM."""
    if len(records) < 2:
        return []
    keys = ("kind", "crop", "commodity", "state", "district", "market", "variety", "season", "unit", "frequency", "dataset", "source")
    rows = [(i, json.dumps([getattr(r, k, None) for k in keys]), r.period, r.value)
            for i, r in enumerate(records)]
    with duckdb.connect(":memory:") as con:
        con.execute("CREATE TABLE observations (id INTEGER, series VARCHAR, period VARCHAR, value DOUBLE)")
        con.executemany("INSERT INTO observations VALUES (?, ?, ?, ?)", rows)
        # Ambiguous duplicates invalidate the series comparison.
        results = con.execute("""
            WITH unique_series AS (
                SELECT series FROM observations GROUP BY series
                HAVING count(*) = count(DISTINCT period)
            ), changes AS (
                SELECT id, value, lag(id) OVER w AS previous_id,
                       lag(value) OVER w AS previous_value
                FROM observations JOIN unique_series USING(series)
                WINDOW w AS (PARTITION BY series ORDER BY period)
            )
            SELECT id, previous_id, value - previous_value,
                   (value - previous_value) / nullif(previous_value, 0) * 100
            FROM changes WHERE previous_id IS NOT NULL
        """).fetchall()
    changes = [{"indicator": "interval_change", "value": delta, "unit": records[i].unit,
             "percentage_change": pct, "from_period": records[j].period,
             "period": records[i].period, "formula": "current - previous; percent = delta / previous * 100",
             "evidence": [records[j].citation(), records[i].citation()]}
            for i, j, delta, pct in results]
    # Annual/fiscal-year and calendar-month labels are compared exactly.
    # Never label a multi-year gap as YoY or a multi-month gap as MoM.
    for change in changes:
        current, previous = change["period"], change["from_period"]
        if re.fullmatch(r"\d{4}(?:-\d{2})?", current) and re.fullmatch(r"\d{4}(?:-\d{2})?", previous):
            record = next(r for r in records if r.period == current)
            if record.frequency.casefold() in {"annual", "annually", "yearly"}:
                if int(current[:4]) - int(previous[:4]) == 1 and current[4:] == (
                    "" if len(current) == 4 else "-" + str((int(previous[5:]) + 1) % 100).zfill(2)
                ):
                    change["indicator"] = "year_over_year_change"
            elif record.frequency.casefold() == "monthly" and len(current) == len(previous) == 7:
                if int(current[:4]) * 12 + int(current[5:]) - int(previous[:4]) * 12 - int(previous[5:]) == 1:
                    change["indicator"] = "month_over_month_change"
    return changes


def rainfall_anomalies(records: list[RainfallObservation]) -> list[dict]:
    return [
        {"indicator": "rainfall_anomaly", "value": (r.value - r.normal_value) / r.normal_value * 100,
         "unit": "%", "period": r.period, "formula": "(rainfall - normal) / normal * 100",
         "evidence": [r.citation()]}
        for r in records
        if r.normal_value is not None and r.normal_value > 0
        and r.normal_period and r.normal_source and r.normal_source_url
    ]


def msp_gaps(prices: list[MandiPrice], supports: list[MSPObservation]) -> list[dict]:
    gaps = []
    for price in prices:
        compatible = [
            msp for msp in supports
            if price.commodity.casefold() == msp.crop.casefold()
            and price.unit == msp.unit and price.variety == msp.variety
            and price.season == msp.season
            and (msp.state is None or msp.state == price.state)
            and (msp.period == price.period or (
                msp.effective_from and msp.effective_to
                and msp.effective_from.isoformat() <= price.period <= msp.effective_to.isoformat()
            ))
        ]
        if len(compatible) != 1:
            continue
        msp = compatible[0]
        gaps.append({"indicator": "msp_price_gap", "value": price.value - msp.value,
                     "unit": price.unit, "period": price.period, "formula": "mandi modal price - MSP",
                     "evidence": [price.citation(), msp.citation()]})
    return gaps
