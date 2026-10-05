"""Comprehensive pytest test suite for the Services Sector.

Test coverage:
  1. Pydantic models — mandatory Citation, validation, UnavailableResponse.
  2. DuckDB schema — initialisation, upsert, fetch, audit log.
  3. Data client — live fetch parsing, cache fallback, ServicesDataUnavailableError.
  4. MCP tools — happy path, invalid inputs, cache-only, unavailable.
  5. FastAPI sub-app — HTTP status codes, response structure, metadata endpoint.

All external HTTP calls are mocked. No live network calls in tests.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services_sector.models import (
    Citation,
    DataFreshness,
    ISPGrowthResponse,
    ISPRecord,
    ServicesGVARecord,
    ServicesPMIRecord,
    ServiceSubSector,
    TransportFreightRecord,
    UnavailableResponse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="National Statistical Office (NSO), MoSPI",
        document_title="Index of Service Production (ISP) Monthly Release",
        table_reference="mospi.isp_monthly",
        retrieval_url="https://mcp.mospi.gov.in",
        observation_period="2026-07",
        freshness=DataFreshness.LIVE,
    )


@pytest.fixture
def sample_isp_record(valid_citation) -> ISPRecord:
    return ISPRecord(
        period="2026-03",
        sub_sector=ServiceSubSector.IT_COMPUTER,
        isp_index=146.5,
        isp_yoy_pct=None,
        isp_mom_pct=None,
        citation=valid_citation,
    )


@pytest.fixture
def sample_gva_record(valid_citation) -> ServicesGVARecord:
    return ServicesGVARecord(
        period="2023-24",
        nas_statement="8.12",
        segment="Financial Services",
        gva_current_cr=1598185.0,
        gva_constant_cr=972874.0,
        gva_yoy_pct=None,
        citation=valid_citation,
    )


@pytest.fixture
def sample_pmi_record() -> ServicesPMIRecord:
    return ServicesPMIRecord(
        period="2026-07",
        headline_pmi=59.2,
        new_orders_idx=60.1,
        input_costs_idx=54.3,
        employment_idx=52.8,
        citation=Citation(
            source_authority="S&P Global / HSBC",
            document_title="HSBC India Services PMI Press Release",
            table_reference="sp_global.services_pmi_india",
            retrieval_url="https://www.pmi.spglobal.com",
            observation_period="2026-07",
        ),
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Redirect DuckDB to a temporary directory for test isolation."""
    db_path = tmp_path / "test_services.duckdb"
    monkeypatch.setattr("services_sector.database._DB_PATH", db_path)
    from services_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


# ---------------------------------------------------------------------------
# 1. Pydantic Model Tests
# ---------------------------------------------------------------------------

class TestCitation:
    def test_citation_requires_all_fields(self):
        with pytest.raises(Exception):
            Citation(source_authority="MoSPI")

    def test_citation_default_freshness_is_live(self, valid_citation):
        assert valid_citation.freshness == DataFreshness.LIVE

    def test_citation_fetched_at_is_set(self, valid_citation):
        assert isinstance(valid_citation.fetched_at, datetime)


class TestISPRecord:
    def test_valid_record_serialises(self, sample_isp_record):
        d = sample_isp_record.model_dump(mode="json")
        assert d["period"] == "2026-03"
        assert d["isp_index"] == 146.5
        assert d["sub_sector"] == "IT_COMPUTER"

    def test_unavailable_response_rejects_records(self, sample_isp_record):
        with pytest.raises(Exception):
            ISPGrowthResponse(status=DataFreshness.UNAVAILABLE, records=[sample_isp_record])

    def test_sub_sector_mapping(self):
        from services_sector.parsers import map_sub_sector
        assert map_sub_sector("IT & Computer Related Services") == ServiceSubSector.IT_COMPUTER
        assert map_sub_sector("Telecommunications") == ServiceSubSector.TELECOMMUNICATIONS
        assert map_sub_sector("General") == ServiceSubSector.GENERAL


class TestUnavailableResponse:
    def test_unavailable_response_structure(self):
        resp = UnavailableResponse(tool="get_isp_growth", reason="Both live fetch and cache are empty.")
        assert resp.status == DataFreshness.UNAVAILABLE
        assert resp.last_successful_fetch is None


# ---------------------------------------------------------------------------
# 2. DuckDB Schema Tests
# ---------------------------------------------------------------------------

class TestDatabaseSchema:
    def test_schema_initialises_without_error(self, temp_db):
        from services_sector import database
        database.initialise_schema()  # idempotent — must not raise

    def test_upsert_and_query_isp_rows(self, temp_db, sample_isp_record):
        from services_sector import database
        row = {
            "period": sample_isp_record.period,
            "sub_sector": sample_isp_record.sub_sector.value,
            "isp_index": sample_isp_record.isp_index,
            "isp_yoy_pct": sample_isp_record.isp_yoy_pct,
            "isp_mom_pct": sample_isp_record.isp_mom_pct,
            "citation": sample_isp_record.citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("isp_growth", [row])
        assert written == 1

        rows = database.query_latest_rows("isp_growth", 10)
        assert len(rows) == 1
        assert rows[0]["period"] == "2026-03"
        assert isinstance(rows[0]["citation"], dict)

    def test_upsert_is_idempotent(self, temp_db, sample_isp_record):
        from services_sector import database
        row = {
            "period": "2026-03",
            "sub_sector": "TELECOMMUNICATIONS",
            "isp_index": 112.4,
            "isp_yoy_pct": 7.2,
            "isp_mom_pct": 0.6,
            "citation": sample_isp_record.citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        database.upsert_rows("isp_growth", [row])
        database.upsert_rows("isp_growth", [row])
        rows = database.query_latest_rows("isp_growth", 10)
        assert len(rows) == 1

    def test_fetch_log_writes_entry(self, temp_db):
        from services_sector import database
        database.log_fetch("get_isp_growth", "live", rows_written=5)
        with database.get_connection() as con:
            result = con.execute("SELECT * FROM fetch_log").fetchall()
        assert len(result) == 1
        assert result[0][1] == "get_isp_growth"

    def test_unauthorized_table_raises_value_error(self, temp_db):
        from services_sector import database
        with pytest.raises(ValueError, match="Invalid or unauthorized database table"):
            database.upsert_rows("malicious_table_drop", [{"a": 1}])
        with pytest.raises(ValueError, match="Invalid or unauthorized database table"):
            database.query_latest_rows("malicious_table_drop", 10)


# ---------------------------------------------------------------------------
# 3. Data Client Tests (mocked MoSPI MCP)
# ---------------------------------------------------------------------------

_MOCK_ISP_PAYLOAD = {
    # Real MCP row format: FY year + month name + sub-sector label + index.
    "data": [
        {"base_year": "2024-25", "year": "2025-26", "frequency": "Monthly", "month": "March",
         "broad_sub_sector": "IT & computer related services", "index": "146.5", "growth_rate": None},
        {"base_year": "2024-25", "year": "2025-26", "frequency": "Monthly", "month": "February",
         "broad_sub_sector": "IT & computer related services", "index": "109.2", "growth_rate": None},
        {"base_year": "2024-25", "year": "2025-26", "frequency": "Monthly", "month": "March",
         "broad_sub_sector": "Telecommunication", "index": "121.3", "growth_rate": None},
    ]
}

_MOCK_NAS_PAYLOAD = {
    # Real MCP row format for indicator_code 1 (GVA), annual.
    "data": [
        {"base_year": "2011-12", "series": "Current", "year": "2023-24",
         "indicator": "Gross Value Added", "frequency": "Annual",
         "revision": "First Revised Estimates", "industry": "Financial Services",
         "subindustry": None, "current_price": "1598185", "constant_price": "972874",
         "unit": "₹ Crore"},
        {"base_year": "2011-12", "series": "Current", "year": "2022-23",
         "indicator": "Gross Value Added", "frequency": "Annual",
         "revision": "First Revised Estimates", "industry": "Financial Services",
         "subindustry": None, "current_price": "1442484", "constant_price": "894602",
         "unit": "₹ Crore"},
    ]
}

_MOCK_NSS80_PAYLOAD = {
    # Real MCP row format for NSS80 indicator 17, All-India.
    "data": [
        {"indicator": "Percentage of households possessing landline, mobile phone and optical fiber connectivity",
         "state": "All-India", "mobile_household_assets": "Smartphone only",
         "sector": "Rural", "value": "53"},
        {"indicator": "Percentage of households possessing landline, mobile phone and optical fiber connectivity",
         "state": "All-India", "mobile_household_assets": "Smartphone only",
         "sector": "Urban", "value": "78.5"},
    ]
}


class TestDataClient:
    @pytest.mark.asyncio
    async def test_fetch_isp_live_success(self, temp_db):
        from services_sector import client
        from services_sector import mospi_client as mcp

        async def _mock_get_data(dataset, filters):
            return dict(_MOCK_ISP_PAYLOAD)

        with patch.object(mcp, "get_data", _mock_get_data):
            records = await client.fetch_isp_growth(lookback_months=6)

        assert len(records) >= 1
        assert records[0].citation.freshness == DataFreshness.LIVE

    @pytest.mark.asyncio
    async def test_fetch_isp_falls_back_to_cache(self, temp_db, sample_isp_record):
        from services_sector import client, database
        from services_sector import mospi_client as mcp

        database.upsert_rows("isp_growth", [{
            "period": "2026-03",
            "sub_sector": "IT_COMPUTER",
            "isp_index": sample_isp_record.isp_index,
            "isp_yoy_pct": sample_isp_record.isp_yoy_pct,
            "isp_mom_pct": sample_isp_record.isp_mom_pct,
            "citation": json.dumps({
                "source_agent": "services_sector",
                "source_authority": "National Statistical Office (NSO), MoSPI",
                "document_title": "Test",
                "table_reference": "mospi.isp_monthly",
                "retrieval_url": "https://mcp.mospi.gov.in",
                "observation_period": "2026-03",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

        async def _failing_get_data(dataset, filters):
            raise RuntimeError("Connection refused")

        with patch.object(mcp, "get_data", _failing_get_data):
            records = await client.fetch_isp_growth(
                sub_sector=ServiceSubSector.IT_COMPUTER, lookback_months=6
            )

        assert records[0].citation.freshness == DataFreshness.CACHED

    @pytest.mark.asyncio
    async def test_fetch_isp_raises_when_cache_empty(self, temp_db):
        from services_sector import mospi_client as mcp
        from services_sector.cache_loaders import ServicesDataUnavailableError
        from services_sector.client import fetch_isp_growth

        async def _failing_get_data(dataset, filters):
            raise RuntimeError("Connection refused")

        with patch.object(mcp, "get_data", _failing_get_data):
            with pytest.raises(ServicesDataUnavailableError):
                await fetch_isp_growth(lookback_months=6)

    @pytest.mark.asyncio
    async def test_fetch_gva_live_success(self, temp_db):
        """NAS GVA live fetch uses verified indicator/industry filters."""
        from services_sector import client
        from services_sector import mospi_client as mcp

        seen_filters: list[dict] = []

        async def _mock_get_data(dataset, filters):
            seen_filters.append({"dataset": dataset, **filters})
            return dict(_MOCK_NAS_PAYLOAD)

        with patch.object(mcp, "get_data", _mock_get_data):
            records = await client.fetch_services_gva()

        assert len(records) >= 1
        assert records[0].citation.freshness == DataFreshness.LIVE
        assert records[0].segment == "Financial Services"
        assert records[0].nas_statement == "8.12"
        # YoY derived from constant-price levels across years
        fin = [r for r in records if r.period == "2023-24" and r.segment == "Financial Services"]
        assert fin and fin[0].gva_yoy_pct == pytest.approx(
            (972874 - 894602) / 894602 * 100, abs=0.01
        )
        # Verified filter contract: indicator 1, base 2011-12, annual
        assert seen_filters and all(
            f["dataset"] == "NAS" and f["indicator_code"] == 1
            and f["base_year"] == "2011-12" and f["frequency_code"] == 1
            for f in seen_filters
        )

    @pytest.mark.asyncio
    async def test_fetch_freight_live_success(self, temp_db):
        """NSS80 telecom live fetch uses verified indicator/state filters."""
        from services_sector import client
        from services_sector import mospi_client as mcp

        async def _mock_get_data(dataset, filters):
            assert dataset == "NSS80"
            assert filters["state_code"] == 37  # All-India
            return dict(_MOCK_NSS80_PAYLOAD)

        with patch.object(mcp, "get_data", _mock_get_data):
            records = await client.fetch_transport_and_freight(lookback_months=6)

        assert len(records) >= 1
        assert records[0].citation.freshness == DataFreshness.LIVE
        assert records[0].unit == "% of households"
        assert records[0].period == "NSS80"

    @pytest.mark.asyncio
    async def test_fetch_pmi_uses_curated_mirror(self, temp_db, sample_pmi_record):
        """PMI has no MoSPI MCP dataset — served honestly from cache as CACHED."""
        from services_sector import client, database

        database.upsert_rows("services_pmi", [{
            "period": sample_pmi_record.period,
            "headline_pmi": sample_pmi_record.headline_pmi,
            "new_orders_idx": sample_pmi_record.new_orders_idx,
            "input_costs_idx": sample_pmi_record.input_costs_idx,
            "employment_idx": sample_pmi_record.employment_idx,
            "citation": json.dumps({
                "source_agent": "services_sector",
                "source_authority": "S&P Global / HSBC",
                "document_title": "HSBC India Services PMI Press Release",
                "table_reference": "sp_global.services_pmi_india",
                "retrieval_url": "https://www.pmi.spglobal.com",
                "observation_period": "2026-07",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

        records = await client.fetch_services_pmi(lookback_months=6)

        assert records[0].headline_pmi == 59.2
        assert records[0].citation.freshness == DataFreshness.CACHED
        assert records[0].citation.source_authority == "S&P Global / HSBC"


# ---------------------------------------------------------------------------
# 4. MCP Tool Tests
# ---------------------------------------------------------------------------

class TestMCPTools:
    @pytest.mark.asyncio
    async def test_get_isp_growth_returns_response(self, temp_db):
        from services_sector.mcp_server import get_isp_growth
        from services_sector import client

        async def _mock_fetch(*args, **kwargs):
            from services_sector.models import Citation, ISPRecord, ServiceSubSector
            return [ISPRecord(
                period="2026-03",
                sub_sector=ServiceSubSector.IT_COMPUTER,
                isp_index=146.5,
                isp_yoy_pct=None,
                isp_mom_pct=None,
                citation=Citation(
                    source_authority="NSO, MoSPI",
                    document_title="Test",
                    table_reference="mospi.isp_monthly",
                    retrieval_url="https://mcp.mospi.gov.in",
                    observation_period="2026-03",
                ),
            )]

        with patch.object(client, "fetch_isp_growth", _mock_fetch):
            result = await get_isp_growth(lookback_months=6)

        assert isinstance(result, ISPGrowthResponse)
        assert result.total_records == 1

    @pytest.mark.asyncio
    async def test_get_isp_growth_returns_unavailable_on_error(self, temp_db):
        from services_sector.mcp_server import get_isp_growth
        from services_sector import client
        from services_sector.cache_loaders import ServicesDataUnavailableError

        async def _raise(*args, **kwargs):
            raise ServicesDataUnavailableError("Both sources unavailable.")

        with patch.object(client, "fetch_isp_growth", _raise):
            result = await get_isp_growth(lookback_months=6)

        assert isinstance(result, UnavailableResponse)
        assert result.status == DataFreshness.UNAVAILABLE
        assert result.tool == "get_isp_growth"


# ---------------------------------------------------------------------------
# 5. FastAPI Sub-App Tests
# ---------------------------------------------------------------------------

class TestServicesAPI:
    async def test_health_returns_200(self):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["sector"] == "services_sector"

    async def test_metadata_endpoint_structure(self):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sector"] == "services_sector"
        assert len(data["tools"]) == 4
        assert "owns" in data
        assert "does_not_own" in data
        assert data["mcp_workflow"] == "list_datasets -> get_indicators -> get_metadata -> get_data"

    async def test_isp_growth_endpoint_503_on_unavailable(self, temp_db):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        from services_sector import client
        from services_sector.cache_loaders import ServicesDataUnavailableError

        async def _raise(*args, **kwargs):
            raise ServicesDataUnavailableError("No data available.")

        with patch.object(client, "fetch_isp_growth", _raise):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/isp-growth?lookback_months=6")
        assert resp.status_code == 503

    async def test_isp_growth_endpoint_returns_typed_response(self, temp_db, sample_isp_record):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        from services_sector import client

        async def _mock_fetch(*args, **kwargs):
            return [sample_isp_record]

        with patch.object(client, "fetch_isp_growth", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/isp-growth?lookback_months=6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "live"
        assert data["total_records"] == 1
        assert data["records"][0]["sub_sector"] == "IT_COMPUTER"

    async def test_services_gva_endpoint_returns_typed_response(self, temp_db, sample_gva_record):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        from services_sector import client

        async def _mock_fetch(*args, **kwargs):
            return [sample_gva_record]

        with patch.object(client, "fetch_services_gva", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/services-gva")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "live"
        assert data["records"][0]["segment"] == "Financial Services"

    async def test_services_pmi_endpoint_returns_typed_response(self, temp_db, sample_pmi_record):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        from services_sector import client

        async def _mock_fetch(*args, **kwargs):
            return [sample_pmi_record]

        with patch.object(client, "fetch_services_pmi", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/services-pmi?lookback_months=6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"][0]["headline_pmi"] == 59.2

    async def test_transport_freight_endpoint_returns_typed_response(self, temp_db):
        from httpx import AsyncClient, ASGITransport
        from services_sector.api.app import app
        from services_sector import client
        from services_sector.models import Citation, TransportFreightRecord

        async def _mock_fetch(*args, **kwargs):
            return [TransportFreightRecord(
                period="NSS80",
                indicator="telecom_smartphone_only_rural",
                value=53.0,
                unit="% of households",
                yoy_pct=None,
                citation=Citation(
                    source_authority="NSO, MoSPI",
                    document_title="NSS80 CMST",
                    table_reference="mospi.nss80_cmst",
                    retrieval_url="https://mcp.mospi.gov.in",
                    observation_period="NSS80",
                ),
            )]

        with patch.object(client, "fetch_transport_and_freight", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/transport-freight?lookback_months=6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"][0]["unit"] == "% of households"


# ---------------------------------------------------------------------------
# 6. LangGraph Agent Node Tests
# ---------------------------------------------------------------------------

class TestServicesAgentNode:
    @pytest.mark.asyncio
    async def test_reasoning_continues_after_token_cap(self):
        """A 'length' stop must resume, not cut the answer mid-section."""
        from services_sector.agent import _execute_groq_reasoning

        first = MagicMock()
        first.message.content = "## Executive Summary\nMomentum is strong "
        first.finish_reason = "length"
        second = MagicMock()
        second.message.content = "and broad-based.\n\n## Attribution\nDone."
        second.finish_reason = "stop"

        mock_groq = MagicMock()
        mock_groq.chat.completions.create = AsyncMock(side_effect=[
            MagicMock(choices=[first]),
            MagicMock(choices=[second]),
        ])

        text = await _execute_groq_reasoning(mock_groq, "system", "user")

        assert text == (
            "## Executive Summary\nMomentum is strong and broad-based.\n\n## Attribution\nDone."
        )
        assert mock_groq.chat.completions.create.await_count == 2

    @pytest.mark.asyncio
    async def test_reasoning_single_call_when_clean_stop(self):
        """No continuation call when the model stops cleanly."""
        from services_sector.agent import _execute_groq_reasoning

        only = MagicMock()
        only.message.content = "Complete answer."
        only.finish_reason = "stop"

        mock_groq = MagicMock()
        mock_groq.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[only])
        )

        text = await _execute_groq_reasoning(mock_groq, "system", "user")

        assert text == "Complete answer."
        assert mock_groq.chat.completions.create.await_count == 1

    def test_deterministic_service_selection_is_narrow(self):
        from services_sector.agent import _select_services_deterministically

        assert _select_services_deterministically(
            "How is India's IT services sector performing?"
        ) == {"isp_growth"}
        assert _select_services_deterministically(
            "What is the current Services PMI reading?"
        ) == {"services_pmi"}
        assert _select_services_deterministically(
            "Compare structural services GVA with high-frequency ISP momentum."
        ) == {"isp_growth", "services_gva"}
        overview = _select_services_deterministically(
            "Give me a comprehensive overview of the services sector."
        )
        assert overview == {
            "isp_growth", "services_gva", "services_pmi",
            "transport_freight", "market_context", "services_news",
        }

    @pytest.mark.asyncio
    async def test_agent_node_fetches_only_selected_pillar(self, temp_db, sample_pmi_record):
        """A PMI-only prompt must not emit other pillars as 'unavailable'."""
        from services_sector.agent import services_agent_node
        from services_sector import client

        async def _fail(*args, **kwargs):
            raise AssertionError("unselected pillar must not be fetched")

        async def _mock_pmi(*args, **kwargs):
            return [sample_pmi_record]

        mock_choice = MagicMock()
        mock_choice.message.content = "PMI holds above 50, signalling expansion."
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [mock_choice]
        mock_groq = MagicMock()
        mock_groq.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

        with patch.object(client, "fetch_services_pmi", _mock_pmi), \
             patch.object(client, "fetch_isp_growth", _fail), \
             patch.object(client, "fetch_services_gva", _fail), \
             patch.object(client, "fetch_transport_and_freight", _fail), \
             patch("services_sector.agent.get_groq_client", return_value=mock_groq):
            result = await services_agent_node({
                "query": "What is the current Services PMI reading?",
                "_selected_services": {"services_pmi"},
            })

        data = result["services_sector_data"]
        assert "services_pmi" in data
        assert "isp_general" not in data
        assert "services_gva_structural" not in data
        assert "transport_freight_telecom" not in data
        assert set(result["services_sector_freshness"]) == {"services_pmi"}
        assert all(
            c["dataset"] == "services_pmi" for c in result["services_sector_citations"]
        )

    @pytest.mark.asyncio
    async def test_agent_node_honours_empty_selection(self, temp_db):
        """An explicit empty selection fetches nothing instead of everything."""
        from services_sector.agent import services_agent_node
        from services_sector import client

        async def _fail(*args, **kwargs):
            raise AssertionError("nothing must be fetched")

        with patch.object(client, "fetch_isp_growth", _fail), \
             patch.object(client, "fetch_services_gva", _fail), \
             patch.object(client, "fetch_services_pmi", _fail), \
             patch.object(client, "fetch_transport_and_freight", _fail):
            result = await services_agent_node({
                "query": "Tell me a joke.",
                "_selected_services": set(),
            })

        assert result["services_sector_data"]["tool_routing"]["selected_services"] == []
        assert result["services_sector_freshness"] == {}
        assert result["services_sector_citations"] == []

    @pytest.mark.asyncio
    async def test_agent_node_runs_with_mocked_llm(self, temp_db):
        from services_sector.agent import services_agent_node, select_isp_sub_sector
        from services_sector import client
        from services_sector.models import ServiceSubSector

        # Prompt → tool routing check
        assert select_isp_sub_sector("How is IT services performing?") == ServiceSubSector.IT_COMPUTER
        assert select_isp_sub_sector("Overall services momentum?") is None

        test_cit = Citation(
            source_authority="NSO, MoSPI",
            document_title="Test Pub",
            table_reference="mospi.isp_monthly",
            retrieval_url="https://mcp.mospi.gov.in",
            observation_period="2026-07",
        )

        async def _mock_isp(*args, **kwargs):
            return [ISPRecord(
                period="2026-03", sub_sector=ServiceSubSector.IT_COMPUTER,
                isp_index=146.5, isp_yoy_pct=None, isp_mom_pct=1.2, citation=test_cit,
            )]

        async def _mock_gva(*args, **kwargs):
            return [ServicesGVARecord(
                period="2023-24", nas_statement="8.12", segment="Financial Services",
                gva_current_cr=1598185.0, gva_constant_cr=972874.0,
                gva_yoy_pct=8.8, citation=test_cit,
            )]

        async def _mock_pmi(*args, **kwargs):
            return [ServicesPMIRecord(
                period="2026-07", headline_pmi=59.2, new_orders_idx=60.1,
                input_costs_idx=54.3, employment_idx=52.8, citation=test_cit,
            )]

        async def _mock_freight(*args, **kwargs):
            return [TransportFreightRecord(
                period="NSS80", indicator="telecom_smartphone_only_rural",
                value=53.0, unit="% of households", yoy_pct=None, citation=test_cit,
            )]

        mock_choice = MagicMock()
        mock_choice.message.content = "Services momentum is broad-based with IT ISP at 146.5 and PMI at 59.2."
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [mock_choice]
        mock_groq = MagicMock()
        mock_groq.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

        with patch.object(client, "fetch_isp_growth", _mock_isp), \
             patch.object(client, "fetch_services_gva", _mock_gva), \
             patch.object(client, "fetch_services_pmi", _mock_pmi), \
             patch.object(client, "fetch_transport_and_freight", _mock_freight), \
             patch("services_sector.agent.get_groq_client", return_value=mock_groq):

            result = await services_agent_node({"query": "How is India's IT services sector performing?"})

        assert "services_sector_analysis" in result
        assert "Services momentum" in result["services_sector_analysis"]
        assert result["services_sector_freshness"]["isp_it_computer"] == "live"
        assert result["services_sector_data"]["isp_it_computer"]["isp_index"] == 146.5
        # MCP publishes sub-sectors only — General is honestly unavailable
        assert result["services_sector_data"]["isp_general"]["status"] == "unavailable"
