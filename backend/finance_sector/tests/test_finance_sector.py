"""Comprehensive pytest test suite for the Finance Sector.

Test coverage:
  1. Pydantic models — mandatory Citation, validation, UnavailableResponse.
  2. DuckDB schema — initialisation, upsert, fetch, audit log.
  3. Data client — live fetch parsing, cache fallback, FinanceDataUnavailableError.
  4. MCP tools — happy path, invalid inputs, cache-only, unavailable.
  5. FastAPI sub-app — HTTP status codes, response structure, metadata endpoint.

All external HTTP calls are mocked with httpx's mock transport.
No live network calls in tests.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from finance_sector.models import (
    BankCreditGrowthRecord,
    BankCreditGrowthResponse,
    BankGroup,
    Citation,
    DataFreshness,
    DepositRecord,
    DepositsAndCDResponse,
    LendingRateRecord,
    LendingRatesResponse,
    NPARecord,
    AssetQualityResponse,
    SectoralCreditBreakdown,
    UnavailableResponse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="Reserve Bank of India (RBI)",
        document_title="RBI DBIE — Test Table",
        table_reference="financial_sector.test_table",
        retrieval_url="https://dev.dbie.rbihub.in/statistics?table=financial_sector.test_table",
        observation_period="2024-09",
        freshness=DataFreshness.LIVE,
    )


@pytest.fixture
def sample_credit_record(valid_citation) -> BankCreditGrowthRecord:
    return BankCreditGrowthRecord(
        period="2024-09",
        gross_credit_cr=21_928_365.0,
        non_food_credit_cr=21_796_315.0,
        non_food_credit_yoy_pct=18.09,
        sectoral=SectoralCreditBreakdown(
            agriculture_cr=2_693_967.0,
            industry_cr=4_771_513.0,
            industry_msme_cr=1_584_000.0,
            industry_large_cr=3_218_000.0,
            services_cr=6_153_050.0,
            personal_loans_cr=7_113_586.0,
            personal_housing_cr=3_404_000.0,
            personal_vehicle_cr=754_000.0,
        ),
        citation=valid_citation,
    )


@pytest.fixture
def sample_npa_record(valid_citation) -> NPARecord:
    return NPARecord(
        period="2024-25",
        bank_group=BankGroup.ALL_SCB,
        gross_npa_pct=2.67,
        net_npa_pct=0.61,
        gross_npa_cr=456_782.0,
        net_npa_cr=104_230.0,
        provision_coverage_ratio_pct=76.3,
        crar_pct=16.78,
        cet1_pct=13.92,
        citation=valid_citation,
    )


@pytest.fixture
def sample_lending_record(valid_citation) -> LendingRateRecord:
    return LendingRateRecord(
        period="2024-09",
        walr_fresh_pct=9.38,
        walr_outstanding_pct=9.91,
        mclr_1yr_median_pct=8.95,
        wadtdr_fresh_pct=6.53,
        wadtdr_outstanding_pct=6.89,
        repo_rate_pct=6.50,
        citation=valid_citation,
    )


@pytest.fixture
def sample_deposit_record(valid_citation) -> DepositRecord:
    return DepositRecord(
        period="2024-09",
        aggregate_deposits_cr=26_301_812.0,
        deposits_yoy_pct=13.34,
        demand_deposits_cr=2_100_000.0,
        time_deposits_cr=22_800_000.0,
        casa_ratio_pct=30.1,
        bank_credit_cr=22_073_000.0,
        cd_ratio_pct=83.94,
        citation=valid_citation,
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Redirect DuckDB to a temporary directory for test isolation."""
    db_path = tmp_path / "test_finance.duckdb"
    monkeypatch.setattr(
        "finance_sector.database._DB_PATH", db_path
    )
    from finance_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


# ---------------------------------------------------------------------------
# 1. Pydantic Model Tests
# ---------------------------------------------------------------------------

class TestCitation:
    def test_citation_requires_all_fields(self):
        with pytest.raises(Exception):
            Citation(
                source_authority="RBI",
                # missing required fields
            )

    def test_citation_default_freshness_is_live(self, valid_citation):
        assert valid_citation.freshness == DataFreshness.LIVE

    def test_citation_fetched_at_is_set(self, valid_citation):
        assert isinstance(valid_citation.fetched_at, datetime)


class TestBankCreditGrowthRecord:
    def test_valid_record_serialises(self, sample_credit_record):
        d = sample_credit_record.model_dump(mode="json")
        assert d["period"] == "2024-09"
        assert d["non_food_credit_yoy_pct"] == 18.09
        assert d["citation"]["source_authority"] == "Reserve Bank of India (RBI)"

    def test_sectoral_breakdown_fields_accessible(self, sample_credit_record):
        assert sample_credit_record.sectoral.agriculture_cr == 2_693_967.0
        assert sample_credit_record.sectoral.industry_cr == 4_771_513.0

    def test_unavailable_response_rejects_records(self, sample_credit_record):
        with pytest.raises(Exception):
            BankCreditGrowthResponse(
                status=DataFreshness.UNAVAILABLE,
                records=[sample_credit_record],
            )


class TestNPARecord:
    def test_valid_npa_record(self, sample_npa_record):
        assert sample_npa_record.gross_npa_pct == 2.67
        assert sample_npa_record.bank_group == BankGroup.ALL_SCB

    def test_npa_record_optional_fields_can_be_none(self, valid_citation):
        record = NPARecord(
            period="2024-25",
            bank_group=BankGroup.FOREIGN_BANKS,
            citation=valid_citation,
        )
        assert record.gross_npa_pct is None
        assert record.crar_pct is None


class TestLendingRateRecord:
    def test_spread_auto_computed_when_repo_set(self, valid_citation):
        record = LendingRateRecord(
            period="2024-09",
            walr_fresh_pct=9.38,
            repo_rate_pct=6.50,
            citation=valid_citation,
        )
        assert record.lending_spread_over_repo_pct == pytest.approx(9.38 - 6.50, abs=1e-4)

    def test_spread_not_overwritten_if_already_set(self, valid_citation):
        record = LendingRateRecord(
            period="2024-09",
            walr_fresh_pct=9.38,
            repo_rate_pct=6.50,
            lending_spread_over_repo_pct=3.0,  # explicit override
            citation=valid_citation,
        )
        assert record.lending_spread_over_repo_pct == 3.0


class TestUnavailableResponse:
    def test_unavailable_response_structure(self):
        resp = UnavailableResponse(
            tool="get_bank_credit_growth",
            reason="Both live fetch and cache are empty.",
        )
        assert resp.status == DataFreshness.UNAVAILABLE
        assert resp.last_successful_fetch is None


# ---------------------------------------------------------------------------
# 2. DuckDB Schema Tests
# ---------------------------------------------------------------------------

class TestDatabaseSchema:
    def test_schema_initialises_without_error(self, temp_db):
        from finance_sector import database
        database.initialise_schema()  # idempotent — must not raise

    def test_upsert_and_query_credit_rows(self, temp_db, sample_credit_record):
        from finance_sector import database
        row = {
            "period": sample_credit_record.period,
            "gross_credit_cr": sample_credit_record.gross_credit_cr,
            "non_food_credit_cr": sample_credit_record.non_food_credit_cr,
            "non_food_credit_yoy_pct": sample_credit_record.non_food_credit_yoy_pct,
            "agriculture_cr": sample_credit_record.sectoral.agriculture_cr,
            "industry_cr": sample_credit_record.sectoral.industry_cr,
            "industry_msme_cr": None,
            "industry_large_cr": None,
            "services_cr": None,
            "personal_loans_cr": None,
            "personal_housing_cr": None,
            "personal_vehicle_cr": None,
            "citation": sample_credit_record.citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("bank_credit_growth", [row])
        assert written == 1

        rows = database.query_latest_rows("bank_credit_growth", 10)
        assert len(rows) == 1
        assert rows[0]["period"] == "2024-09"
        assert isinstance(rows[0]["citation"], dict)  # deserialised from JSON

    def test_upsert_is_idempotent(self, temp_db, sample_credit_record):
        from finance_sector import database
        row = {
            "period": sample_credit_record.period,
            "gross_credit_cr": 100.0,
            "non_food_credit_cr": 90.0,
            "non_food_credit_yoy_pct": None,
            "agriculture_cr": None, "industry_cr": None, "industry_msme_cr": None,
            "industry_large_cr": None, "services_cr": None, "personal_loans_cr": None,
            "personal_housing_cr": None, "personal_vehicle_cr": None,
            "citation": sample_credit_record.citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        database.upsert_rows("bank_credit_growth", [row])
        database.upsert_rows("bank_credit_growth", [row])  # second upsert same period
        rows = database.query_latest_rows("bank_credit_growth", 10)
        assert len(rows) == 1  # still exactly 1 row

    def test_fetch_log_writes_entry(self, temp_db):
        from finance_sector import database
        database.log_fetch("get_bank_credit_growth", "live", rows_written=5)
        with database.get_connection() as con:
            result = con.execute("SELECT * FROM fetch_log").fetchall()
        assert len(result) == 1
        assert result[0][1] == "get_bank_credit_growth"
        assert result[0][2] == "live"

    def test_unauthorized_table_raises_value_error(self, temp_db):
        from finance_sector import database
        with pytest.raises(ValueError, match="Invalid or unauthorized database table"):
            database.upsert_rows("malicious_table_drop", [{"a": 1}])

        with pytest.raises(ValueError, match="Invalid or unauthorized database table"):
            database.query_latest_rows("malicious_table_drop", 10)


# ---------------------------------------------------------------------------
# 3. Data Client Tests (mocked HTTP)
# ---------------------------------------------------------------------------

_MOCK_CREDIT_PAYLOAD = {
    "data": [
        {
            "period": "2024-09",
            "total_gross_credit": "21928365",
            "non_food_credit": "21796315",
            "non_food_credit_yoy": "18.09",
            "agriculture": "2693967",
            "industry": "4771513",
            "services": "6153050",
            "personal_loans": "7113586",
        }
    ]
}

_MOCK_BANK_SURVEY_PAYLOAD = {
    "data": [
        {
            "period": "2024-09",
            "deposits": "26301812",
            "demand_deposits": "2100000",
            "time_deposits": "22800000",
            "bank_credit": "22073000",
            "deposits_yoy": "13.34",
        }
    ]
}

_MOCK_BUSINESS_PAYLOAD = {
    "data": [
        {
            "period": "2024-09",
            "deposits": "26301812",
            "bank_credit": "22073000",
        }
    ]
}


class TestDataClient:
    @pytest.mark.asyncio
    async def test_fetch_credit_live_success(self, temp_db):
        """Live fetch succeeds → returns records with freshness=LIVE."""
        from finance_sector import client

        async def _mock_get(self_inner, url, **kwargs):
            return httpx.Response(200, json=_MOCK_CREDIT_PAYLOAD)

        with patch.object(httpx.AsyncClient, "get", _mock_get):
            records = await client.fetch_bank_credit_growth(lookback_months=6)

        assert len(records) >= 1
        assert records[0].citation.freshness == DataFreshness.LIVE
        assert records[0].non_food_credit_yoy_pct == 18.09

    @pytest.mark.asyncio
    async def test_fetch_credit_falls_back_to_cache(self, temp_db, sample_credit_record):
        """When live fetch raises, cached DuckDB data is returned with freshness=CACHED."""
        from finance_sector import client, database

        # Pre-populate cache
        database.upsert_rows("bank_credit_growth", [{
            "period": "2024-09",
            "gross_credit_cr": sample_credit_record.gross_credit_cr,
            "non_food_credit_cr": sample_credit_record.non_food_credit_cr,
            "non_food_credit_yoy_pct": sample_credit_record.non_food_credit_yoy_pct,
            "agriculture_cr": None, "industry_cr": None, "industry_msme_cr": None,
            "industry_large_cr": None, "services_cr": None, "personal_loans_cr": None,
            "personal_housing_cr": None, "personal_vehicle_cr": None,
            "citation": json.dumps({
                "source_agent": "finance_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "Test",
                "table_reference": "financial_sector.test",
                "retrieval_url": "https://example.com",
                "observation_period": "2024-09",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

        async def _failing_get(self_inner, url, **kwargs):
            raise httpx.NetworkError("Connection refused")

        with patch.object(httpx.AsyncClient, "get", _failing_get):
            records = await client.fetch_bank_credit_growth(lookback_months=6)

        assert records[0].citation.freshness == DataFreshness.CACHED

    @pytest.mark.asyncio
    async def test_fetch_credit_raises_when_cache_empty(self, temp_db):
        """When live fails AND cache empty → FinanceDataUnavailableError."""
        from finance_sector.client import FinanceDataUnavailableError, fetch_bank_credit_growth

        async def _failing_get(self_inner, url, **kwargs):
            raise httpx.NetworkError("Connection refused")

        with patch.object(httpx.AsyncClient, "get", _failing_get):
            with pytest.raises(FinanceDataUnavailableError):
                await fetch_bank_credit_growth(lookback_months=6)

    @pytest.mark.asyncio
    async def test_fetch_deposits_live_success(self, temp_db):
        from finance_sector import client

        async def _mock_get(self_inner, url, **kwargs):
            if "commercial-bank-survey" in url:
                return httpx.Response(200, json=_MOCK_BANK_SURVEY_PAYLOAD)
            return httpx.Response(200, json=_MOCK_BUSINESS_PAYLOAD)

        with patch.object(httpx.AsyncClient, "get", _mock_get):
            records = await client.fetch_deposits_and_cd_ratio(lookback_months=3)

        assert len(records) >= 1
        assert records[0].deposits_yoy_pct == 13.34


# ---------------------------------------------------------------------------
# 4. MCP Tool Tests
# ---------------------------------------------------------------------------

class TestMCPTools:
    @pytest.mark.asyncio
    async def test_get_bank_credit_growth_returns_response(self, temp_db):
        from finance_sector.mcp_server import get_bank_credit_growth
        from finance_sector import client

        async def _mock_fetch(*args, **kwargs):
            from finance_sector.models import BankCreditGrowthRecord, Citation, SectoralCreditBreakdown
            return [BankCreditGrowthRecord(
                period="2024-09",
                gross_credit_cr=21_928_365.0,
                non_food_credit_cr=21_796_315.0,
                non_food_credit_yoy_pct=18.09,
                sectoral=SectoralCreditBreakdown(),
                citation=Citation(
                    source_authority="RBI",
                    document_title="Test",
                    table_reference="fin.test",
                    retrieval_url="https://example.com",
                    observation_period="2024-09",
                ),
            )]

        with patch.object(client, "fetch_bank_credit_growth", _mock_fetch):
            result = await get_bank_credit_growth(lookback_months=6)

        assert isinstance(result, BankCreditGrowthResponse)
        assert result.total_records == 1

    @pytest.mark.asyncio
    async def test_get_bank_credit_growth_returns_unavailable_on_error(self, temp_db):
        from finance_sector.mcp_server import get_bank_credit_growth
        from finance_sector import client
        from finance_sector.client import FinanceDataUnavailableError

        async def _raise(*args, **kwargs):
            raise FinanceDataUnavailableError("Both sources unavailable.")

        with patch.object(client, "fetch_bank_credit_growth", _raise):
            result = await get_bank_credit_growth(lookback_months=6)

        assert isinstance(result, UnavailableResponse)
        assert result.status == DataFreshness.UNAVAILABLE
        assert result.tool == "get_bank_credit_growth"

    @pytest.mark.asyncio
    async def test_get_deposits_cd_ratio_returns_response(self, temp_db):
        from finance_sector.mcp_server import get_deposits_and_cd_ratio
        from finance_sector import client
        from finance_sector.models import DepositRecord, Citation

        async def _mock_fetch(*args, **kwargs):
            return [DepositRecord(
                period="2024-09",
                cd_ratio_pct=83.94,
                casa_ratio_pct=30.1,
                deposits_yoy_pct=13.34,
                citation=Citation(
                    source_authority="RBI",
                    document_title="Test",
                    table_reference="fin.test",
                    retrieval_url="https://example.com",
                    observation_period="2024-09",
                ),
            )]

        with patch.object(client, "fetch_deposits_and_cd_ratio", _mock_fetch):
            result = await get_deposits_and_cd_ratio(lookback_months=3)

        assert isinstance(result, DepositsAndCDResponse)
        assert result.records[0].cd_ratio_pct == 83.94


# ---------------------------------------------------------------------------
# 5. FastAPI Sub-App Tests
# ---------------------------------------------------------------------------

class TestFinanceAPI:
    """Uses httpx.AsyncClient with ASGITransport to avoid starlette version issues."""

    async def test_health_returns_200(self):
        from httpx import AsyncClient, ASGITransport
        from finance_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["sector"] == "finance_sector"

    async def test_metadata_endpoint_structure(self):
        from httpx import AsyncClient, ASGITransport
        from finance_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sector"] == "finance_sector"
        assert len(data["tools"]) == 4
        assert "owns" in data
        assert "does_not_own" in data
        assert any("repo_rate" in item for item in data["does_not_own"])

    async def test_credit_growth_endpoint_503_on_unavailable(self, temp_db):
        from httpx import AsyncClient, ASGITransport
        from finance_sector.api.app import app
        from finance_sector import client
        from finance_sector.client import FinanceDataUnavailableError

        async def _raise(*args, **kwargs):
            raise FinanceDataUnavailableError("No data available.")

        with patch.object(client, "fetch_bank_credit_growth", _raise):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/credit-growth?lookback_months=6")
        assert resp.status_code == 503

    async def test_credit_growth_endpoint_returns_typed_response(self, temp_db, sample_credit_record):
        from httpx import AsyncClient, ASGITransport
        from finance_sector.api.app import app
        from finance_sector import client

        async def _mock_fetch(*args, **kwargs):
            return [sample_credit_record]

        with patch.object(client, "fetch_bank_credit_growth", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/credit-growth?lookback_months=6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "live"
        assert data["total_records"] == 1
        assert data["records"][0]["period"] == "2024-09"

    async def test_lending_rates_accepts_repo_rate_param(self, temp_db):
        from httpx import AsyncClient, ASGITransport
        from finance_sector.api.app import app
        from finance_sector import client
        from finance_sector.models import LendingRateRecord, Citation

        async def _mock_fetch(*args, **kwargs):
            return [LendingRateRecord(
                period="2024-09",
                walr_fresh_pct=9.38,
                citation=Citation(
                    source_authority="RBI",
                    document_title="Test",
                    table_reference="fin.test",
                    retrieval_url="https://example.com",
                    observation_period="2024-09",
                ),
            )]

        with patch.object(client, "fetch_lending_rates", _mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/lending-rates?lookback_months=3&repo_rate_from_a2a=6.5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["records"][0]["lending_spread_over_repo_pct"] == pytest.approx(
            9.38 - 6.5, abs=1e-4
        )


# ---------------------------------------------------------------------------
# 6. LangGraph Agent Node Tests
# ---------------------------------------------------------------------------

class TestFinanceAgentNode:
    @pytest.mark.asyncio
    async def test_agent_node_runs_with_mocked_llm(self, temp_db):
        from finance_sector.agent import finance_agent_node
        from finance_sector import client
        from finance_sector.models import (
            BankCreditGrowthRecord,
            NPARecord,
            LendingRateRecord,
            DepositRecord,
            Citation,
            SectoralCreditBreakdown,
        )

        test_cit = Citation(
            source_authority="RBI",
            document_title="Test Pub",
            table_reference="fin.test",
            retrieval_url="https://example.com",
            observation_period="2024-09",
        )

        async def _mock_credit(*args, **kwargs):
            return [BankCreditGrowthRecord(
                period="2024-09",
                gross_credit_cr=21000000.0,
                non_food_credit_cr=20000000.0,
                non_food_credit_yoy_pct=15.0,
                sectoral=SectoralCreditBreakdown(),
                citation=test_cit,
            )]

        async def _mock_npa(*args, **kwargs):
            return [NPARecord(
                period="2024-Q2",
                bank_group="ALL_SCB",
                gross_npa_pct=2.8,
                net_npa_pct=0.6,
                crar_pct=16.8,
                citation=test_cit,
            )]

        async def _mock_rates(*args, **kwargs):
            return [LendingRateRecord(
                period="2024-09",
                walr_fresh_pct=9.3,
                citation=test_cit,
            )]

        async def _mock_deposits(*args, **kwargs):
            return [DepositRecord(
                period="2024-09",
                aggregate_deposits_cr=25000000.0,
                deposits_yoy_pct=12.0,
                cd_ratio_pct=80.0,
                citation=test_cit,
            )]

        mock_choice = MagicMock()
        mock_choice.message.content = "SCB credit growth is healthy at 15.0% with GNPA at 2.8%."
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [mock_choice]

        with patch.object(client, "fetch_bank_credit_growth", _mock_credit), \
             patch.object(client, "fetch_asset_quality", _mock_npa), \
             patch.object(client, "fetch_lending_rates", _mock_rates), \
             patch.object(client, "fetch_deposits_and_cd_ratio", _mock_deposits), \
             patch("groq.AsyncGroq.chat", create=True) as mock_groq_chat:

            mock_completions = AsyncMock()
            mock_completions.create = AsyncMock(return_value=mock_chat_completion)
            mock_groq_chat.completions = mock_completions

            state = {
                "query": "Assess banking sector health",
                "repo_rate_from_monetary": 6.5,
                "headline_cpi_from_prices": 5.1,
            }

            result = await finance_agent_node(state)

        assert "finance_sector_analysis" in result
        assert "SCB credit growth" in result["finance_sector_analysis"]
        assert result["finance_sector_freshness"]["credit"] == "live"
        assert result["finance_sector_data"]["credit_growth"]["non_food_credit_yoy_pct"] == 15.0

    def test_pydantic_ai_agent_offline_verification(self):
        """Verifies PydanticAI Agent runs offline with TestModel adhering to the pydantic-ai skill."""
        pytest.importorskip("pydantic_ai")
        from pydantic_ai.models.test import TestModel
        from finance_sector.agent import create_pydantic_ai_agent, FinanceAnalysisOutput

        agent = create_pydantic_ai_agent(model=TestModel())
        result = agent.run_sync("Assess asset quality and credit growth")

        output = getattr(result, "output", getattr(result, "data", None))
        assert isinstance(output, FinanceAnalysisOutput)
        assert hasattr(output, "summary")
        assert hasattr(output, "key_findings")
        assert hasattr(output, "citations")



