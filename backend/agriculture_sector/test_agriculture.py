"""Offline tests. All values/dates below are fictional test fixtures, not economic facts."""
from datetime import date, datetime, timezone
from importlib import import_module
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client, FastMCP
from pydantic import ValidationError

from agriculture_sector.agent import (
    _resolve_weather_dates, agriculture_agent_node, query_parameters, select_agriculture_tools,
)
from agriculture_sector.client import (
    AgmarknetClient, MoSPIClient, SourceConfig, SourcePayload, SourceUnavailable, ToolBinding,
)
from agriculture_sector.models import AgricultureObservation, AgricultureQuery, AgricultureResult
from agriculture_sector.parsers import (
    parse_mandi_response, parse_crop_production_response, parse_msp_response,
    parse_rainfall_response, parse_weather_response, parse_monsoon_response, msp_gaps, series_changes,
)

server = import_module("agriculture_sector.mcp_server")
NOW = datetime(2001, 1, 1, tzinfo=timezone.utc)
BASE = {"period": "2000-01-01", "unit": "test-units", "frequency": "daily"}
ROWS = {
    "mandi_price": [{**BASE, "commodity": "wheat", "market": "Fixture Market", "modal_price": 100}],
    "crop_production": [{**BASE, "crop": "wheat", "production": 100}],
    "crop_yield": [{**BASE, "crop": "wheat", "yield": 100}],
    "crop_area": [{**BASE, "crop": "wheat", "area": 100}],
    "market_arrivals": [{**BASE, "commodity": "wheat", "market": "Fixture Market", "arrivals": 100}],
    "msp": [{**BASE, "crop": "wheat", "msp": 80}],
    "rainfall": [{**BASE, "rainfall": 100, "normal_value": 125, "normal_period": "1961-1990",
                  "normal_source": "Fixture climatology", "normal_source_url": "https://example.test/normal"}],
    "monsoon": [{"period": "2000-01-01", "state": "Fixture State", "monsoon_status": "fixture status"}],
    "fertilizer": [{**BASE, "fertilizer": "Fixture fertilizer", "consumption": 100}],
    "irrigation": [{**BASE, "irrigated_area": 100}],
    "scheme": [{"period": "2000", "name": "Fixture scheme", "description": "Fictional test policy"}],
    "crop_list": [{"period": "catalog", "name": "Wheat"}, {"period": "catalog", "name": "Rice"}],
}
WEATHER_ROWS = [{"period": "2026-09-28", "metric": "temperature_max", "value": 32,
                 "unit": "°C", "location": "Tamil Nadu", "display_name": "Tamil Nadu, India",
                 "latitude": 11.0, "longitude": 78.0, "frequency": "daily"}]


def test_agmarket_api_queries_select_mandi_prices():
    for query in ("agri market API", "agricultural market API", "AgMarket API"):
        assert "get_mandi_price" in select_agriculture_tools(query)


def test_named_crop_production_selects_crop_production():
    assert "get_crop_production" in select_agriculture_tools("rice production")


def test_tamilnadu_alias_resolves_for_agmarket_queries():
    assert query_parameters("rice price in tamilnadu").state == "Tamil Nadu"


def payload(operation="mandi_price", rows=None, category="agmarknet"):
    if operation.startswith("weather_"):
        return SourcePayload(
            data={"records": WEATHER_ROWS}, source="Open-Meteo", category="weather_mcp",
            retrieved_at=NOW,
            binding=ToolBinding(tool=operation, dataset="Open-Meteo weather",
                                source_url="https://archive-api.open-meteo.com/v1/archive"),
        )
    return SourcePayload(
        data={"records": ROWS[operation] if rows is None else rows},
        source="IMD fixture authority" if operation == "monsoon" else "Fixture authority",
        category=category, retrieved_at=NOW,
        binding=ToolBinding(tool="fixture_tool", dataset="fixture-dataset",
                            source_url="https://example.test/dataset"),
    )


class FixtureClient:
    def __init__(self, category):
        self.category = category
        self.error = None
        self.rows = {}

    def configuration(self):
        return SimpleNamespace(operations={})

    async def fetch(self, operation, query):
        if self.error:
            raise self.error
        return payload(operation, self.rows.get(operation), self.category)


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    clients = {key: FixtureClient(key) for key in server.CLIENTS}
    monkeypatch.setattr(server, "CLIENTS", clients)
    return clients


async def call(tool, query=None):
    async with Client(server.mcp_server) as client:
        result = await client.call_tool(tool, {"query": query or {}})
    return AgricultureResult.model_validate(result.structured_content)


@pytest.mark.asyncio
async def test_get_mandi_price():
    result = await call("get_mandi_price")
    assert result.records[0].value == 100
    assert result.records[0].mcp_tool == "get_mandi_price"


@pytest.mark.asyncio
async def test_get_mandi_price_trend(sources):
    sources["agmarknet"].rows["mandi_price"] = [
        ROWS["mandi_price"][0], {**ROWS["mandi_price"][0], "period": "2000-02-01", "modal_price": 125}]
    # The two fictional observations are 31 days apart, so request a window
    # that deliberately contains both. Trend windows are anchored to the
    # source's latest observation rather than to today's date.
    result = await call("get_mandi_price_trend", {"days": 32})
    assert result.derived[0]["value"] == 25
    assert len(result.derived[0]["evidence"]) == 2


@pytest.mark.asyncio
async def test_get_crop_production():
    assert (await call("get_crop_production")).records[0].kind == "crop_production"


@pytest.mark.asyncio
async def test_get_crop_yield():
    assert (await call("get_crop_yield")).records[0].kind == "crop_yield"


@pytest.mark.asyncio
async def test_get_msp():
    assert (await call("get_msp")).records[0].value == 80


@pytest.mark.asyncio
async def test_get_rainfall():
    assert (await call("get_rainfall")).records[0].value == 100


@pytest.mark.asyncio
async def test_get_rainfall_anomaly():
    result = await call("get_rainfall_anomaly")
    assert result.derived[0]["value"] == -20
    assert result.derived[0]["evidence"][0]["normal_source_url"]


@pytest.mark.asyncio
async def test_get_monsoon_status():
    assert (await call("get_monsoon_status")).records[0].monsoon_status == "fixture status"


@pytest.mark.asyncio
async def test_all_tools_are_registered_and_callable():
    async with Client(server.mcp_server) as client:
        exposed = await client.list_tools()
    assert {t.name for t in exposed} == set(server.OPERATIONS)
    assert len(exposed) == 24
    for tool in server.OPERATIONS:
        result = await call(tool)
        assert result.records
        assert result.status in {"available", "partial"}


def test_parse_mandi_response():
    result = parse_mandi_response(payload(rows=[{**ROWS["mandi_price"][0], "period": "01/02/2000"}]))
    assert result[0].period == "2000-02-01"


def test_parse_mandi_response_keeps_modal_when_range_is_inconsistent():
    result = parse_mandi_response(payload(rows=[{
        **ROWS["mandi_price"][0], "min_price": 125, "modal_price": 100,
    }]))
    assert result[0].value == 100
    assert result[0].min_price is None


def test_parse_crop_production_response():
    assert parse_crop_production_response(payload("crop_production"))[0].crop == "wheat"


def test_parse_msp_response():
    assert parse_msp_response(payload("msp"))[0].value == 80


def test_parse_rainfall_response():
    assert parse_rainfall_response(payload("rainfall"))[0].normal_value == 125


def observation_fields():
    return dict(indicator="Fixture", value=100, unit="test-units", period="2000", frequency="annual",
                source="Fixture authority", source_category="data_gov", source_url="https://example.test",
                dataset="fixture", mcp_tool="get_crop_production", upstream_tool="fixture", retrieved_at=NOW)


def test_valid_agriculture_observation():
    assert AgricultureObservation(**observation_fields()).value == 100


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), None, "not numeric"])
def test_invalid_agriculture_observation(bad):
    with pytest.raises(ValidationError):
        AgricultureObservation(**{**observation_fields(), "value": bad})


def test_missing_required_source():
    data = observation_fields()
    del data["source"]
    with pytest.raises(ValidationError):
        AgricultureObservation(**data)


def test_agriculture_query_routing():
    assert select_agriculture_tools("What is food CPI?") == set()
    assert "get_msp_gap" in select_agriculture_tools("Are mandi prices above MSP?")
    assert "get_state_crop_production" in select_agriculture_tools("Which states produce the most rice?")


def test_price_query_routes_to_mandi():
    assert "get_mandi_price_trend" in select_agriculture_tools("How have onion prices changed?")
    scope = query_parameters("Compare tomato mandi prices in Pune")
    assert scope.district == "Pune" and scope.state == "Maharashtra"


def test_production_query_routes_to_production():
    assert "get_production_trend" in select_agriculture_tools("How has wheat production changed?")


def test_weather_query_routes_to_weather():
    assert "get_rainfall_anomaly" in select_agriculture_tools("How does rainfall compare with normal levels?")


def test_weather_temporal_routing_and_relative_dates():
    assert select_agriculture_tools("weather in Tamil Nadu") == {"get_current_weather"}
    assert select_agriculture_tools("weather forecast for Chennai") == {"get_weather_forecast"}
    assert select_agriculture_tools("weather in Tamil Nadu last week") == {"get_historical_weather"}
    assert select_agriculture_tools("rainfall in Tamil Nadu yesterday") == {"get_historical_weather"}
    assert _resolve_weather_dates("weather in Tamil Nadu last week", date(2026, 10, 4)) == (
        date(2026, 9, 28), date(2026, 10, 4))


def test_weather_query_parameters_include_explicit_range():
    parameters = query_parameters("weather in tamilnadu last week")
    assert parameters.state == "Tamil Nadu"
    assert parameters.start_date is not None and parameters.end_date is not None


def test_parse_structured_weather_response():
    result = parse_weather_response(payload("weather_historical"), "get_historical_weather")
    assert result[0].metric == "temperature_max"
    assert result[0].location == "Tamil Nadu"


@pytest.mark.asyncio
async def test_historical_weather_agent_calls_weather_tool(sources, monkeypatch):
    import agriculture_sector.agent as agent_module
    real_resolve = agent_module._resolve_weather_dates
    monkeypatch.setattr(
        agent_module, "_resolve_weather_dates", lambda query, today=None: real_resolve(query, date(2026, 10, 4)),
    )
    result = await agriculture_agent_node({"query": "weather in tamilnadu last week"})
    assert result["agriculture_sector_status"] == "completed"
    assert result["agriculture_sector_citations"]
    assert "28 Sep 2026" in result["agriculture_sector_analysis"]


@pytest.mark.asyncio
async def test_mcp_timeout(sources):
    sources["agmarknet"].error = TimeoutError()
    result = await call("get_mandi_price")
    assert result.status == "unavailable" and result.errors[0].code == "timeout"


@pytest.mark.asyncio
async def test_source_unavailable(sources):
    sources["agmarknet"].error = SourceUnavailable("Fixture outage")
    assert (await call("get_mandi_price")).status == "unavailable"


@pytest.mark.asyncio
async def test_missing_data(sources):
    sources["agmarknet"].rows["mandi_price"] = []
    assert (await call("get_mandi_price")).errors[0].code == "missing_data"


@pytest.mark.asyncio
async def test_no_source_no_answer(sources):
    for client in sources.values():
        client.error = SourceUnavailable("Fixture unconfigured", "not_configured")
    result = await agriculture_agent_node({"query": "What is the MSP for wheat?"})
    assert result["agriculture_sector_citations"] == []
    assert result["agriculture_sector_status"] == "unavailable"


@pytest.mark.asyncio
async def test_source_fallback_is_visible(sources):
    sources["faostat"].error = SourceUnavailable("Fixture FAOSTAT outage")
    sources["mospi"].error = SourceUnavailable("Fixture outage")
    result = await call("get_crop_production")
    assert result.status == "partial"
    assert result.records[0].source_category == "data_gov"
    assert result.errors[0].source == "faostat"


@pytest.mark.asyncio
async def test_crop_production_prefers_faostat(sources):
    result = await call("get_crop_production")
    assert result.records[0].source_category == "faostat"


@pytest.mark.asyncio
async def test_crop_production_falls_back_to_mospi(sources):
    sources["faostat"].error = SourceUnavailable("Fixture FAOSTAT outage")
    result = await call("get_crop_production")
    assert result.status == "partial"
    assert result.records[0].source_category == "mospi"


@pytest.mark.asyncio
async def test_scope_filters_provider_results():
    assert (await call("get_mandi_price", {"commodity": "onion"})).status == "unavailable"


def test_mock_payload_rejected():
    with pytest.raises(SourceUnavailable):
        parse_mandi_response(payload(rows=[{**ROWS["mandi_price"][0], "use_mock": True}]))


def test_weather_provider_not_mislabelled():
    p = payload("rainfall", category="weather_mcp")
    p.source = "Open-Meteo"
    p.data = {"city": "Fixture City", "daily_units": {"precipitation_sum": "mm"},
              "daily": {"time": ["2000-01-01"], "precipitation_sum": [0]}}
    assert parse_rainfall_response(p)[0].source == "Open-Meteo"
    with pytest.raises(SourceUnavailable):
        parse_monsoon_response(p)


@pytest.mark.asyncio
async def test_missing_normal_disables_anomaly(sources):
    sources["weather_mcp"].rows["rainfall"] = [{**BASE, "rainfall": 100}]
    result = await call("get_rainfall_anomaly")
    assert result.status == "partial" and not result.derived


def test_analytics_reject_incompatible_units_and_duplicate_periods():
    prices = parse_mandi_response(payload())
    supports = parse_msp_response(payload("msp"))
    assert msp_gaps(prices, supports)[0]["value"] == 20
    supports[0].unit = "different"
    assert msp_gaps(prices, supports) == []
    assert series_changes(prices + prices) == []


@pytest.mark.asyncio
async def test_agent_uses_mcp_and_returns_citations():
    result = await agriculture_agent_node({"query": "What is the current MSP for wheat?"})
    assert result["agriculture_sector_status"] == "completed"
    assert result["agriculture_sector_citations"][0]["mcp_tool"] == "get_msp"
    assert "2000-01-01" in result["agriculture_sector_analysis"]
    assert "## Agriculture diagnostic" in result["agriculture_sector_analysis"]
    assert "| Ref | Indicator | Scope | Observation | Period |" in result["agriculture_sector_analysis"]
    assert result["agriculture_sector_citations"][0]["citation_id"] == 1
    assert result["agriculture_sector_citations"][0]["provenance_hash"]


@pytest.mark.asyncio
async def test_trend_headline_compares_full_requested_window(sources):
    sources["agmarknet"].rows["mandi_price"] = [
        ROWS["mandi_price"][0],
        *[{**ROWS["mandi_price"][0], "period": f"2000-01-{day:02d}",
           "modal_price": 100 + day} for day in range(2, 11)],
        {**ROWS["mandi_price"][0], "period": "2000-02-01", "modal_price": 125},
    ]
    result = await agriculture_agent_node({
        "query": "How have wheat prices changed in the last 32 days?"})
    report = result["agriculture_sector_analysis"]
    assert "increased by 25 test-units (25.00%)" in report
    assert "from 2000-01-01 to 2000-02-01" in report
    assert "[1][10]" in report
    assert len(result["agriculture_sector_citations"]) == 10
    assert result["agriculture_sector_citations"][0]["citation_id"] == 1


@pytest.mark.asyncio
async def test_unavailable_report_does_not_invent_number(sources):
    sources["data_gov"].error = SourceUnavailable(
        "Data.gov.in MCP/resource mappings are not configured", "not_configured")
    result = await agriculture_agent_node({"query": "What is the current MSP for wheat?"})
    report = result["agriculture_sector_analysis"]
    assert "**Result: data unavailable.**" in report
    assert "No verified Data.gov.in dataset mapping" in report
    assert result["agriculture_sector_citations"] == []


def test_weather_readme_prose_is_parsed_as_dated_precipitation():
    weather = payload("rainfall", category="weather_mcp")
    weather.source = "Open-Meteo via Indian Weather MCP (not IMD)"
    weather.binding = weather.binding.model_copy(update={"tool": "get_historical_weather_india"})
    weather.data = (
        "Historical Weather for Fixture City, India (Last 2 days)\n"
        "2000-01-01: Max 30 C | Min 20 C | Rain 1.5mm | Max Wind 10 km/h\n"
        "2000-01-02: Max 31 C | Min 21 C | Rain 0mm | Max Wind 11 km/h"
    )
    records = parse_rainfall_response(weather)
    assert [(record.period, record.value) for record in records] == [
        ("2000-01-01", 1.5), ("2000-01-02", 0.0)]
    assert all("not IMD" in (record.source_note or "") for record in records)


def test_gateway_a2a_and_stream():
    import main
    with TestClient(main.app) as client:
        card = client.get("/agriculture-sector/.well-known/agent.json")
        assert card.json()["name"] == "Agriculture Agent"
        result = client.post("/agriculture-sector/a2a/tasks", json={"query": "MSP for wheat"}).json()
        assert result["status"] == "completed", result
        assert result["artifacts"][0]["content"]["findings"][0]["source"]
        direct = client.post("/api/v1/chat", json={"agent": "agriculture_sector", "message": "MSP for wheat"})
        assert direct.status_code == 200
        assert direct.json()["citations"][0]["value"] == 80
        streamed = client.post("/api/v1/chat/stream", json={"agent": "agriculture_sector", "message": "MSP for wheat"})
        assert '"type": "done"' in streamed.text
        assert '"source_category": "data_gov"' in streamed.text


def test_orchestrator_agriculture_ownership():
    from core.orchestrator.graph import decompose_node, parallel_a2a_execute_node
    from core.data.schema import SectorEnum
    state = decompose_node({"query": "wheat production"})
    assert SectorEnum.AGRICULTURE_RURAL.value in state["target_sectors"]
    result = parallel_a2a_execute_node({"query": "MSP for wheat", "target_sectors": [SectorEnum.AGRICULTURE_RURAL.value]})
    assert result["agent_analyses"][0]["agent"] == "Agriculture Agent"
    assert result["citations"][0]["source_url"] == "https://example.test/dataset"


@pytest.mark.asyncio
async def test_connector_uses_discovered_schema(monkeypatch):
    upstream = FastMCP("Fixture upstream")
    calls = []

    @upstream.tool
    async def fixture_price(commodity: str):
        calls.append(commodity)
        return {"records": ROWS["mandi_price"]}

    module = import_module("agriculture_sector.client")
    monkeypatch.setattr(module, "Client", lambda *args, **kwargs: Client(upstream))
    adapter = AgmarknetClient(SourceConfig(
        transport="https://example.test/mcp", authority="Fixture authority", live_data_verified=True,
        operations={"mandi_price": ToolBinding(tool="fixture_price", dataset="fixture",
                    source_url="https://example.test", query_fields={"commodity": "commodity"})}))
    data = await adapter.fetch("mandi_price", AgricultureQuery(commodity="wheat"))
    assert calls == ["wheat"] and data.category == "agmarknet"


@pytest.mark.asyncio
async def test_mospi_metadata_sequence():
    calls = []
    adapter = MoSPIClient()

    async def invoke(session, schemas, name, arguments):
        calls.append(name)
        return {"datasets": ["fixture"]} if name == "list_datasets" else {"metadata": ["fixture"]}

    adapter._invoke = invoke
    await adapter.before_fetch(None, {}, ToolBinding(tool="get_data", dataset="fixture", source_url="https://example.test"))
    assert calls == ["list_datasets", "get_indicators", "get_metadata"]
