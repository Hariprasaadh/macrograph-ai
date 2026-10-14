"""Offline contracts for Agriculture's two data.gov.in resources."""
import json
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from importlib import import_module

import pytest
import httpx
from fastmcp import Client
from pydantic import SecretStr

from agriculture_sector import ogd_mcp
from agriculture_sector.agent import (
    _llm_explanation, _production_tavily_rows, _production_year_window, _report, agriculture_agent_node,
    query_parameters, select_agriculture_tools,
)
from agriculture_sector.client import SourcePayload, SourceUnavailable, ToolBinding
from agriculture_sector.data_gov_resources import CROP, MANDI
from agriculture_sector.mcp_server import SOURCE_ROUTING, mcp_server, run_tool
from agriculture_sector.models import AgricultureQuery, AgricultureResult, CropProduction, SourceError
from data_gov_in_mcp.api_client import DataGovInClient
from data_gov_in_mcp.config import Config
from data_gov_in_mcp.exceptions import InvalidParameterError

MANDI_ROWS = [
    {"state": "Maharashtra", "district": "Pune", "market": "Pune", "commodity": "Wheat",
     "variety": "Wheat", "arrival_date": "01/01/2025", "min_price": 90, "max_price": 110, "modal_price": 100},
    {"state": "Maharashtra", "district": "Pune", "market": "Pune", "commodity": "Wheat",
     "variety": "Wheat", "arrival_date": "02/01/2025", "min_price": 100, "max_price": 130, "modal_price": 120},
    {"state": "Maharashtra", "district": "Pune", "market": "Baramati", "commodity": "Wheat",
     "variety": "Wheat", "arrival_date": "02/01/2025", "min_price": 90, "max_price": 120, "modal_price": 110},
]
CROP_ROWS = [
    {"state_name": "Maharashtra", "district_name": "Pune", "crop_year": 2014,
     "season": "Rabi", "crop": "Wheat", "area_": 10, "production_": 20},
    {"state_name": "Maharashtra", "district_name": "Pune", "crop_year": 2015,
     "season": "Rabi", "crop": "Wheat", "area_": 10, "production_": 25},
]


def report_crop(value: float, year: str, season: str = "Kharif", **overrides) -> CropProduction:
    fields = {
        "source": "data.gov.in", "source_category": "data_gov",
        "source_url": "https://api.data.gov.in/resource/crop-fixture",
        "dataset": "District season crop production", "mcp_tool": "get_crop_production",
        "upstream_tool": "get_dataset", "retrieved_at": datetime(2026, 10, 14, tzinfo=timezone.utc),
        "indicator": "Crop production", "value": value, "unit": "tonnes", "period": year,
        "frequency": "crop year", "state": "Odisha", "district": "Rayagada",
        "crop": "Ragi", "season": season,
        "source_filters": {"filters": {"crop": "Ragi", "state_name": "Odisha"}},
    }
    return CropProduction(**(fields | overrides))


@pytest.fixture
def ogd_fixture(monkeypatch):
    monkeypatch.setattr(ogd_mcp.settings, "DATA_GOV_IN_API_KEY", SecretStr("fixture-key"))
    monkeypatch.setattr(ogd_mcp.ogd_server, "configure_client", lambda key: None)
    state = {"calls": [], "rows": {MANDI.resource_id: MANDI_ROWS, CROP.resource_id: CROP_ROWS},
             "fail": None}

    async def fake_call(_session, name, args):
        state["calls"].append((name, args))
        if state["fail"]:
            raise state["fail"]
        resource_id = args["resource_id"]
        spec = MANDI if resource_id == MANDI.resource_id else CROP
        rows = state["rows"][resource_id]
        if name == "get_dataset_summary":
            return {"resource_id": resource_id, "total_records": len(rows),
                    "fields": sorted(spec.required_fields), "sample_record": rows[0] if rows else None}
        if name == "get_dataset_fields":
            return {"resource_id": resource_id,
                    "fields": [{"id": field, "type": "string"} for field in spec.required_fields]}
        filters = json.loads(args.get("filters", "{}"))
        selected = [row for row in rows if all(str(row.get(k)).casefold() == str(v).casefold()
                                                 for k, v in filters.items())]
        if args.get("sort"):
            selected.sort(key=lambda row: row["crop_year"], reverse=True)
        offset, limit = args.get("offset", 0), args.get("limit", 10)
        return {"resource_id": resource_id, "offset": offset, "total_records": len(selected),
                "records": selected[offset:offset + limit]}

    monkeypatch.setattr(ogd_mcp, "_call", fake_call)
    async def no_mospi(_operation, _query):
        raise SourceUnavailable("MoSPI fixture not configured", "not_configured")
    mospi_client = import_module("agriculture_sector.mcp_server").CLIENTS["mospi"]
    monkeypatch.setattr(mospi_client, "fetch", no_mospi)
    return state


@pytest.fixture(autouse=True)
def _deterministic_agriculture_llm(monkeypatch):
    """Keep answer-selection tests offline: no live LLM calls, template answers."""
    from core.orchestrator.llm_client import llm_client as llm_singleton
    monkeypatch.setattr(llm_singleton, "_get_api_key", lambda: "")
    import agriculture_sector.answer as answer_module
    monkeypatch.setattr(answer_module, "audit_candidate_llm",
                        AsyncMock(return_value={"verdict": "ABSTAIN", "reasons": ["test_no_llm"]}))


def test_resource_ids_and_validation():
    import uuid
    assert uuid.UUID(MANDI.resource_id) != uuid.UUID(CROP.resource_id)
    client = DataGovInClient(Config(api_key="fixture-key"))
    try:
        with pytest.raises(InvalidParameterError):
            client.get_resource("not-a-resource-id")
    finally:
        client.close()


def test_community_client_uses_api_filter_names_and_field_schema():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"total": 1, "records": [CROP_ROWS[0]],
                                         "field": [{"id": "crop_year", "type": "double"}]})

    client = DataGovInClient(Config(api_key="fixture-key", cache_enabled=False, max_retries=0))
    client.client.close()
    client.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        result = client.get_resource(CROP.resource_id, filters={"crop": "Wheat"},
                                     sort={"crop_year": "desc"}, limit=1)
        fields = client.get_resource_fields(CROP.resource_id)
    finally:
        client.close()
    assert result["records"][0]["crop"] == "Wheat"
    assert requests[0].url.params["filters[crop]"] == "Wheat"
    assert requests[0].url.params["sort[crop_year]"] == "desc"
    assert fields == [{"id": "crop_year", "type": "double"}]


@pytest.mark.asyncio
async def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(ogd_mcp.settings, "DATA_GOV_IN_API_KEY", SecretStr(""))
    with pytest.raises(SourceUnavailable, match="DATA_GOV_IN_API_KEY"):
        await ogd_mcp.fetch_ogd("mandi_price", AgricultureQuery(commodity="Wheat"))


@pytest.mark.asyncio
async def test_mandi_schema_pagination_provenance_and_trend(ogd_fixture, monkeypatch):
    monkeypatch.setattr(ogd_mcp, "PAGE_SIZE", 2)
    result = await run_tool("get_mandi_price_trend", AgricultureQuery(commodity="Wheat", days=2))
    assert result.status == "available" and len(result.records) == 3
    assert result.records[0].unit == "INR/quintal"
    assert result.records[0].source_url == MANDI.api_url
    assert MANDI.resource_id in result.records[0].dataset
    assert result.records[0].source == MANDI.publisher
    assert result.records[0].citation()["source_filters"]["filters"] == {"commodity": "Wheat"}
    pages = [args["offset"] for name, args in ogd_fixture["calls"]
             if name == "get_dataset" and "filters" in args]
    assert pages == [0, 2]
    assert not any(args["resource_id"] == CROP.resource_id for _, args in ogd_fixture["calls"])


@pytest.mark.asyncio
async def test_crop_year_filter_growth_area_and_derived_yield(ogd_fixture):
    query = AgricultureQuery(crop="Wheat", district="Pune", state="Maharashtra")
    trend = await run_tool("get_production_trend", query)
    assert [r.period for r in trend.records] == ["2014", "2015"]
    assert trend.derived[0]["percentage_change"] == 25
    assert trend.derived[0]["indicator"] == "year_over_year_change"
    area = await run_tool("get_crop_area", query.model_copy(update={"period": "2014"}))
    yield_result = await run_tool("get_crop_yield", query.model_copy(update={"period": "2014"}))
    assert area.records[0].value == 10 and area.records[0].unit == "hectare"
    assert yield_result.records[0].value == 2
    assert yield_result.records[0].unit == "tonnes/hectare"
    assert "Calculated" in yield_result.records[0].source_note
    assert all(args["resource_id"] == CROP.resource_id for _, args in ogd_fixture["calls"])


@pytest.mark.asyncio
async def test_missing_year(ogd_fixture):
    result = await run_tool("get_crop_production", AgricultureQuery(crop="Wheat", period="2023"))
    assert result.status == "unavailable"
    assert any("newest Wheat year is 2015" in error.message for error in result.errors)


@pytest.mark.asyncio
async def test_msp_and_weather_route_to_their_own_sources(ogd_fixture, monkeypatch):
    server = import_module("agriculture_sector.mcp_server")
    now = datetime.now(timezone.utc)

    async def msp(_query):
        return SourcePayload(data={"records": [
            {"crop": "Wheat", "period": "2026-27", "season": "Rabi", "msp": 2585,
             "unit": "INR/quintal", "frequency": "marketing season",
             "source_note": "Active Rabi marketing season as of retrieval date."},
            {"crop": "Wheat", "period": "2027-28", "season": "Rabi", "msp": 2610,
             "unit": "INR/quintal", "frequency": "marketing season"}]},
            source="PIB fixture", category="pib", retrieved_at=now,
            binding=ToolBinding(tool="official_PIB_MSP_table", dataset="PIB MSP fixture",
                                source_url="https://www.pib.gov.in/fixture", unit="INR/quintal",
                                frequency="marketing season"))

    async def weather(_operation, _query):
        return SourcePayload(data={"records": [
            {"period": "2026-10-13", "metric": "precipitation", "value": 1.4,
             "unit": "mm", "frequency": "daily", "location": "Mumbai", "city": "Mumbai",
             "display_name": "Mumbai, India", "latitude": 19.07, "longitude": 72.88}]},
            source="Open-Meteo fixture", category="weather_mcp", retrieved_at=now,
            binding=ToolBinding(tool="Open-Meteo daily API", dataset="weather fixture",
                                source_url="https://archive-api.open-meteo.com/v1/archive", frequency="daily"))

    monkeypatch.setattr(server, "fetch_rabi_msp", msp)
    monkeypatch.setattr(server, "fetch_open_meteo", weather)
    msp_result = await run_tool("get_msp", AgricultureQuery(crop="Wheat"))
    rain_result = await run_tool("get_historical_weather", AgricultureQuery(location="Mumbai"))
    assert [(r.period, r.value) for r in msp_result.records] == [("2026-27", 2585), ("2027-28", 2610)]
    assert rain_result.records[0].value == 1.4
    assert not ogd_fixture["calls"]
    fallback = AsyncMock(return_value=[])
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", fallback)
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    answer = await agriculture_agent_node({"query": "What is the current MSP for wheat?"})
    assert "active Rabi marketing season MSP" in answer["agriculture_sector_analysis"]
    assert answer["agriculture_sector_status"] == "completed"
    fallback.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_tavily_is_skipped_when_in_range_official_crop_rows_exist(ogd_fixture, monkeypatch):
    ogd_fixture["rows"][CROP.resource_id] = [dict(CROP_ROWS[0], crop_year=2025, production_=31)]
    fallback = AsyncMock(return_value=[])
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", fallback)
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({"query": "Show wheat production in Maharashtra."})
    assert any(citation["source_category"] == "data_gov" for citation in result["agriculture_sector_citations"])
    assert not any(citation["source_category"] == "tavily" for citation in result["agriculture_sector_citations"])
    fallback.assert_not_awaited()


async def test_tavily_supplements_stale_crop_rows(ogd_fixture, monkeypatch):
    fallback = AsyncMock(return_value=[{"title": "Official wheat update", "url": "https://pib.gov.in/update",
                                        "excerpt": "Wheat production in India for 2025 was estimated at 31 million tonnes."}])
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", fallback)
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({"query": "How has wheat production changed?"})
    assert result["agriculture_sector_status"] == "partial"
    assert any(c["source_category"] == "tavily" for c in result["agriculture_sector_citations"])
    assert not any(c["source_category"] == "data_gov" for c in result["agriculture_sector_citations"])
    assert "2014" not in result["agriculture_sector_analysis"]
    assert "2015" not in result["agriculture_sector_analysis"]
    serialized = json.dumps({"data": result["agriculture_sector_data"],
                             "findings": result["agriculture_sector_findings"]})
    assert "2014" not in serialized and "2015" not in serialized
    assert "31 million tonnes" in result["agriculture_sector_analysis"]
    assert result["agriculture_sector_freshness"]["tavily_search"] == "retrieved_live"
    fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_tavily_network_failure_stays_conversational(ogd_fixture, monkeypatch):
    fallback = AsyncMock(return_value=None)
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", fallback)
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({
        "query": "Show rice production in Punjab from 2023 through 2026."
    })
    assert result["agriculture_sector_freshness"]["tavily_search"] == "search_failed"
    assert "could not be completed" not in result["agriculture_sector_analysis"]
    assert "I couldn't find a verified figure" in result["agriculture_sector_analysis"]
    assert fallback.await_count in (1, 2)


@pytest.mark.asyncio
async def test_empty_tavily_search_stays_conversational(ogd_fixture, monkeypatch):
    fallback = AsyncMock(return_value=[])
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", fallback)
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({
        "query": "Show rice production in Punjab from 2023 through 2026."
    })
    assert result["agriculture_sector_freshness"]["tavily_search"] == "searched_no_qualifying_results"
    assert "Tavily was searched" not in result["agriculture_sector_analysis"]
    assert "I couldn't find a verified figure" in result["agriculture_sector_analysis"]
    assert fallback.await_count in (1, 2)


@pytest.mark.asyncio
async def test_timeout_rate_limit_empty_and_bounds(ogd_fixture, monkeypatch):
    ogd_fixture["fail"] = TimeoutError()
    timed = await run_tool("get_mandi_price", AgricultureQuery(commodity="Wheat"))
    assert timed.errors[0].code == "timeout"
    ogd_fixture["fail"] = SourceUnavailable("rate limited", "source_error")
    limited = await run_tool("get_mandi_price", AgricultureQuery(commodity="Wheat"))
    assert "rate limited" in limited.errors[0].message
    ogd_fixture["fail"] = None
    monkeypatch.setattr(ogd_mcp, "MAX_ROWS", 2)
    bounded = await run_tool("get_mandi_price", AgricultureQuery(commodity="Wheat"))
    assert "narrow" in bounded.errors[0].message
    monkeypatch.setattr(ogd_mcp, "MAX_ROWS", 5000)
    ogd_fixture["rows"][MANDI.resource_id] = []
    empty = await run_tool("get_mandi_price", AgricultureQuery(commodity="Wheat"))
    assert empty.status == "unavailable"


@pytest.mark.asyncio
async def test_duplicate_page(ogd_fixture, monkeypatch):
    monkeypatch.setattr(ogd_mcp, "PAGE_SIZE", 1)
    ogd_fixture["rows"][MANDI.resource_id] = [MANDI_ROWS[0], MANDI_ROWS[0]]
    result = await run_tool("get_mandi_price", AgricultureQuery(commodity="Wheat"))
    assert "duplicate" in result.errors[0].message


def test_query_ownership():
    assert "get_production_trend" in select_agriculture_tools("How has wheat production changed?")
    assert query_parameters("How has wheat production changed?").crop == "Wheat"
    assert "get_mandi_price" in select_agriculture_tools("Wheat mandi price")
    assert select_agriculture_tools("What is the CPI?") == set()
    rainfall = query_parameters("Show historical rainfall in Mumbai for the last 7 days.")
    assert rainfall.location == "Mumbai" and rainfall.days == 7
    assert (rainfall.end_date - rainfall.start_date).days == 6


def test_agriculture_production_queries_extract_crop_scope_and_year():
    first = query_parameters(
        "Show me the Ragi production data for Odisha, including district, season, year, production quantity, and source.")
    assert first.crop == "Ragi" and first.state == "Odisha"
    historical = query_parameters("Show the available historical production trend for Ragi in Odisha.")
    assert historical.crop == "Ragi" and historical.intent == "crop_production_history"
    rayagada = query_parameters("Show all retrieved Ragi production records for Rayagada in 2015, grouped by season.")
    assert rayagada.crop == "Ragi" and rayagada.district == "Rayagada"
    assert rayagada.period == "2015"
    assert query_parameters("rice production in 2025").period == "2025"
    assert query_parameters("Show rice production in Punjab.2025").period == "2025"
    ranged = query_parameters("Show rice production in Punjab from 2023 through 2026.")
    assert ranged.crop == "Rice" and (ranged.start_year, ranged.end_year) == (2023, 2026)
    two_years = query_parameters("rice production for last 2 yeras")
    assert two_years.crop == "Rice" and two_years.history_years == 2
    current_year = _production_year_window()[1]
    assert _production_year_window("rice production for last 2 yeras") == (current_year - 1, current_year)
    assert _production_year_window("rice production from 2023 through 2026") == (2023, 2026)


def test_production_report_displays_matching_government_rows_and_seasons():
    rows = [report_crop(120, "2025", "Kharif"), report_crop(45, "2025", "Rabi")]
    report, citations = _report(
        "Show all retrieved Ragi production records for Rayagada in 2025, grouped by season.",
        [AgricultureResult(tool="get_crop_production", status="available", records=rows)],
    )
    assert "120" in report and "45" in report and "Kharif" in report and "Rabi" in report
    assert "data.gov.in" in report and "tonnes" in report and len(citations) == 2
    assert "data unavailable" not in report.casefold()


def test_production_report_explains_one_year_without_claiming_a_trend():
    report, _ = _report(
        "Show the available historical production trend for Ragi in Odisha.",
        [AgricultureResult(tool="get_production_trend", status="available",
                           records=[report_crop(120, "2025")])],
    )
    assert "do not establish a multi-year trend" in report
    assert "120" in report and "2025" in report


def test_latest_production_report_uses_newer_official_publication():
    report, citations = _report(
        "Show the latest Ragi production in Odisha.",
        [AgricultureResult(tool="get_crop_production", status="available",
                           records=[report_crop(120, "2015")])],
        [{"title": "Ragi output estimate 2025", "url": "https://pib.gov.in/ragi",
          "excerpt": "Ragi production in Odisha for 2025 is estimated at 1.2 million tonnes."}],
    )
    assert "2015" not in report and "2025" in report
    assert "1.2 million tonnes" in report and "Published official estimate" in report
    assert "not raw structured dataset observations" in report
    assert any(citation["source_category"] == "tavily" for citation in citations)
    assert "multi-year trend" not in report


def test_production_report_accepts_lower_boundary_year():
    first_year, _ = _production_year_window()
    report, citations = _report(
        "Show Ragi production in Odisha.",
        [AgricultureResult(tool="get_crop_production", status="available",
                           records=[report_crop(120, str(first_year))])],
    )
    assert str(first_year) in report and "120" in report and citations


def test_production_report_rejects_old_government_and_tavily_figures():
    first_year, _ = _production_year_window()
    old_year = first_year - 1
    report, citations = _report(
        "Show the latest Ragi production in Odisha.",
        [AgricultureResult(tool="get_crop_production", status="available",
                           records=[report_crop(120, "2013"), report_crop(45, "2014")])],
        [{"title": f"Ragi production estimate {old_year}", "url": "https://pib.gov.in/old",
          "excerpt": f"Ragi production in Odisha for {old_year} was 1.1 million tonnes."}],
    )
    assert "120" not in report and "45" not in report
    assert "2013" not in report and "2014" not in report
    assert "1.1 million tonnes" not in report and citations == []
    assert "covers" not in report


def test_production_report_uses_actual_observation_periods_not_search_window():
    report, _ = _report(
        "Show rice production in Punjab.",
        [AgricultureResult(tool="get_crop_production", status="available",
                           records=[report_crop(35, "2022"), report_crop(42, "2024")])],
    )
    assert "are for 2022, 2024" in report
    assert "2020" not in report and "2026" not in report


def test_tavily_preserves_source_reported_cotton_bale_unit_and_indicator():
    query = "Show cotton production in Gujarat."
    result = {"title": "Cotton estimates Gujarat", "url": "https://pib.gov.in/cotton",
              "excerpt": "Total cotton production in Gujarat for 2024 was 4 million tonnes. "
                         "Organic cotton production in Gujarat for 2024 was 1.25 thousand bales."}
    rows = _production_tavily_rows(query, [result])
    assert len(rows) == 2
    assert {(row["indicator"], row["value"], row["unit"]) for row in rows} == {
        ("Crop production", "4", "million tonnes"),
        ("Organic cotton production", "1.25", "thousand bales"),
    }
    report, _ = _report(query, [AgricultureResult(tool="get_crop_production", status="unavailable")], [result])
    assert "Organic cotton production" in report and "1.25 thousand bales" in report
    assert "Crop production" in report and "4 million tonnes" in report


def test_crop_production_source_priority_is_mospi_then_data_gov():
    assert SOURCE_ROUTING["crop_production"] == ("mospi", "data_gov")


def test_tavily_figure_must_be_geographically_linked_in_the_same_sentence():
    query = "Show rice production in Punjab from 2023 through 2026."
    unrelated = [{
        "title": "Punjab agriculture update",
        "url": "https://pib.gov.in/rice-update",
        "excerpt": "Punjab farmers adopted new methods. Rice production in India in 2024 was 150.18 million tonnes.",
    }]
    contextual = _production_tavily_rows(query, unrelated)
    assert len(contextual) == 1 and not contextual[0]["scope_match"]
    assert contextual[0]["geography"] == "India-wide context; not specific to the requested area"
    state_specific = [{
        "title": "Punjab rice production",
        "url": "https://pib.gov.in/punjab-rice",
        "excerpt": "Rice production in Punjab during Kharif 2024 was 3.2 million tonnes.",
    }]
    rows = _production_tavily_rows(query, state_specific)
    assert len(rows) == 1
    assert rows[0]["year"] == "2024" and rows[0]["season"] == "Kharif"
    assert rows[0]["district"] == "Not stated"


def test_tavily_broader_rice_context_keeps_only_in_range_source_figures():
    query = "Show rice production in Punjab from 2023 through 2026."
    results = [
        {"title": "Press Release Page | Press Information Bureau", "url": "https://pib.gov.in/a",
         "excerpt": "Rice touched a record production of 150.18 Mt in 2024-25, a 42.38 percent increase compared to 2014-15 (105.48 Mt)."},
        {"title": "FAO GIEWS Country Brief on India", "url": "https://fao.org/india",
         "excerpt": "2025/26 main Kharif paddy crop was harvested by January 2026, and production is estimated at a record level of 187.5 million tonnes."},
        {"title": "Press Release Page | Press Information Bureau", "url": "https://pib.gov.in/b",
         "excerpt": "Total Rice production is estimated at 1490.74 LMT as compared to 1378.25 LMT in 2023-24, showing an increase of 112.49 LMT."},
        {"title": "Rice production forecast", "url": "https://example.com/forecast",
         "excerpt": "Rice production is forecast at 14 MMT in 2026/27."},
    ]
    rows = _production_tavily_rows(query, results)
    assert [(row["year"], row["value"], row["unit"]) for row in rows] == [
        ("2024-25", "150.18", "Mt"), ("2025/26", "187.5", "million tonnes"),
        ("2023-24", "1378.25", "LMT"),
    ]
    assert not any(row["scope_match"] for row in rows)
    assert not any(row["value"] == "14" for row in rows)
    report, citations = _report(query, [AgricultureResult(tool="get_production_trend", status="unavailable")], results)
    assert "do not establish that these figures apply specifically to Punjab" in report
    assert "2014-15" not in report and "105.48" not in report and "112.49" not in report
    assert "2024-25" in report and "2025/26" in report and len(citations) == 3


def test_tavily_does_not_mislabel_rice_sales_or_ethanol_allocation_as_production():
    query = "Show rice production in Punjab from 2023 through 2026."
    results = [{
        "title": "Government rice allocation",
        "url": "https://pib.gov.in/rice-allocation",
        "excerpt": "During 2025 as on 18.11.2025, 33.06 LMT of rice has been sold to ethanol distilleries for production of ethanol. 10 LMT of broken rice were allocated for sale in 2025-26.",
    }]
    assert _production_tavily_rows(query, results) == []


def test_published_figures_with_same_year_are_explained_as_different_claims():
    report, _ = _report(
        "Rice production in 2025.", [AgricultureResult(tool="get_crop_production", status="unavailable")],
        [{"title": "Press Release | Estimate A", "url": "https://pib.gov.in/a",
          "excerpt": "Rice production for 2025 is estimated at 376.563 million tonnes."},
         {"title": "Press Release | Estimate B", "url": "https://pib.gov.in/b",
          "excerpt": "Rice production for 2025 is estimated at 124.504 million tonnes."}],
    )
    assert "376.563 million tonnes" in report and "124.504 million tonnes" in report
    assert "report different production figures" in report
    assert "excerpts do not establish" in report
    assert "Press Release \\| Estimate" in report


@pytest.mark.asyncio
async def test_llm_explanation_is_prompted_to_explain_observed_patterns(monkeypatch):
    from core.orchestrator.llm_client import llm_client

    prompts = []

    async def complete(_message, system_prompt):
        prompts.append(system_prompt)
        return "Sangrur reports more rice production than Pathankot in the listed observations."

    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "fixture-key")
    monkeypatch.setattr(llm_client, "complete", complete)
    explanation = await _llm_explanation(
        "Show rice production by district.",
        {"structured_observations": [{"district": "Sangrur"}, {"district": "Pathankot"}]},
    )
    assert explanation and "Sangrur" in explanation
    assert "identify which reported observations are relatively higher or lower" in prompts[0]
    assert "Do not claim a lack of verification" in prompts[0]


@pytest.mark.asyncio
async def test_tavily_only_llm_formats_source_evidence_without_changing_figures(monkeypatch):
    from core.orchestrator.llm_client import llm_client

    prompts = []
    async def complete(_message, system_prompt):
        prompts.append(system_prompt)
        return "The publication describes a broader production estimate; its scope does not support a district comparison."

    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "fixture-key")
    monkeypatch.setattr(llm_client, "complete", complete)
    answer = await _llm_explanation(
        "Show rice production in Punjab.",
        {"publication_evidence": [{"indicator": "Crop production", "unit": "tonnes",
                                   "scope_match": False}],
         "structured_observations": [], "comparable_trend_supported": False},
    )
    assert answer and "broader production estimate" in answer
    assert "Format a concise, polished explanation" in prompts[0]
    assert "Do not describe production figures as yield or area" in prompts[0]


@pytest.mark.asyncio
async def test_llm_cannot_invent_yield_or_a_trend_from_production_only(monkeypatch):
    from core.orchestrator.llm_client import llm_client

    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "fixture-key")
    async def unsupported(_message, _system_prompt):
        return "Rice yield increased across the period."
    monkeypatch.setattr(llm_client, "complete", unsupported)
    answer = await _llm_explanation(
        "Show rice production.",
        {"structured_observations": [{"indicator": "Crop production", "period": "2025"}],
         "comparable_trend_supported": False},
    )
    assert answer is None


def test_requested_year_uses_matching_tavily_publication_only():
    report, citations = _report(
        "Show Ragi production in Odisha for 2025.",
        [AgricultureResult(tool="get_crop_production", status="unavailable")],
        [{"title": "Ragi production estimates 2022", "url": "https://pib.gov.in/ragi-2022",
          "excerpt": "Ragi production in Odisha for 2022 was 1.1 million tonnes."},
         {"title": "Ragi production estimates 2025", "url": "https://pib.gov.in/ragi-2025",
          "excerpt": "Ragi production in Odisha for 2025 was 1.2 million tonnes."}],
    )
    assert "1.2 million tonnes" in report
    assert "1.1 million tonnes" not in report
    assert len(citations) == 1 and citations[0]["observation_period"] == "2025"


def test_production_report_labels_government_and_publication_sources_separately():
    report, _ = _report(
        "Show Ragi production in Odisha.",
        [AgricultureResult(tool="get_crop_production", status="available",
                           records=[report_crop(120, "2025")])],
        [{"title": "Ragi production 2025", "url": "https://pib.gov.in/ragi",
          "excerpt": "Ragi production for Odisha in 2025 was estimated at 125 tonnes."}],
    )
    assert "Structured government observations" in report
    assert "Published source figures" in report
    assert "data.gov.in" in report and "pib.gov.in" in report
    assert "shown separately" in report


def test_empty_production_response_is_user_facing_and_error_free():
    report, citations = _report(
        "Show Ragi production in Odisha for 2025.",
        [AgricultureResult(tool="get_crop_production", status="unavailable",
                           errors=[SourceError(source="data.gov", code="source_error",
                                               message="MCP server failed after retries")])],
    )
    assert "no figure that can be attributed to" in report
    assert "MCP server failed" not in report and "data unavailable" not in report.casefold()
    assert citations == []


def test_valid_observations_are_not_overridden_by_tool_warning():
    report, citations = _report(
        "Show Ragi production in Odisha.",
        [AgricultureResult(tool="get_crop_production", status="partial",
                           records=[report_crop(120, "2025")],
                           errors=[SourceError(source="mcp", code="source_error",
                                               message="Tool returned an error")])],
    )
    assert "120" in report and "2025" in report and citations
    assert "Tool returned an error" not in report


@pytest.mark.asyncio
async def test_public_tools_registered():
    async with Client(mcp_server) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert {"get_mandi_price", "get_crop_production", "get_production_trend"} <= names


def _tn_rice(value: float, year: str, **overrides):
    return report_crop(value, year, **{
        "crop": "Rice", "state": "Tamil Nadu", "district": None,
        "season": "Kharif", "unit": "tonnes", "indicator": "Crop production",
    } | overrides)


def test_tamil_nadu_rice_prioritizes_state_records_over_national():
    tn = _tn_rice(500, "2024")
    national = _tn_rice(1500, "2024", state=None, district=None)
    report, citations = _report(
        "Show rice production in Tamil Nadu.",
        [AgricultureResult(tool="get_crop_production", status="available",
                            records=[national, tn])],
    )
    assert "Tamil Nadu" in report
    tn_pos = report.find("Tamil Nadu")
    broader_pos = report.find("Broader context")
    assert tn_pos >= 0 and broader_pos > tn_pos
    assert len(citations) == 2
    assert "do not establish that these figures apply specifically to" in report or "Broader context" in report


def test_comparable_state_years_are_displayed_and_compared():
    first = _tn_rice(400, "2024")
    second = _tn_rice(500, "2025")
    report, _ = _report(
        "Show rice production in Tamil Nadu.",
        [AgricultureResult(tool="get_crop_production", status="available",
                            records=[first, second])],
    )
    assert "2024" in report and "2025" in report
    assert "calculated from the cited values" in report
    assert "25.00%" in report


def test_same_year_estimate_revisions_stay_distinguishable():
    query = "Show rice production in Tamil Nadu."
    web = [
        {"title": "Rice estimates TN", "url": "https://pib.gov.in/tn-a",
         "excerpt": "Rice production in Tamil Nadu for 2024-25 is estimated at 50 lakh tonnes as per the third advance estimate.",
         "published_date": "2025-05-01"},
        {"title": "Rice estimates TN final", "url": "https://pib.gov.in/tn-b",
         "excerpt": "Rice production in Tamil Nadu for 2024-25 is estimated at 55 lakh tonnes as per the final estimate.",
         "published_date": "2025-09-01"},
    ]
    report, citations = _report(
        query, [AgricultureResult(tool="get_crop_production", status="unavailable")], web)
    assert "50" in report and "55" in report
    assert "different production figures" in report
    assert "should not be combined" in report
    assert any("Advance Estimate" in (c.get("source_note") or "") for c in citations)
    assert any("Final Estimate" in (c.get("source_note") or "") for c in citations)


def test_missing_state_results_do_not_invent_figures():
    other = _tn_rice(900, "2024", state="Punjab")
    report, _ = _report(
        "Show rice production in Tamil Nadu.",
        [AgricultureResult(tool="get_crop_production", status="available",
                            records=[other])],
    )
    assert "do not establish that these figures apply specifically to Tamil Nadu" in report
    assert "Tamil Nadu" in report


# ---------------------------------------------------------------------------
# Primary-answer selection, final-answer rendering, and response isolation.
# ---------------------------------------------------------------------------

def _tn_published(value: str, year_text: str, **overrides):
    row = {"title": "Tamil Nadu rice report", "url": "https://pib.gov.in/tn-rice",
           "year": year_text, "year_start": year_text[:4], "indicator": "Crop production",
           "value": value, "unit": "lakh tonnes", "district": "Not stated",
           "season": "Kharif", "geography": "Tamil Nadu", "scope_match": True,
           "label": "Published official estimate", "excerpt": ""}
    return row | overrides


def test_primary_selection_prefers_exact_state_and_period():
    from agriculture_sector.answer import select_primary
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    structured = [
        {"value": 500.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Rice",
         "geography": "Tamil Nadu", "period": "2024", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/rice", "scope_match": True},
        {"value": 1500.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Rice",
         "geography": "India-wide context", "period": "2025", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/india", "scope_match": False},
    ]
    published = [_tn_published("80", "2025")]
    import asyncio
    primary, _ = asyncio.run(select_primary("Rice production in Tamil Nadu in 2025.", dims, structured, published))
    assert primary is not None
    assert primary.period == "2025" and "Tamil Nadu" in primary.geography
    assert primary.value_text == "80" and primary.source_url == "https://pib.gov.in/tn-rice"


def test_title_without_number_is_not_a_candidate():
    rows = _production_tavily_rows(
        "Show rice production in Tamil Nadu.",
        [{"title": "Tamil Nadu rice policy announcement", "url": "https://pib.gov.in/policy",
          "excerpt": "The government announced a new rice procurement policy for Tamil Nadu farmers."}])
    assert rows == []


def test_wrong_unit_and_geography_are_rejected():
    from agriculture_sector.answer import deterministic_audit
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    candidate = {"value_num": 80.0, "value_text": "80", "unit": "", "indicator": "Crop production",
                 "geography": "India-wide context", "period": "2025", "source_url": "https://example.test"}
    failures = deterministic_audit(dims, candidate)
    assert "unit_missing" in failures and "geography_mismatch" in failures


def test_missing_year_selects_latest_with_true_period():
    from agriculture_sector.answer import select_primary, template_answer
    import asyncio
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    structured = [
        {"value": 500.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Rice",
         "geography": "Tamil Nadu", "period": "2024", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/rice", "scope_match": True},
    ]
    primary, _ = asyncio.run(select_primary("Rice production in Tamil Nadu in 2025.", dims, structured, []))
    assert primary is not None and primary.period == "2024" and primary.is_fallback
    lead = template_answer(dims, primary)
    assert "reported for **2024**" in lead and "500 tonnes" in lead


@pytest.mark.asyncio
async def test_llm_rejection_selects_next_candidate(monkeypatch):
    import agriculture_sector.answer as answer_module
    calls = {"n": 0}

    async def fake_audit(query, dims, candidate, conflicts):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"verdict": "FAIL", "reasons": ["unit_mismatch"], "needs_retry": True}
        return {"verdict": "PASS", "reasons": [], "needs_retry": False}

    monkeypatch.setattr(answer_module, "audit_candidate_llm", fake_audit)
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": ""}
    structured = [
        {"value": 500.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Rice",
         "geography": "Tamil Nadu", "period": "2025", "season": "Kharif",
         "source_name": "mospi", "source_url": "https://mospi.gov.in/a", "scope_match": True},
        {"value": 510.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Rice",
         "geography": "Tamil Nadu", "period": "2024", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/b", "scope_match": True},
    ]
    primary, trail = await answer_module.select_primary("Rice production in Tamil Nadu.", dims, structured, [])
    assert primary is not None and primary.period == "2024"
    assert trail[0]["llm"]["verdict"] == "FAIL" and calls["n"] == 2


def test_final_answer_has_one_value_and_no_table_or_verdicts():
    from agriculture_sector.answer import render_final_answer, scan_forbidden
    import asyncio
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    from agriculture_sector.answer import PrimaryObservation
    primary = PrimaryObservation(
        value_text="80", unit="lakh tonnes", crop="Rice", indicator="Crop production",
        geography="Tamil Nadu", period="2025", source_name="Press Information Bureau",
        source_url="https://pib.gov.in/tn-rice")
    lead = asyncio.run(render_final_answer("Rice production in Tamil Nadu in 2025.", dims, primary))
    assert "80" in lead and "lakh tonnes" in lead and "2025" in lead
    assert "https://pib.gov.in/tn-rice" in lead
    assert "|" not in lead and scan_forbidden(lead) == []


@pytest.mark.asyncio
async def test_node_answer_is_clean_and_cited(ogd_fixture, monkeypatch):
    from agriculture_sector.answer import scan_forbidden
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", AsyncMock(return_value=[{
        "title": "Tamil Nadu rice production", "url": "https://pib.gov.in/tn-rice",
        "excerpt": "Rice production in Tamil Nadu for 2025 was 80 lakh tonnes.",
        "published_date": "2026-01-05"}]))
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    monkeypatch.setattr("agriculture_sector.answer.audit_candidate_llm",
                        AsyncMock(return_value={"verdict": "PASS", "reasons": [], "needs_retry": False}))
    result = await agriculture_agent_node({"query": "Rice production in Tamil Nadu in 2025."})
    analysis = result["agriculture_sector_analysis"]
    assert scan_forbidden(analysis) == []
    primary = result["agriculture_sector_primary"]
    assert primary is not None and primary["value"] == "80" and primary["period"] == "2025"
    assert "**Metric:** Rice production — **80 lakh tonnes**" in analysis
    assert "**Geography:** Tamil Nadu" in analysis
    assert "**Reporting period:** 2025" in analysis
    assert "https://pib.gov.in/tn-rice" in analysis
    assert "|" not in analysis
    urls = [c.get("source_url") or c.get("retrieval_url") for c in result["agriculture_sector_citations"]]
    assert primary["source_url"] in urls
    public = json.dumps({"answer": result["agriculture_sector_answer"], "primary": primary})
    assert "verdict" not in public and "PASS" not in public


@pytest.mark.asyncio
async def test_node_empty_result_invents_no_number(ogd_fixture, monkeypatch):
    from agriculture_sector.answer import scan_forbidden
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback", AsyncMock(return_value=[]))
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({"query": "Rice production in Tamil Nadu in 2025."})
    lead = result["agriculture_sector_answer"]
    assert "couldn't find a verified Rice production figure for Tamil Nadu for 2025" in lead
    assert "tonnes" not in lead and "lakh" not in lead
    assert scan_forbidden(result["agriculture_sector_analysis"]) == []


def test_district_query_keeps_district_scope():
    from agriculture_sector.answer import select_primary
    import asyncio
    dims = {"crop": "Ragi", "indicator": "production", "geography": "Rayagada", "period": "2015"}
    structured = [
        {"value": 120.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Ragi",
         "geography": "Odisha / Rayagada", "period": "2015", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/a", "scope_match": True},
        {"value": 900.0, "unit": "tonnes", "indicator": "Crop production", "crop": "Ragi",
         "geography": "Odisha", "period": "2015", "season": "Kharif",
         "source_name": "data.gov.in", "source_url": "https://data.gov.in/b", "scope_match": True},
    ]
    primary, _ = asyncio.run(select_primary("Ragi production in Rayagada in 2015.", dims, structured, []))
    assert primary is not None and "Rayagada" in primary.geography


def test_duplicate_publications_yield_one_primary():
    from agriculture_sector.answer import build_candidates
    rows = [_tn_published("80", "2025"),
            _tn_published("80", "2025", url="https://example.test/copy", title="Copy of TN rice report")]
    candidates = build_candidates(
        {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"},
        [], rows)
    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_mospi_to_data_gov_fallback_order(ogd_fixture, monkeypatch):
    from agriculture_sector.mcp_server import CLIENTS, run_tool
    from agriculture_sector.client import SourceUnavailable
    from agriculture_sector.models import AgricultureQuery
    monkeypatch.setattr(CLIENTS["mospi"], "fetch",
                        AsyncMock(side_effect=SourceUnavailable("Fixture MOSPI outage", "source_error")))
    result = await run_tool("get_crop_production", AgricultureQuery(crop="Wheat"))
    assert result.records and result.records[0].source_category == "data_gov"
    assert result.errors and result.errors[0].source == "mospi"


def test_capital_market_implementation_untouched():
    from pathlib import Path
    cap = Path(__file__).parents[1] / "capital_market_sector" / "agent.py"
    assert "agriculture_sector_answer" not in cap.read_text()
    assert "select_primary" not in cap.read_text()


def test_metric_families_are_never_substituted():
    from agriculture_sector.answer import deterministic_audit, metric_family_of, metric_mismatch
    assert metric_family_of("Crop production") == "production"
    assert metric_family_of("Crop yield") == "yield"
    assert metric_family_of("Crop area") == "area"
    assert metric_family_of("Mandi price") == "price"
    assert metric_mismatch("production", "Crop yield")
    assert metric_mismatch("yield", "Crop production")
    assert metric_mismatch("production", "Crop area")
    assert metric_mismatch("production", "Mandi price")
    assert not metric_mismatch("production", "Crop production")
    assert not metric_mismatch("price", "MSP")
    candidate = {"value_num": 2.5, "value_text": "2.5", "unit": "tonnes/hectare",
                 "indicator": "Crop yield", "geography": "Tamil Nadu", "period": "2025",
                 "source_url": "https://data.gov.in/y"}
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    assert "metric_mismatch" in deterministic_audit(dims, candidate)


def test_answer_card_has_only_requested_fields():
    from agriculture_sector.answer import PrimaryObservation, render_answer_card, scan_forbidden
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": "2025"}
    primary = PrimaryObservation(
        value_text="80", unit="lakh tonnes", crop="Rice", indicator="Crop production",
        geography="Tamil Nadu", period="2025", source_name="Press Information Bureau",
        source_url="https://pib.gov.in/tn-rice", estimate_status="Third Advance Estimate")
    card = render_answer_card(dims, primary)
    assert "**Metric:** Rice production — **80 lakh tonnes**" in card
    assert "**Crop/commodity:** Rice" in card
    assert "**Geography:** Tamil Nadu" in card
    assert "**Reporting period:** 2025" in card
    assert "**Source:** [Press Information Bureau](https://pib.gov.in/tn-rice)" in card
    assert "Third Advance Estimate" in card
    assert "|" not in card and scan_forbidden(card) == []
    national = PrimaryObservation(
        value_text="357", unit="MMT", crop="Rice", indicator="Crop production",
        geography="India-wide context; not specific to the requested area", period="2024-25",
        source_name="PIB", source_url="https://pib.gov.in/i",
        is_fallback=True, fallback_note="covers India-wide context")
    national_card = render_answer_card(dims, national)
    assert "**Geography:** India (national-level)" in national_card
    assert "in Tamil Nadu was" not in national_card
    assert "covers India-wide context" in national_card
    missing = render_answer_card(dims, None)
    assert "couldn't find a verified Rice production figure" in missing
    assert scan_forbidden(missing) == []


# ---------------------------------------------------------------------------
# Same-year excerpt hits: reason with the LLM and answer from one best pick.
# ---------------------------------------------------------------------------

_EXCERPT_WEB = [
    {"title": "Tamil Nadu rice assessment", "url": "https://pib.gov.in/tn-rice",
     "excerpt": "Rice production in Tamil Nadu for 2024-25 shows an increase of 75 lakh tonnes over 2023-24.",
     "published_date": "2025-06-01"},
    {"title": "National rice overview", "url": "https://pib.gov.in/india-rice",
     "excerpt": "Rice production in India for 2024-25 shows an increase of 357 MMT over 2023-24.",
     "published_date": "2025-06-02"},
    {"title": "Advance estimates note", "url": "https://example.test/advance-note",
     "excerpt": "The Government has released the 3rd advance estimates of rice production for 2025-26, providing a comprehensive assessment.",
     "published_date": "2025-07-01"},
]


def test_excerpt_scoring_prefers_state_numeric_official():
    from agriculture_sector.answer import score_excerpt
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": ""}
    from agriculture_sector.agent import _relevant_tavily_excerpts
    related = _relevant_tavily_excerpts("Rice production in Tamil Nadu.", _EXCERPT_WEB)
    assert len(related) == 3
    scores = {item["url"]: score_excerpt(dims, item)[0] for item in related}
    assert scores["https://pib.gov.in/tn-rice"] > scores["https://pib.gov.in/india-rice"]
    assert scores["https://pib.gov.in/india-rice"] > scores["https://example.test/advance-note"]


def test_excerpt_without_number_never_becomes_candidate():
    from agriculture_sector.answer import excerpt_to_published_row, extract_excerpt_figure
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": ""}
    assert extract_excerpt_figure("A comprehensive assessment with no figures.") is None
    blurb = {"relevant_excerpt": "The Government has released estimates of rice, providing an assessment.",
             "relevant_year": "2025", "title": "Note", "url": "https://example.test/note"}
    assert excerpt_to_published_row(dims, blurb) is None


@pytest.mark.asyncio
async def test_llm_pick_choice_is_used(monkeypatch):
    from core.orchestrator.llm_client import llm_client as llm_singleton
    from agriculture_sector.answer import pick_best_excerpt
    monkeypatch.setattr(llm_singleton, "_get_api_key", lambda: "fixture-key")
    monkeypatch.setattr(llm_singleton, "complete",
                        AsyncMock(return_value='{"pick": 1, "reason": "geo_match"}'))
    dims = {"crop": "Rice", "indicator": "production", "geography": "Tamil Nadu", "period": ""}
    from agriculture_sector.agent import _relevant_tavily_excerpts
    related = _relevant_tavily_excerpts("Rice production in Tamil Nadu.", _EXCERPT_WEB)
    pick, trail = await pick_best_excerpt("Rice production in Tamil Nadu.", dims, related)
    assert pick is not None and pick["url"] == "https://pib.gov.in/india-rice"
    assert trail[-1]["llm_pick"] == 1


@pytest.mark.asyncio
async def test_node_answers_from_single_best_excerpt(ogd_fixture, monkeypatch):
    from agriculture_sector.answer import scan_forbidden
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback",
                        AsyncMock(return_value=_EXCERPT_WEB))
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    result = await agriculture_agent_node({"query": "Rice production in Tamil Nadu."})
    analysis = result["agriculture_sector_analysis"]
    lead = result["agriculture_sector_answer"]
    assert "**Metric:** Rice production — **75 lakh tonnes**" in lead
    assert "**Reporting period:** 2024-25" in lead
    assert analysis == lead
    assert "Related Tavily publication details" not in analysis
    assert "357" not in analysis
    excerpt_citations = [c for c in result["agriculture_sector_citations"]
                         if c.get("source_category") == "tavily"]
    assert len(excerpt_citations) == 1
    assert excerpt_citations[0]["source_url"] == "https://pib.gov.in/tn-rice"
    assert scan_forbidden(analysis) == []


@pytest.mark.asyncio
async def test_node_llm_pick_override_changes_answer(ogd_fixture, monkeypatch):
    from agriculture_sector.agent import _relevant_tavily_excerpts
    related = _relevant_tavily_excerpts("Rice production in Tamil Nadu.", _EXCERPT_WEB)
    national = next(item for item in related if item["url"] == "https://pib.gov.in/india-rice")
    monkeypatch.setattr("agriculture_sector.agent._tavily_fallback",
                        AsyncMock(return_value=_EXCERPT_WEB))
    monkeypatch.setattr("agriculture_sector.agent._llm_explanation", AsyncMock(return_value=None))
    monkeypatch.setattr("agriculture_sector.agent.pick_best_excerpt",
                        AsyncMock(return_value=(national, [{"llm_pick": "test"}])))
    result = await agriculture_agent_node({"query": "Rice production in Tamil Nadu."})
    lead = result["agriculture_sector_answer"]
    assert "**357 MMT**" in lead and "India (national-level)" in lead
    assert "covers India-wide context" in lead
    assert "75 lakh tonnes" not in result["agriculture_sector_analysis"]
