"""Pytest test suite for the External Sector."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
import httpx

from external_sector.models import (
    Citation,
    DataFreshness,
    ForexReservesRecord,
    TradeBalanceRecord,
    UnavailableResponse,
)
from external_sector.parsers import parse_exchange_rates, parse_trade_balance


@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="Reserve Bank of India (RBI)",
        document_title="RBI Forex Reserves",
        table_reference="external_sector.r540_forex_reserves",
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


class TestExternalModels:
    def test_forex_record(self, valid_citation):
        rec = ForexReservesRecord(
            period="18-Sep-2026",
            total_reserves_usd_mn=765901.0,
            total_reserves_inr_cr=7342985.0,
            citation=valid_citation,
        )
        assert rec.total_reserves_usd_mn == 765901.0

    def test_unavailable_response(self):
        resp = UnavailableResponse(tool="get_forex_reserves", reason="DBIE unavailable")
        assert resp.status == DataFreshness.UNAVAILABLE


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
        assert records[0].exports_usd_bn == pytest.approx(44.2435)
        assert records[0].imports_usd_bn == pytest.approx(76.2232)
        assert records[0].trade_balance_usd_bn == pytest.approx(-31.9798)
        assert records[0].citation.table_reference == (
            "external_sector.r433_india_s_foreign_trade_us_dollars"
        )
        assert records[0].citation.freshness is DataFreshness.LIVE

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
        assert records[0].citation.table_reference == "external_sector.r575_exchange_rate"
        assert records[0].citation.observation_period == "2026-09-28"


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
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("forex_reserves", [row])
        assert written == 1

        rows = database.query_latest_rows("forex_reserves", 10)
        assert len(rows) == 1
        assert rows[0]["total_reserves_usd_mn"] == 765901.0


class TestExternalLiveClient:
    @pytest.mark.asyncio
    async def test_trade_and_exchange_live_fetches_are_persisted(self, monkeypatch):
        from external_sector import client

        calls = []
        persisted = []

        async def fetch_json(_client, url, params):
            calls.append((url, params))
            columns = ["src_file", "tab", "period", "row_no", "c1", "c2", "c3", "c4", "c5"]
            if url.endswith("r433_india_s_foreign_trade_us_dollars/rows"):
                rows = [[
                    "file.csv", "Trade", "full-history", 8, "2026-27", "July",
                    "44,243.5", "76,223.2", "-31,979.8",
                ]]
            else:
                rows = [[
                    "file.csv", "Daily", "full-history", 8, "28-Sep-2026",
                    "95.9681", "127.0320", "109.2043", "60.8800",
                ]]
            return {"columns": columns, "rows": rows}

        monkeypatch.setattr(client, "_fetch_json", fetch_json)
        monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
        monkeypatch.setattr(
            client.db,
            "upsert_rows",
            lambda table, rows: persisted.extend((table, row) for row in rows) or len(rows),
        )
        monkeypatch.setattr(client.db, "log_fetch", lambda *args, **kwargs: None)

        trade = await client.fetch_trade_balance(lookback_months=1)
        exchange = await client.fetch_exchange_rate_snapshot(lookback_months=1)

        assert trade[0].trade_balance_usd_bn == pytest.approx(-31.9798)
        assert exchange[0].usd_inr_rate == pytest.approx(95.9681)
        assert [item[0] for item in calls] == [
            client._TRADE_BALANCE_API_URL,
            client._EXCHANGE_RATE_API_URL,
        ]
        assert [table for table, _ in persisted] == ["trade_balance", "exchange_rates"]


class TestExternalAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from external_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["sector"] == "external_sector"
