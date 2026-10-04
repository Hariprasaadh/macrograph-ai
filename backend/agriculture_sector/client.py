"""Four configurable upstream MCP adapters. Only Agriculture MCP calls these."""
from __future__ import annotations

import asyncio
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import logging
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
import httpx

logger = logging.getLogger(__name__)
from jsonschema import validate
from pydantic import BaseModel, ConfigDict, Field
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import settings
from .models import AgricultureQuery, SourceCategory


class SourceUnavailable(Exception):
    def __init__(self, message: str, code: str = "source_error"):
        super().__init__(message)
        self.code = code


FAOSTAT_MCP_URL = "https://faostat.caseyjhand.com/mcp"


class ToolBinding(BaseModel):
    """Deployment mapping based on an inspected MCP schema, never LLM-selected."""
    model_config = ConfigDict(extra="forbid")
    tool: str
    dataset: str
    source_url: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    query_fields: dict[str, str] = Field(default_factory=dict)
    fields: dict[str, str] = Field(default_factory=dict)
    unit: str | None = None
    frequency: str | None = None
    metadata_arguments: dict[str, Any] = Field(default_factory=dict)
    indicators_arguments: dict[str, Any] = Field(default_factory=dict)


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    transport: str | dict[str, Any] | Any
    authority: str
    # Mandatory acknowledgement after disabling any upstream demo/sample mode.
    live_data_verified: bool = False
    operations: dict[str, ToolBinding] = Field(default_factory=dict)


class SourcePayload(BaseModel):
    data: Any
    source: str
    category: SourceCategory
    binding: ToolBinding
    retrieved_at: datetime
    warnings: list[str] = Field(default_factory=list)


# Use the supplied ready-made server, but retain dates that its prose tool drops.
# This runs inside that server's stdio process, not in the agent.
agmarknet_mcp_server = FastMCP("Agmarknet MCP Server")

@agmarknet_mcp_server.tool()
def get_verified_commodity_prices(
    commodity: str,
    state: str | None = None,
    district: str | None = None,
    market: str | None = None,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    ceda_key = settings.CEDA_API_KEY.get_secret_value()
    data_gov_key = settings.DATA_GOV_IN_API_KEY.get_secret_value()

    COMMODITY_DEFAULT_STATES = {
        "onion": "Maharashtra", "tomato": "Maharashtra", "potato": "Uttar Pradesh",
        "wheat": "Uttar Pradesh", "rice": "West Bengal", "paddy": "West Bengal",
        "cotton": "Gujarat", "maize": "Karnataka", "soybean": "Madhya Pradesh",
        "pulses": "Madhya Pradesh", "gram": "Madhya Pradesh", "mustard": "Rajasthan",
    }
    if not state:
        state = COMMODITY_DEFAULT_STATES.get((commodity or "").lower(), "Maharashtra")

    if date:
        start_date = end_date = date

    if ceda_key:
        from agmarknet_mcp.api import CedaClient
        client = CedaClient(api_key=ceda_key, timeout=45.0)
        try:
            rows = client.get_prices(
                commodity, state, district, from_date=start_date, to_date=end_date,
                # CEDA is a historical snapshot and may publish with a long lag.
                # Search a full year so "latest" means latest available source data.
                default_lookback_days=365,
            )
            note = (f"CEDA Agri Market data is historical and periodically updated ({state}); "
                    "the observation period shown is not today's price.")
            return {"records": [
                {**row.model_dump(), "frequency": "daily", "unit": "INR/quintal",
                 "freshness": "source_snapshot", "source_note": note}
                for row in rows
            ], "provider": "CEDA", "sample": False}
        except Exception as exc:
            logger.warning("CEDA live fetch error: %s", exc)
            if not data_gov_key or data_gov_key == "your_api_key_here":
                raise SourceUnavailable(f"CEDA Agri Market provider error: {exc}", "source_error") from exc

    if data_gov_key and data_gov_key != "your_api_key_here":
        params = {"api-key": data_gov_key, "format": "json", "limit": 1000}
        if commodity:
            params["filters[commodity]"] = commodity
        if state:
            params["filters[state]"] = state
        if district:
            params["filters[district]"] = district
        if market:
            params["filters[market]"] = market
        if date:
            params["filters[arrival_date]"] = date
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        with httpx.Client(timeout=45.0) as http_client:
            resp = http_client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        return {"records": data.get("records", []), "use_mock": False}

    raise SourceUnavailable("CEDA_API_KEY or DATA_GOV_IN_API_KEY is required", "not_configured")


def ready_made_config(category: SourceCategory) -> SourceConfig:
    """Verified tool/schema mappings, never stored economic observations."""
    if not settings.AGRICULTURE_USE_READYMADE_SOURCES:
        raise SourceUnavailable(f"{category} MCP is not configured", "not_configured")
    if category == "mospi":
        operations = {}
        for operation, code, fields in (
            ("crop_production", 51, {"crop": "commodity", "period": "year"}),
            ("crop_area", 50, {"crop": "foodgrains", "period": "year"}),
            ("irrigation", 44, {"period": "year", "irrigation_source": "source_irrigation", "measure": "sub_indicator"}),
            ("fertilizer", 55, {"period": "year", "fertilizer": "emission_source"}),
        ):
            operations[operation] = ToolBinding(
                tool="get_data", dataset="ENVSTATS", source_url=settings.AGRICULTURE_MOSPI_URL,
                arguments={"dataset": "ENVSTATS", "filters": {"indicator_code": code, "Format": "JSON", "limit": 100}},
                metadata_arguments={"dataset": "ENVSTATS", "indicator_code": code},
                query_fields={"state": "filters.state", "period": "filters.year",
                              **({"crop": "filters.commodity"} if code == 51 else {})},
                fields=fields, frequency="annual",
            )
        return SourceConfig(transport=settings.AGRICULTURE_MOSPI_URL,
                            authority="MoSPI eSankhyiki", live_data_verified=True, operations=operations)
    if category == "weather_mcp":
        path = Path(settings.AGRICULTURE_WEATHER_SCRIPT)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if not path.is_file():
            raise SourceUnavailable("Build the supplied Indian Weather MCP server; see Agriculture README", "not_configured")
        return SourceConfig(
            transport={"mcpServers": {"weather": {"command": settings.AGRICULTURE_WEATHER_COMMAND, "args": [str(path)]}}},
            authority="Open-Meteo via Indian Weather MCP (not IMD)", live_data_verified=True,
            operations={
                "weather_current": ToolBinding(
                    tool="get_current_weather", dataset="Open-Meteo current weather",
                    source_url="https://api.open-meteo.com/v1/forecast",
                    query_fields={"location": "location", "city": "location", "state": "location"}),
                "weather_forecast": ToolBinding(
                    tool="get_weather_forecast", dataset="Open-Meteo weather forecast",
                    source_url="https://api.open-meteo.com/v1/forecast",
                    query_fields={"location": "location", "city": "location", "state": "location"}),
                "weather_historical": ToolBinding(
                    tool="get_historical_weather", dataset="Open-Meteo historical daily weather",
                    source_url="https://archive-api.open-meteo.com/v1/archive",
                    query_fields={"location": "location", "city": "location", "state": "location",
                                  "start_date": "start_date", "end_date": "end_date"}),
                "weather_agriculture": ToolBinding(
                    tool="get_agriculture_weather", dataset="Open-Meteo agricultural weather",
                    source_url="https://archive-api.open-meteo.com/v1/archive",
                    query_fields={"location": "location", "city": "location", "state": "location",
                                  "start_date": "start_date", "end_date": "end_date"}),
                "rainfall": ToolBinding(
                    tool="get_historical_weather_india", dataset="Open-Meteo historical daily precipitation",
                    source_url="https://archive-api.open-meteo.com/v1/archive",
                    query_fields={"city": "city", "days": "days"}),
            },
        )
    if category == "faostat":
        return SourceConfig(
            transport=FAOSTAT_MCP_URL, authority="FAOSTAT, Food and Agriculture Organization of the United Nations",
            live_data_verified=True,
            operations={"crop_production": ToolBinding(
                tool="faostat_query_observations", dataset="QCL - Production: Crops and livestock products",
                source_url=FAOSTAT_MCP_URL, query_fields={
                    "crop": "item", "state": "area", "country": "area",
                    "start_date": "year_start", "end_date": "year_end",
                }, fields={"crop": "item", "state": "area", "period": "year",
                           "value": "value", "unit": "unit", "quality_flag": "flag"},
                unit="t", frequency="annual",
            ), "crop_list": ToolBinding(
                tool="faostat_resolve_codes", dataset="QCL crop items",
                source_url=FAOSTAT_MCP_URL, frequency="catalog",
            )},
        )
    if category == "agmarknet":
        ceda_key = settings.CEDA_API_KEY.get_secret_value()
        data_gov_key = settings.DATA_GOV_IN_API_KEY.get_secret_value()
        if ceda_key:
            authority = "CEDA Agri Market Data, Ashoka University (Agmarknet-derived)"
            source_url = "https://api.ceda.ashoka.edu.in/v1/agmarknet/prices"
            dataset = "CEDA Agri Market historical prices"
        elif data_gov_key and data_gov_key != "your_api_key_here":
            authority = "Directorate of Marketing & Inspection (Agmarknet via Data.gov.in)"
            source_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
            dataset = "9ef84268-d588-465a-a308-a864a43d0070"
        else:
            raise SourceUnavailable(
                "CEDA_API_KEY or DATA_GOV_IN_API_KEY is required; sample mode is disabled",
                "not_configured",
            )
        return SourceConfig(
            transport=agmarknet_mcp_server,
            authority=authority,
            live_data_verified=True, operations={"mandi_price": ToolBinding(
                tool="get_verified_commodity_prices", dataset=dataset,
                source_url=source_url,
                query_fields={
                    "commodity": "commodity", "state": "state", "district": "district",
                    "period": "date", "start_date": "start_date", "end_date": "end_date",
                },
                unit="INR/quintal", frequency="daily",
            )},
        )
    if settings.AGRICULTURE_OGD_RESOURCES:
        return SourceConfig(transport="ogd", authority="Government of India via Data.gov.in",
                            live_data_verified=True, operations=settings.AGRICULTURE_OGD_RESOURCES)
    raise SourceUnavailable("Data.gov.in MCP/resource mappings are not configured", "not_configured")


def unwrap(result: Any) -> Any:
    if result.is_error:
        raise SourceUnavailable("Upstream MCP reported a tool error")
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    data = getattr(result, "data", None)
    if data is not None:
        return data.model_dump(mode="json") if hasattr(data, "model_dump") else data
    for block in result.content:
        if hasattr(block, "text"):
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                continue
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    if text:
        return text
    raise SourceUnavailable("Upstream tool did not return data", "invalid_data")


def reject_sample_data(data: Any) -> None:
    """Reject explicit demo, estimated or mock flags anywhere in a response."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in {"mock", "is_mock", "use_mock", "sample", "is_sample", "estimated"} and value not in (False, None, "", 0):
                raise SourceUnavailable("Sample/estimated data is not admissible", "invalid_data")
            if key.lower() in {"source", "mode", "data_status"} and any(
                token in str(value).lower() for token in ("mock", "sample", "demo", "synthetic")
            ):
                raise SourceUnavailable("Sample data is not admissible", "invalid_data")
            reject_sample_data(value)
    elif isinstance(data, list):
        for item in data:
            reject_sample_data(item)


class AgricultureMCPClient:
    category: SourceCategory

    def __init__(self, config: SourceConfig | None = None):
        self._config = config

    def configuration(self) -> SourceConfig:
        raw = settings.AGRICULTURE_MCP_SOURCES.get(self.category)
        config = self._config or (SourceConfig.model_validate(raw) if raw else ready_made_config(self.category))
        if not config.live_data_verified:
            raise SourceUnavailable("Live mode must be verified; demo sources are disabled", "not_configured")
        return config

    async def _invoke(self, session: Client, schemas: dict, name: str, arguments: dict) -> Any:
        if name not in schemas:
            raise SourceUnavailable(f"MCP tool '{name}' is not exposed", "unsupported")
        missing = [field for field in schemas[name].get("required", []) if field not in arguments]
        if missing:
            raise SourceUnavailable(
                "Required source scope is missing: " + ", ".join(missing), "missing_data")
        validate(arguments, schemas[name])
        try:
            response = await session.call_tool(name, arguments)
        except ToolError as exc:
            # FastMCP wraps upstream network exceptions as ToolError. Recover
            # only the transient classes so the outer bounded retry can help;
            # never expose the raw upstream message (which may contain internals).
            message = str(exc).casefold()
            if "timed out" in message or "timeout" in message:
                raise TimeoutError("Upstream MCP request timed out") from exc
            if "network error" in message or "connection" in message:
                raise ConnectionError("Upstream MCP connection failed") from exc
            raise SourceUnavailable("Upstream MCP reported a tool error") from exc
        result = unwrap(response)
        reject_sample_data(result)
        return result

    async def before_fetch(self, session: Client, schemas: dict, binding: ToolBinding) -> dict | None:
        return None

    def resolve_arguments(self, arguments: dict, metadata: dict | None) -> dict:
        return arguments

    async def fetch(self, operation: str, query: AgricultureQuery) -> SourcePayload:
        config = self.configuration()
        binding = config.operations.get(operation)
        if binding is None:
            raise SourceUnavailable(f"{self.category} has no verified mapping for {operation}", "unsupported")
        arguments = json.loads(json.dumps(binding.arguments))
        supplied = query.model_dump(mode="json", exclude_none=True)
        for field, destination in binding.query_fields.items():
            if field in supplied:
                target = arguments
                path = destination.split(".")
                for key in path[:-1]:
                    target = target.setdefault(key, {})
                target[path[-1]] = supplied[field]
        # Retry only transient connection/timeouts, not invalid schemas or empty datasets.
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.2, max=1),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)), reraise=True,
        ):
            with attempt:
                async with asyncio.timeout(settings.AGRICULTURE_MCP_TIMEOUT):
                    async with Client(config.transport, timeout=settings.AGRICULTURE_MCP_TIMEOUT) as session:
                        schemas = {
                            tool.name: (
                                tool.input_schema if hasattr(tool, "input_schema")
                                else getattr(tool, "inputSchema", {})
                            ) for tool in await session.list_tools()
                        }
                        metadata = await self.before_fetch(session, schemas, binding)
                        resolved = self.resolve_arguments(arguments, metadata)
                        data = await self._invoke(session, schemas, binding.tool, resolved)
                        if self.category == "mospi" and isinstance(data, dict) and data.get("data"):
                            pages = int(data.get("meta_data", {}).get("totalPages", 1))
                            rows = list(data["data"])
                            for page in range(2, min(pages, 10) + 1):
                                paged = json.loads(json.dumps(resolved))
                                paged["filters"]["page"] = page
                                response = await self._invoke(session, schemas, binding.tool, paged)
                                if not isinstance(response, dict) or not isinstance(response.get("data"), list):
                                    raise SourceUnavailable("MoSPI pagination failed", "source_error")
                                rows.extend(response["data"])
                            data = {**data, "data": rows}
        warnings = []
        if isinstance(data, dict) and isinstance(data.get("meta_data"), dict):
            if data["meta_data"].get("totalRecords", 0) > len(data.get("data", [])):
                warnings.append("Source response is paginated; analysis covers returned observations only")
        return SourcePayload(data=data, source=config.authority, category=self.category,
                             binding=binding.model_copy(update={"arguments": resolved}),
                             retrieved_at=datetime.now(timezone.utc), warnings=warnings)


class AgmarknetClient(AgricultureMCPClient):
    category = "agmarknet"


class FaostatClient(AgricultureMCPClient):
    category = "faostat"

    async def fetch(self, operation: str, query: AgricultureQuery) -> SourcePayload:
        config = self.configuration()
        binding = config.operations.get(operation)
        if binding is None:
            raise SourceUnavailable(f"FAOSTAT has no verified mapping for {operation}", "unsupported")
        if operation == "crop_list":
            async with Client(config.transport, timeout=settings.AGRICULTURE_MCP_TIMEOUT) as session:
                result = await session.call_tool("faostat_resolve_codes", {
                    "domain": "QCL", "dimension": "item", "limit": 100})
                data = unwrap(result)
            matches = data.get("matches", []) if isinstance(data, dict) else []
            if not matches:
                raise SourceUnavailable("FAOSTAT returned no crop items", "missing_data")
            return SourcePayload(
                data={"records": [{"name": row["name"], "period": "catalog"} for row in matches]},
                source=config.authority, category=self.category,
                binding=binding, retrieved_at=datetime.now(timezone.utc),
            )
        crop = query.crop or query.commodity
        if not crop:
            raise SourceUnavailable("FAOSTAT crop production requires a crop or commodity", "missing_data")
        area = query.country or query.state or "India"
        year_start = query.start_year or (query.start_date.year if query.start_date else 1961)
        year_end = query.end_year or (query.end_date.year if query.end_date else datetime.now(timezone.utc).year)
        try:
            async with Client(config.transport, timeout=settings.AGRICULTURE_MCP_TIMEOUT) as session:
                async def call(name: str, arguments: dict[str, Any]) -> Any:
                    result = await session.call_tool(name, arguments)
                    if result.is_error:
                        raise SourceUnavailable(f"FAOSTAT tool {name} returned an error", "source_error")
                    return unwrap(result)

                area_result = await call("faostat_resolve_codes", {
                    "domain": "QCL", "dimension": "area", "query": area, "limit": 20})
                item_result = await call("faostat_resolve_codes", {
                    "domain": "QCL", "dimension": "item", "query": crop, "limit": 20})
                element_result = await call("faostat_resolve_codes", {
                    "domain": "QCL", "dimension": "element", "query": "Production", "limit": 20})

                def matches(result: Any) -> list[dict[str, Any]]:
                    if isinstance(result, dict):
                        return result.get("matches", [])
                    return []

                area_matches = [row for row in matches(area_result)
                                if str(row.get("name", "")).casefold() == area.casefold()
                                and row.get("kind") != "aggregate"]
                item_rows = matches(item_result)
                item_matches = [row for row in item_rows
                                if str(row.get("name", "")).casefold() == crop.casefold()]
                if not item_matches:
                    candidates = [row for row in item_rows
                                  if str(row.get("name", "")).casefold().startswith(crop.casefold())
                                  and "oil" not in str(row.get("name", "")).casefold()]
                    if len(candidates) == 1:
                        item_matches = candidates
                element_matches = [row for row in matches(element_result)
                                   if str(row.get("name", "")).casefold() == "production"]
                if not area_matches:
                    raise SourceUnavailable(f"FAOSTAT could not resolve area '{area}'", "missing_data")
                if not item_matches:
                    raise SourceUnavailable(f"FAOSTAT could not resolve crop '{crop}'", "missing_data")
                if not element_matches:
                    raise SourceUnavailable("FAOSTAT has no Production element for QCL", "unsupported")
                data = await call("faostat_query_observations", {
                    "domain": "QCL", "area_codes": [int(area_matches[0]["code"])],
                    "item_codes": [int(item_matches[0]["code"])],
                    "element_codes": [int(element_matches[0]["code"])],
                    "year_start": year_start, "year_end": year_end, "limit": 1000,
                })
            observations = data.get("observations", []) if isinstance(data, dict) else []
            if not observations:
                raise SourceUnavailable("FAOSTAT returned no crop-production observations", "missing_data")
            observations = sorted(observations, key=lambda row: int(row["year"]))
            if query.history_years:
                observations = observations[-query.history_years:]
            return SourcePayload(
                data={"records": [{
                    "crop": crop, "state": row.get("area"),
                    "period": str(int(row["year"])), "value": row.get("value"),
                    "unit": row.get("unit"), "quality_flag": row.get("flag"),
                    "frequency": "annual",
                } for row in observations]},
                source=config.authority, category=self.category,
                binding=binding.model_copy(update={"arguments": {
                    "domain": "QCL", "area": area, "crop": crop,
                    "canonical_item": item_matches[0].get("name"),
                    "element": "Production", "year_start": year_start, "year_end": year_end,
                }}), retrieved_at=datetime.now(timezone.utc),
            )
        except SourceUnavailable:
            raise
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise TimeoutError("FAOSTAT MCP request timed out") from exc
        except Exception as exc:
            logger.warning("FAOSTAT crop fetch failed: %s", type(exc).__name__)
            raise SourceUnavailable("FAOSTAT crop query failed", "source_error") from exc


class MoSPIClient(AgricultureMCPClient):
    category = "mospi"

    async def before_fetch(self, session: Client, schemas: dict, binding: ToolBinding) -> dict:
        # All filters/codes come from a deployment mapping verified against metadata.
        catalog = await self._invoke(session, schemas, "list_datasets", {})
        if binding.dataset.lower() not in json.dumps(catalog).lower():
            raise SourceUnavailable("Configured agriculture dataset is absent from MoSPI catalog", "unsupported")
        indicators = await self._invoke(session, schemas, "get_indicators",
                                        binding.indicators_arguments or {"dataset": binding.dataset})
        code = binding.metadata_arguments.get("indicator_code")
        if code is not None and not any(row.get("indicator_code") == code for row in indicators.get("data", [])):
            raise SourceUnavailable("Configured indicator is absent from MoSPI indicators", "unsupported")
        metadata = await self._invoke(session, schemas, "get_metadata",
                                     binding.metadata_arguments or {"dataset": binding.dataset})
        if not metadata:
            raise SourceUnavailable("MoSPI returned no dataset metadata", "missing_data")
        return metadata

    def resolve_arguments(self, arguments: dict, metadata: dict | None) -> dict:
        resolved = json.loads(json.dumps(arguments))
        values = (metadata or {}).get("data", {})
        for key, value in resolved.get("filters", {}).items():
            options = values.get(key)
            if isinstance(options, list):
                matches = [row["id"] for row in options if str(value).casefold()
                           in {str(row.get("id")).casefold(), str(row.get("label")).casefold()}]
                if len(matches) != 1:
                    raise SourceUnavailable(f"Requested {key} is not present in MoSPI metadata", "missing_data")
                resolved["filters"][key] = matches[0]
        return resolved


class WeatherClient(AgricultureMCPClient):
    category = "weather_mcp"


class DataGovClient(AgricultureMCPClient):
    category = "data_gov"

    async def fetch(self, operation: str, query: AgricultureQuery) -> SourcePayload:
        """OGD HTTP is permitted only behind Agriculture MCP, never in agents."""
        config = self.configuration()
        if config.transport != "ogd":
            return await super().fetch(operation, query)
        binding = config.operations.get(operation)
        if binding is None:
            raise SourceUnavailable(f"No verified Data.gov.in resource for {operation}", "unsupported")
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", binding.tool):
            raise SourceUnavailable("OGD binding.tool must be a verified resource UUID", "invalid_data")
        key = settings.DATA_GOV_IN_API_KEY.get_secret_value()
        if not key:
            raise SourceUnavailable("DATA_GOV_IN_API_KEY is required for Data.gov.in", "not_configured")
        url = "https://api.data.gov.in/resource/" + binding.tool
        params = {**binding.arguments, "api-key": key, "format": "json", "limit": 1000}
        for field, upstream in binding.query_fields.items():
            value = query.model_dump(mode="json", exclude_none=True).get(field)
            if value is not None:
                params[f"filters[{upstream}]"] = value
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.2, max=1),
            retry=retry_if_exception_type(httpx.TransportError), reraise=True,
        ):
            with attempt:
                try:
                    async with httpx.AsyncClient(timeout=settings.AGRICULTURE_MCP_TIMEOUT) as client:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                except httpx.TimeoutException as exc:
                    if attempt.retry_state.attempt_number >= 2:
                        raise TimeoutError("Data.gov.in request timed out") from exc
                    raise
                except httpx.HTTPStatusError as exc:
                    raise SourceUnavailable("Data.gov.in rejected the resource request") from exc
        reject_sample_data(data)
        warnings = []
        if int(data.get("total", 0)) > len(data.get("records", [])):
            warnings.append("OGD response is truncated; analysis covers returned observations only")
        return SourcePayload(
            data=data, source=config.authority, category=self.category,
            binding=binding.model_copy(update={"source_url": url}),
            retrieved_at=datetime.now(timezone.utc), warnings=warnings,
        )
