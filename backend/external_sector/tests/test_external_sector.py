"""Pytest test suite for the External Sector.

All tests are fully isolated: no live network calls, no shared state, no file
system side-effects beyond the temp_db fixture.  External HTTP transports
(yfinance, Tavily, RBI DBIE, IMF MCP, MoSPI MCP) are replaced with
deterministic mock fixtures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from external_sector.models import (
    Citation,
    DataFreshness,
    ExternalDebtRecord,
    ForexReservesRecord,
    IMFExternalOutlookRecord,
    LiveMarketRatesRecord,
    RemittancesRecord,
    TradeBalanceRecord,
    UnavailableResponse,
)
from external_sector.parsers import (
    parse_exchange_rates,
    parse_mospi_external_debt,
    parse_mospi_invisibles,
    parse_trade_balance,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="Reserve Bank of India (RBI)",
        document_title="RBI Forex Reserves",
        table_reference="external_sector.r574_forex_reserves",
        retrieval_url="https://dbie.rbihub.in/data/forex-reserves.json",
        observation_period="18-Sep-2026",
        freshness=DataFreshness.LIVE,
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_external.duckdb"
    monkeypatch.setattr("external_sector.database._DB_PATH", db_path)
    from external_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


def _make_citation_dict(period: str = "18-Sep-2026") -> dict[str, Any]:
    return {
        "source_agent": "external_sector",
        "source_authority": "Reserve Bank of India (RBI)",
        "document_title": "RBI Forex Reserves",
        "table_reference": "external_sector.r574_forex_reserves",
        "retrieval_url": "https://dbie.rbihub.in/data/forex-reserves.json",
        "observation_period": period,
        "freshness": "live",
    }


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------

class TestExternalModels:
    def test_forex_record(self, valid_citation):
        rec = ForexReservesRecord(
            period="18-Sep-2026",
            total_reserves_usd_mn=765901.0,
            total_reserves_inr_cr=7342985.0,
            import_cover_months=13.2,
            citation=valid_citation,
        )
        assert rec.total_reserves_usd_mn == 765901.0
        assert rec.import_cover_months == 13.2

    def test_forex_record_import_cover_none_when_not_published(self, valid_citation):
        """import_cover_months must be None when the official source omits the field."""
        rec = ForexReservesRecord(
            period="18-Sep-2026",
            total_reserves_usd_mn=765901.0,
            citation=valid_citation,
        )
        assert rec.import_cover_months is None

    def test_remittances_record(self, valid_citation):
        rec = RemittancesRecord(
            period="2024-25",
            private_transfers_net_usd_mn=124555.8,
            receipts_usd_mn=135426.0,
            payments_usd_mn=10870.2,
            services_net_usd_mn=188823.8,
            citation=valid_citation,
        )
        assert rec.private_transfers_net_usd_mn == pytest.approx(124555.8)
        assert rec.receipts_usd_mn == pytest.approx(135426.0)

    def test_external_debt_record(self, valid_citation):
        rec = ExternalDebtRecord(
            period="2024-12",
            total_debt_usd_bn=682.3,
            general_government_usd_bn=158.4,
            short_term_to_reserves_pct=18.9,
            citation=valid_citation,
        )
        assert rec.total_debt_usd_bn == 682.3
        assert rec.short_term_to_reserves_pct == 18.9

    def test_external_debt_ratios_none_when_unpublished(self, valid_citation):
        """Vulnerability ratios must default to None — never hardcoded."""
        rec = ExternalDebtRecord(
            period="2024-12",
            citation=valid_citation,
        )
        assert rec.short_term_to_reserves_pct is None
        assert rec.debt_to_gdp_pct is None

    def test_live_market_rates_record(self, valid_citation):
        rec = LiveMarketRatesRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            usd_inr=83.95,
            brent_crude_usd=78.50,
            citation=valid_citation,
        )
        assert rec.usd_inr == 83.95
        assert rec.brent_crude_usd == 78.50

    def test_trade_balance_record(self, valid_citation):
        rec = TradeBalanceRecord(
            period="2026-07",
            exports_usd_bn=44.24,
            imports_usd_bn=76.22,
            trade_balance_usd_bn=-31.98,
            services_surplus_usd_bn=15.50,
            citation=valid_citation,
        )
        assert rec.exports_usd_bn == 44.24
        assert rec.trade_balance_usd_bn == -31.98

    def test_imf_outlook_record(self, valid_citation):
        rec = IMFExternalOutlookRecord(
            period="2026",
            current_account_to_gdp_pct=-2.03,
            current_account_balance_usd_bn=-84.46,
            export_volume_growth_pct=4.22,
            citation=valid_citation,
        )
        assert rec.current_account_to_gdp_pct == -2.03
        assert rec.export_volume_growth_pct == 4.22

    def test_unavailable_response(self):
        resp = UnavailableResponse(tool="get_forex_reserves", reason="DBIE unavailable")
        assert resp.status == DataFreshness.UNAVAILABLE


# ---------------------------------------------------------------------------
# Parser unit tests (fully isolated — no I/O)
# ---------------------------------------------------------------------------

class TestExternalLiveParsers:
    def test_trade_parser_normalizes_fiscal_period_and_usd_millions(self):
        records = parse_trade_balance({
            "columns": ["src_file", "tab", "period", "row_no", "c1", "c2", "c3", "c4", "c5"],
            "rows": [
                ["file.csv", "Trade", "full-history", 6, "Year", "Month", "Exports", "Imports", "Trade Balance"],
                ["file.csv", "Trade", "full-history", 8, "2026-27", "July", "44,243.5", "76,223.2", "-31,979.8"],
                ["file.csv", "Trade", "full-history", 9, "2025-26", "March", "38,934.4", "59,898.7", "-20,964.4"],
            ],
        })

        assert [record.period for record in records] == ["2026-07", "2026-03"]
        assert records[0].exports_usd_bn == pytest.approx(44.24)
        assert records[0].imports_usd_bn == pytest.approx(76.22)
        assert records[0].trade_balance_usd_bn == pytest.approx(-31.98)

    def test_trade_parser_skips_rows_with_no_numeric_data(self):
        records = parse_trade_balance({
            "columns": ["c1", "c2", "c3", "c4", "c5"],
            "rows": [
                ["2026-27", "July", None, None, None],
            ],
        })
        assert records == []

    def test_trade_parser_empty_payload(self):
        assert parse_trade_balance({}) == []

    def test_exchange_rate_parser_accepts_official_dbie_columns(self):
        records = parse_exchange_rates({
            "columns": ["src_file", "tab", "period", "row_no", "c1", "c2", "c3", "c4", "c5"],
            "rows": [
                ["file.csv", "Daily", "full-history", 6, "Date", "US Dollar", "Pound", "Euro", "Yen"],
                ["file.csv", "Daily", "full-history", 8, "28-Sep-2026", "95.9681", "127.0320", "109.2043", "60.8800"],
            ],
        })

        assert len(records) == 1
        assert records[0].period == "2026-09-28"
        assert records[0].usd_inr_rate == pytest.approx(95.9681)

    def test_exchange_rate_parser_skips_non_date_rows(self):
        records = parse_exchange_rates({
            "columns": ["c1", "c2"],
            "rows": [
                ["invalid-date", "83.5"],
            ],
        })
        assert records == []

    def test_exchange_rate_parser_empty_payload(self):
        assert parse_exchange_rates({}) == []

    def test_mospi_invisibles_parser(self):
        mock_mospi = [
            {"year": "2024-25", "category": "Private Transfers, Net", "trade_category": None, "value": "124555.81"},
            {"year": "2024-25", "category": "Private Transfers, Net", "trade_category": "Receipts/GDP", "value": "135426.03"},
            {"year": "2024-25", "category": "Non-factor Services", "trade_category": None, "value": "188823.83"},
        ]
        records = parse_mospi_invisibles(mock_mospi)
        assert len(records) == 1
        assert records[0].period == "2024-25"
        assert records[0].private_transfers_net_usd_mn == pytest.approx(124555.81)
        assert records[0].receipts_usd_mn == pytest.approx(135426.03)
        assert records[0].services_net_usd_mn == pytest.approx(188823.83)

    def test_mospi_invisibles_parser_empty(self):
        assert parse_mospi_invisibles([]) == []

    def test_mospi_external_debt_parser_no_fabricated_ratios(self):
        """Parsed records must never carry hardcoded ratio values."""
        mock_debt = [
            {"year": "2024", "month": "December", "external_debt_sector": "General Government",
             "external_debt_term": "long", "unit": "usd million", "value": "158400"},
        ]
        records = parse_mospi_external_debt(mock_debt, lookback_limit=2)
        assert len(records) == 1
        assert records[0].period == "2024-December"
        assert records[0].general_government_usd_bn is not None
        # Ratios must be None when not explicitly published in the source data
        assert records[0].short_term_to_reserves_pct is None
        assert records[0].debt_to_gdp_pct is None

    def test_mospi_external_debt_parser_empty(self):
        assert parse_mospi_external_debt([], lookback_limit=8) == []


# ---------------------------------------------------------------------------
# DuckDB layer — isolated with temp_db fixture
# ---------------------------------------------------------------------------

class TestExternalDatabase:
    def test_upsert_and_query_forex(self, temp_db, valid_citation):
        from external_sector import database
        row = {
            "period": "18-Sep-2026",
            "total_reserves_usd_mn": 765901.0,
            "total_reserves_inr_cr": 7342985.0,
            "foreign_currency_assets_usd_mn": 630980.0,
            "gold_reserves_usd_mn": 111292.0,
            "sdrs_usd_mn": 18200.0,
            "reserve_tranche_position_usd_mn": 5429.0,
            "import_cover_months": 13.2,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("forex_reserves", [row])
        assert written == 1

        rows = database.query_latest_rows("forex_reserves", 10)
        assert len(rows) == 1
        assert rows[0]["total_reserves_usd_mn"] == 765901.0
        assert rows[0]["import_cover_months"] == 13.2

    def test_upsert_idempotent_on_same_period(self, temp_db, valid_citation):
        """Upserting the same period twice must not create duplicate rows."""
        from external_sector import database
        base_row = {
            "period": "2026-09",
            "exports_usd_bn": 40.0,
            "imports_usd_bn": 70.0,
            "trade_balance_usd_bn": -30.0,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        database.upsert_rows("trade_balance", [base_row])
        updated_row = {**base_row, "exports_usd_bn": 42.0}
        database.upsert_rows("trade_balance", [updated_row])
        rows = database.query_latest_rows("trade_balance", 10)
        assert len(rows) == 1
        assert rows[0]["exports_usd_bn"] == pytest.approx(42.0)

    def test_upsert_invalid_table_raises(self, temp_db):
        from external_sector import database
        with pytest.raises(ValueError, match="Invalid table"):
            database.upsert_rows("injected_table; DROP TABLE forex_reserves; --", [{"period": "x"}])

    def test_query_invalid_table_raises(self, temp_db):
        from external_sector import database
        with pytest.raises(ValueError, match="Invalid table"):
            database.query_latest_rows("unknown_table", 10)

    def test_upsert_and_query_bop(self, temp_db, valid_citation):
        """Confirms the corrected 'bop' table name is functional end-to-end."""
        from external_sector import database
        row = {
            "period": "2024-Q1",
            "current_account_balance_usd_bn": -5.7,
            "current_account_to_gdp_pct": -0.6,
            "capital_account_balance_usd_bn": 23.5,
            "net_bop_usd_bn": 17.8,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("bop", [row])
        assert written == 1
        rows = database.query_latest_rows("bop", 5)
        assert len(rows) == 1
        assert rows[0]["net_bop_usd_bn"] == pytest.approx(17.8)

    def test_upsert_and_query_remittances(self, temp_db, valid_citation):
        from external_sector import database
        row = {
            "period": "2024-25",
            "private_transfers_net_usd_mn": 124555.8,
            "receipts_usd_mn": 135426.0,
            "payments_usd_mn": 10870.2,
            "services_receipts_usd_mn": 387540.5,
            "services_net_usd_mn": 188823.8,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("remittances_invisibles", [row])
        assert written == 1

        rows = database.query_latest_rows("remittances_invisibles", 5)
        assert len(rows) == 1
        assert rows[0]["private_transfers_net_usd_mn"] == pytest.approx(124555.8)


# ---------------------------------------------------------------------------
# Client layer — mocked (no live I/O)
# ---------------------------------------------------------------------------

class TestExternalClientMocked:
    @pytest.mark.asyncio
    async def test_fetch_live_market_rates_success(self, valid_citation):
        mock_rates = {
            "usd_inr": 83.95, "eur_inr": 92.10, "gbp_inr": 108.50,
            "jpy_inr": 58.20, "brent_crude": 75.40,
        }
        with patch("external_sector.market_client._fetch_sync_market_rates", return_value=mock_rates):
            from external_sector import client
            mkt = await client.fetch_live_market_rates()
        assert mkt.usd_inr == pytest.approx(83.95)
        assert mkt.brent_crude_usd == pytest.approx(75.40)
        assert mkt.citation.freshness is DataFreshness.LIVE

    @pytest.mark.asyncio
    async def test_fetch_live_market_rates_partial_failure(self):
        """yfinance returning None for some tickers must not raise — None fields are valid."""
        mock_rates = {
            "usd_inr": 83.95, "eur_inr": None, "gbp_inr": None,
            "jpy_inr": None, "brent_crude": None,
        }
        with patch("external_sector.market_client._fetch_sync_market_rates", return_value=mock_rates):
            from external_sector import client
            mkt = await client.fetch_live_market_rates()
        assert mkt.usd_inr == pytest.approx(83.95)
        assert mkt.eur_inr is None

    @pytest.mark.asyncio
    async def test_fetch_trade_balance_falls_back_to_cache_on_dbie_failure(self, temp_db, valid_citation):
        """When DBIE fetch raises, the client must fall back to DuckDB cache."""
        from external_sector.cache_loaders import ExternalDataUnavailableError
        from external_sector.models import TradeBalanceRecord

        sentinel = TradeBalanceRecord(
            period="2026-08",
            exports_usd_bn=44.0,
            imports_usd_bn=74.0,
            trade_balance_usd_bn=-30.0,
            citation=valid_citation,
        )
        with patch("external_sector.client.fetch_raw_trade", side_effect=RuntimeError("DBIE unreachable")), \
             patch("external_sector.client.load_trade_from_cache", return_value=[sentinel]):
            from external_sector import client
            records = await client.fetch_trade_balance(lookback_months=3)
        assert len(records) >= 1
        assert records[0].period == "2026-08"

    @pytest.mark.asyncio
    async def test_fetch_balance_of_payments_reads_bop_table(self, temp_db, valid_citation):
        """Confirms end-to-end that fetch_balance_of_payments reads from the 'bop' table."""
        from external_sector import database
        row = {
            "period": "2024-Q2",
            "current_account_balance_usd_bn": -7.1,
            "current_account_to_gdp_pct": -0.8,
            "capital_account_balance_usd_bn": 19.2,
            "net_bop_usd_bn": 12.1,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        database.upsert_rows("bop", [row])

        from external_sector import client
        records = await client.fetch_balance_of_payments(lookback_quarters=4)
        assert len(records) >= 1
        assert records[0].net_bop_usd_bn == pytest.approx(12.1)

    @pytest.mark.asyncio
    async def test_fetch_realtime_intelligence_mocked(self, valid_citation):
        """Tavily fetch must be fully mocked — no live HTTP."""
        from external_sector.models import RealtimeIntelligenceRecord
        mock_record = RealtimeIntelligenceRecord(
            query="India reserves",
            summary="RBI forex reserves remain adequate.",
            news_items=[{"title": "Reserves stable", "url": "https://example.com", "snippet": "...", "score": 0.9}],
            source_urls=["https://example.com"],
            fetched_at=datetime.now(timezone.utc).isoformat(),
            citation=valid_citation,
        )
        with patch("external_sector.tavily_client.fetch_realtime_intelligence", AsyncMock(return_value=mock_record)):
            from external_sector import client
            rec = await client.fetch_realtime_intelligence("India reserves", max_results=1)
        assert rec.query == "India reserves"
        assert len(rec.summary) > 0

    @pytest.mark.asyncio
    async def test_fetch_imf_external_outlook_mocked(self, valid_citation):
        """IMF MCP call must be fully mocked — no live HTTP."""
        mock_obs = [
            {"series_key": "IND.BCA_NGDPD.A", "period": "2025", "value": -2.1, "source": "IMF WEO"},
            {"series_key": "IND.TX_RPCH.A", "period": "2025", "value": 4.5, "source": "IMF WEO"},
        ]
        with patch.object(
            __import__("external_sector.imf_client", fromlist=["imf_client"]).imf_client,
            "get_india_weo_outlook",
            AsyncMock(return_value=mock_obs),
        ):
            from external_sector import client
            records = await client.fetch_imf_external_outlook("2025", "2025")
        assert len(records) == 1
        assert records[0].period == "2025"


# ---------------------------------------------------------------------------
# FastMCP tool layer — mocked
# ---------------------------------------------------------------------------

class TestExternalFastMCPMocked:
    """Tests for MCP tool logic exercised via the client layer to avoid
    importing mcp_server at module level (which touches the production DB)."""

    @pytest.mark.asyncio
    async def test_mcp_forex_tool_returns_cached_data_on_dbie_failure(self, temp_db, valid_citation):
        from external_sector import client
        from external_sector.models import ForexReservesRecord

        sentinel = ForexReservesRecord(
            period="25-Sep-2026",
            total_reserves_usd_mn=770000.0,
            citation=valid_citation,
        )
        with patch("external_sector.client.fetch_raw_forex", side_effect=RuntimeError("DBIE down")), \
             patch("external_sector.client.load_forex_from_cache", return_value=[sentinel]):
            records = await client.fetch_forex_reserves(lookback_weeks=2)
        assert len(records) > 0
        assert records[0].total_reserves_usd_mn == pytest.approx(770000.0)

    @pytest.mark.asyncio
    async def test_mcp_forex_tool_raises_on_total_failure(self):
        """When both live and cache fail, ExternalDataUnavailableError must propagate."""
        from external_sector import client
        from external_sector.cache_loaders import ExternalDataUnavailableError
        with patch("external_sector.client.fetch_raw_forex", side_effect=RuntimeError("all down")), \
             patch("external_sector.client.load_forex_from_cache", side_effect=ExternalDataUnavailableError("cache empty")):
            with pytest.raises(ExternalDataUnavailableError):
                await client.fetch_forex_reserves(lookback_weeks=2)

    @pytest.mark.asyncio
    async def test_mcp_balance_of_payments_reads_bop_table(self, temp_db, valid_citation):
        """Confirms the BoP client reads from the corrected 'bop' table."""
        from external_sector import database, client
        database.upsert_rows("bop", [{
            "period": "2024-Q3",
            "current_account_balance_usd_bn": -6.0,
            "current_account_to_gdp_pct": -0.7,
            "capital_account_balance_usd_bn": 21.0,
            "net_bop_usd_bn": 15.0,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])
        records = await client.fetch_balance_of_payments(lookback_quarters=4)
        assert len(records) >= 1
        assert records[0].net_bop_usd_bn == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# FastAPI endpoint layer — isolated with ASGI transport
# ---------------------------------------------------------------------------

class TestExternalAPIMocked:
    @pytest.mark.asyncio
    async def test_health_and_metadata_endpoints(self):
        from external_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            h_res = await ac.get("/health")
            m_res = await ac.get("/metadata")

        assert h_res.status_code == 200
        assert h_res.json()["status"] == "healthy"
        assert m_res.status_code == 200
        assert "forex_reserves" in m_res.json()["owns"]
        assert "remittances" in m_res.json()["owns"]

    @pytest.mark.asyncio
    async def test_live_market_rates_endpoint_mocked(self):
        mock_rates = {
            "usd_inr": 83.95, "eur_inr": 92.10, "gbp_inr": 108.50,
            "jpy_inr": 58.20, "brent_crude": 75.40,
        }
        with patch("external_sector.market_client._fetch_sync_market_rates", return_value=mock_rates):
            from external_sector.api.app import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/live-market-rates")
        assert res.status_code == 200
        assert res.json()["status"] == "live"
        assert res.json()["record"]["usd_inr"] == pytest.approx(83.95)

    @pytest.mark.asyncio
    async def test_live_market_rates_endpoint_500_sanitized(self):
        """500 responses must not leak internal error details."""
        with patch("external_sector.client.fetch_live_market_rates", AsyncMock(side_effect=RuntimeError("conn refused: /var/db/external.duckdb"))):
            from external_sector.api.app import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/live-market-rates")
        assert res.status_code == 500
        detail = res.json().get("detail", "")
        assert "conn refused" not in detail
        assert "/var/db" not in detail

    @pytest.mark.asyncio
    async def test_forex_reserves_endpoint_503_on_unavailable(self):
        from external_sector.cache_loaders import ExternalDataUnavailableError
        with patch("external_sector.client.fetch_forex_reserves", AsyncMock(side_effect=ExternalDataUnavailableError("no data"))):
            from external_sector.api.app import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/forex-reserves")
        assert res.status_code == 503

    @pytest.mark.asyncio
    async def test_imf_outlook_endpoint_mocked(self):
        mock_obs = [
            {"series_key": "IND.BCA_NGDPD.A", "period": "2025", "value": -2.1, "source": "IMF WEO"},
        ]
        with patch.object(
            __import__("external_sector.imf_client", fromlist=["imf_client"]).imf_client,
            "get_india_weo_outlook",
            AsyncMock(return_value=mock_obs),
        ):
            from external_sector.api.app import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/imf-outlook?start_year=2025&end_year=2025")
        assert res.status_code == 200
        assert res.json()["total_records"] > 0

    @pytest.mark.asyncio
    async def test_realtime_intelligence_endpoint_503_when_unconfigured(self, monkeypatch):
        """When TVLY_KEY_1 is None, endpoint must return 503 instead of 500."""
        from external_sector.config import external_settings
        monkeypatch.setattr(external_settings, "TVLY_KEY_1", None)
        from external_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/realtime-intelligence")
        assert res.status_code == 503


# ---------------------------------------------------------------------------
# Direct FastMCP tool layer tests
# ---------------------------------------------------------------------------

class TestDirectFastMCPTools:
    @pytest.mark.asyncio
    async def test_mcp_get_exchange_rate_snapshot_direct(self, temp_db, valid_citation):
        """Directly invokes get_exchange_rate_snapshot tool from mcp_server."""
        from external_sector import mcp_server
        from external_sector.models import ExchangeRateRecord

        sentinel = ExchangeRateRecord(
            period="2026-09-18",
            usd_inr_rate=83.92,
            citation=valid_citation,
        )
        with patch("external_sector.client.fetch_exchange_rate_snapshot", AsyncMock(return_value=[sentinel])):
            res = await mcp_server.get_exchange_rate_snapshot(lookback_months=1)
        assert res.status == DataFreshness.LIVE
        assert len(res.records) == 1
        assert res.records[0].usd_inr_rate == pytest.approx(83.92)

    @pytest.mark.asyncio
    async def test_mcp_get_forex_reserves_direct(self, temp_db, valid_citation):
        """Directly invokes get_forex_reserves tool from mcp_server."""
        from external_sector import mcp_server
        from external_sector.models import ForexReservesRecord

        sentinel = ForexReservesRecord(
            period="18-Sep-2026",
            total_reserves_usd_mn=765000.0,
            citation=valid_citation,
        )
        with patch("external_sector.client.fetch_forex_reserves", AsyncMock(return_value=[sentinel])):
            res = await mcp_server.get_forex_reserves(lookback_weeks=1)
        assert res.status == DataFreshness.LIVE
        assert len(res.records) == 1
        assert res.records[0].total_reserves_usd_mn == pytest.approx(765000.0)


# ---------------------------------------------------------------------------
# Chronological sorting & parser edge case tests
# ---------------------------------------------------------------------------

class TestChronologicalSortingAndEdgeCases:
    def test_parse_period_sort_key_chronology(self):
        from external_sector.parsers import parse_period_sort_key

        sep = parse_period_sort_key("18-Sep-2026")
        aug = parse_period_sort_key("28-Aug-2026")
        assert sep > aug  # September must sort after August despite '1' < '2' in string

        q2 = parse_period_sort_key("2024-Q2")
        q1 = parse_period_sort_key("2024-Q1")
        assert q2 > q1

        y2 = parse_period_sort_key("2025-01")
        y1 = parse_period_sort_key("2024-12")
        assert y2 > y1

    def test_parse_mospi_external_debt_honors_lookback_limit(self):
        raw = [
            {"year": "2024", "month": "12", "external_debt_sector": "Total External Debt", "unit": "US Dollar Million", "value": "680000"},
            {"year": "2024", "month": "09", "external_debt_sector": "Total External Debt", "unit": "US Dollar Million", "value": "670000"},
            {"year": "2024", "month": "06", "external_debt_sector": "Total External Debt", "unit": "US Dollar Million", "value": "660000"},
        ]
        records = parse_mospi_external_debt(raw, lookback_limit=2)
        assert len(records) == 2
        assert records[0].period == "2024-12"
        assert records[1].period == "2024-09"

    def test_forex_cache_loader_chronological_order(self, temp_db, valid_citation):
        """DuckDB cache loader must return 18-Sep before 28-Aug."""
        from external_sector import database
        from external_sector.cache_loaders import load_forex_from_cache

        cit_json = valid_citation.model_dump_json()
        now_iso = datetime.now(timezone.utc).isoformat()
        database.upsert_rows("forex_reserves", [
            {"period": "28-Aug-2026", "total_reserves_usd_mn": 760000.0, "citation": cit_json, "fetched_at": now_iso},
            {"period": "18-Sep-2026", "total_reserves_usd_mn": 765901.0, "citation": cit_json, "fetched_at": now_iso},
            {"period": "04-Sep-2026", "total_reserves_usd_mn": 762000.0, "citation": cit_json, "fetched_at": now_iso},
        ])
        records = load_forex_from_cache(limit=10)
        assert len(records) == 3
        # Must be in chronological order descending: Sep 18, Sep 04, Aug 28
        assert records[0].period == "18-Sep-2026"
        assert records[1].period == "04-Sep-2026"
        assert records[2].period == "28-Aug-2026"

