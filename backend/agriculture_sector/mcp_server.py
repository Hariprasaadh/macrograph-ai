"""Single Agriculture FastMCP server; data retrieval only."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from fastmcp import FastMCP

from .client import AgmarknetClient, DataGovClient, FaostatClient, MoSPIClient, SourceUnavailable, WeatherClient
from .models import AgricultureQuery, AgricultureResult, SourceError
from .parsers import PARSERS, filter_records, msp_gaps, rainfall_anomalies, series_changes

logger = logging.getLogger(__name__)
mcp_server = FastMCP("Agriculture Sector MCP Server", instructions=(
    "Retrieve sourced Indian agriculture observations only. No CPI, WPI, GDP/GVA, "
    "banking, equities or fiscal indicators. Unavailable sources produce structured results."
))

CLIENTS = {
    "agmarknet": AgmarknetClient(), "mospi": MoSPIClient(),
    "weather_mcp": WeatherClient(), "data_gov": DataGovClient(), "faostat": FaostatClient(),
}
SOURCE_ROUTING = {
    "crop_production": ("faostat", "mospi", "data_gov"),
    "crop_list": ("faostat",),
    "crop_yield": ("mospi", "data_gov"),
    "crop_area": ("mospi", "data_gov"),
    "mandi_price": ("agmarknet",),
    "market_arrivals": ("agmarknet",),
    "msp": ("data_gov",),
    "rainfall": ("weather_mcp",),
    "weather_current": ("weather_mcp",),
    "weather_forecast": ("weather_mcp",),
    "weather_historical": ("weather_mcp",),
    "weather_agriculture": ("weather_mcp",),
    "monsoon": ("weather_mcp",),
    "fertilizer": ("mospi", "data_gov"),
    "irrigation": ("mospi", "data_gov"),
    "scheme": ("data_gov",),
}
# Each public logical tool resolves only to the declared agriculture dataset.
OPERATIONS = {
    "get_crop_production": "crop_production", "get_crop_yield": "crop_yield",
    "get_crop_list": "crop_list",
    "get_crop_area": "crop_area", "get_production_trend": "crop_production",
    "get_state_crop_production": "crop_production",
    "get_mandi_price": "mandi_price", "get_mandi_price_trend": "mandi_price",
    "compare_mandi_prices": "mandi_price", "get_market_arrivals": "market_arrivals",
    "get_msp": "msp", "get_msp_history": "msp", "get_msp_gap": "msp",
    "get_rainfall": "rainfall", "get_rainfall_anomaly": "rainfall",
    "get_monsoon_status": "monsoon", "get_weather_history": "rainfall",
    "get_current_weather": "weather_current", "get_weather_forecast": "weather_forecast",
    "get_historical_weather": "weather_historical", "get_agriculture_weather": "weather_agriculture",
    "get_fertilizer_consumption": "fertilizer", "get_irrigation_area": "irrigation",
    "get_agriculture_scheme": "scheme",
}


async def _retrieve(operation: str, query: AgricultureQuery, tool: str) -> AgricultureResult:
    errors = []
    for source in SOURCE_ROUTING[operation]:
        try:
            # Trend tools may have separate history bindings; no invented tool names.
            client = CLIENTS[source]
            binding_key = operation
            if tool in client.configuration().operations:
                binding_key = tool
            payload = await client.fetch(binding_key, query)
            errors.extend(SourceError(source=source, code="missing_data", message=message)
                          for message in payload.warnings)
            parsed = PARSERS[operation](payload, tool)
            records = parsed if operation.startswith("weather_") else filter_records(parsed, query)
            if operation == "rainfall" and query.days:
                records = records[-query.days:]
            if not records:
                raise SourceUnavailable("No matching observations returned", "missing_data")
            return AgricultureResult(tool=tool, status="partial" if errors else "available",
                                     records=records, errors=errors)
        except TimeoutError:
            errors.append(SourceError(source=source, code="timeout", message="MCP request timed out"))
        except SourceUnavailable as exc:
            errors.append(SourceError(source=source, code=exc.code, message=str(exc)))
        except Exception as exc:
            # Do not put credentials or raw transport exception messages in API responses.
            logger.warning("Agriculture %s normalization/retrieval failed: %s", source, type(exc).__name__)
            errors.append(SourceError(source=source, code="invalid_data",
                                      message="Source failed or returned data that did not satisfy the contract"))
    return AgricultureResult(tool=tool, status="unavailable", errors=errors)


def _missing_analysis(result: AgricultureResult, message: str) -> AgricultureResult:
    result.status = "partial" if result.records else "unavailable"
    result.errors.append(SourceError(source="agriculture_sector", code="missing_data", message=message))
    return result


async def run_tool(tool: str, query: AgricultureQuery) -> AgricultureResult:
    """Dispatch a validated agriculture tool and preserve all fallback attempts."""
    operation = OPERATIONS[tool]
    if tool == "get_msp_gap":
        support_scope = query.model_copy(update={
            "period": None, "start_date": None, "end_date": None,
            "market": None, "district": None, "state": None,
        })
        prices, supports = await asyncio.gather(
            _retrieve("mandi_price", query, tool), _retrieve("msp", support_scope, tool))
        if prices.records:
            latest_price_period = max(record.period for record in prices.records)
            prices.records = [
                record for record in prices.records if record.period == latest_price_period]
        records = prices.records + supports.records
        result = AgricultureResult(tool=tool, status="available" if records else "unavailable",
                                   records=records, errors=prices.errors + supports.errors)
        result.derived = msp_gaps(prices.records, supports.records)
        if not result.derived:
            return _missing_analysis(result, "No compatible price/MSP pair: crop, variety, units and effective period must match")
        if result.errors:
            result.status = "partial"
        return result
    result = await _retrieve(operation, query, tool)
    if not result.records:
        return result
    if operation == "mandi_price":
        if tool in {"get_mandi_price", "compare_mandi_prices"}:
            latest_period = max(record.period for record in result.records)
            result.records = [record for record in result.records if record.period == latest_period]
        elif tool == "get_mandi_price_trend":
            try:
                latest = max(date.fromisoformat(record.period) for record in result.records)
                # An N-day window is inclusive of the latest day, so subtract
                # N-1 days (for example, 30 days ending Oct 30 starts Oct 1).
                cutoff = latest - timedelta(days=query.days - 1)
                result.records = [
                    record for record in result.records
                    if date.fromisoformat(record.period) >= cutoff
                ]
            except ValueError:
                return _missing_analysis(result, "Mandi trend requires ISO-dated observations")
    if tool in {"get_production_trend", "get_mandi_price_trend", "get_msp_history"}:
        result.derived = await asyncio.to_thread(series_changes, result.records)
        if not result.derived:
            _missing_analysis(result, "At least two distinct periods of the same series are required for a trend")
    elif tool == "get_rainfall_anomaly":
        result.derived = rainfall_anomalies(result.records)
        if not result.derived:
            _missing_analysis(result, "A sourced climatological normal, baseline period and nonzero normal are required")
    elif tool in {"compare_mandi_prices", "get_state_crop_production"}:
        # Compare only within identical periods, commodities, units and varieties.
        groups: dict[tuple, list] = {}
        for record in result.records:
            key = (record.period, record.unit, record.crop, record.commodity,
                   record.variety, record.season, record.dataset, record.source)
            groups.setdefault(key, []).append(record)
        for group in groups.values():
            if len(group) < 2:
                continue
            dimension = "market" if tool == "compare_mandi_prices" else "state"
            locations = [getattr(r, dimension) for r in group]
            if None in locations or len(set(locations)) != len(locations):
                continue
            ordered = sorted(group, key=lambda r: r.value, reverse=tool == "get_state_crop_production")
            result.derived.append({
                "indicator": "comparison", "scope": "returned matching observations only",
                "period": group[0].period, "unit": group[0].unit,
                "ranking": [r.model_dump(mode="json") for r in ordered],
            })
        if not result.derived:
            _missing_analysis(result, "No comparable markets/states in the same period and series")
    return result


def _register(name: str) -> Any:
    async def fetch(query: AgricultureQuery) -> AgricultureResult:
        return await run_tool(name, query)
    fetch.__name__ = name
    fetch.__doc__ = (
        f"{name.replace('_', ' ').capitalize()} using Agriculture MCP sources. "
        "Supply crop/commodity and geography/date scope in query. "
        "Returns sourced records, derived comparisons and explicit source errors."
    )
    mcp_server.tool(name=name)(fetch)
    return fetch


# Register the 19 declared tools with identical typed query and result contracts.
for _name in OPERATIONS:
    globals()[_name] = _register(_name)

__all__ = ["mcp_server", *OPERATIONS]
