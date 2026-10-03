"""Pytest test suite for the Capital Markets Sector."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
import httpx

from capital_market_sector.models import (
    Citation,
    DataFreshness,
    GSecYieldRecord,
    IndiaVixRecord,
    NiftySnapshotRecord,
    UnavailableResponse,
)


@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="National Stock Exchange of India (NSE)",
        document_title="NSE Capital Market Daily Bhavcopy",
        table_reference="capital_market_sector.nifty_50_bhavcopy",
        retrieval_url="https://mcp.nseindia.in/bhavcopy/cm/mcp",
        observation_period="2024-09-30",
        freshness=DataFreshness.LIVE,
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_capital.duckdb"
    monkeypatch.setattr("capital_market_sector.database._DB_PATH", db_path)
    from capital_market_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


class TestCapitalMarketModels:
    def test_nifty_record(self, valid_citation):
        rec = NiftySnapshotRecord(
            period="2024-09-30",
            index_name="NIFTY 50",
            close_price=25810.85,
            citation=valid_citation,
        )
        assert rec.close_price == 25810.85

    def test_sector_ownership_boundary(self, valid_citation):
        """Capital Markets cannot own USD/INR (External sector owns USD/INR)."""
        rec = NiftySnapshotRecord(
            period="2024-09-30",
            index_name="NIFTY 50",
            close_price=25810.85,
            citation=valid_citation,
        )
        assert not hasattr(rec, "usd_inr_rate")


@pytest.mark.asyncio
async def test_agent_uses_finance_compatible_reasoning_model(monkeypatch):
    from capital_market_sector import agent

    observed = {}

    async def select_nifty(**_kwargs):
        return {"nifty_snapshot"}, None

    async def fetch_nifty():
        return [{
            "period": "2026-10-02",
            "close_price": 25000.0,
            "citation": {"freshness": "upstream_snapshot"},
        }]

    async def capture_reasoning(**kwargs):
        observed.update(kwargs)
        return "NIFTY 50 closed at 25,000 points."

    monkeypatch.setattr(agent, "select_relevant_services_with_llm", select_nifty)
    monkeypatch.setitem(agent._FETCHERS, "nifty_snapshot", fetch_nifty)
    monkeypatch.setattr(agent, "reason_over_sector_data", capture_reasoning)

    await agent.capital_agent_node({"query": "NIFTY 50 latest close"})

    assert observed["model"] == "openai/gpt-oss-120b"


class TestCapitalMarketDatabase:
    def test_upsert_and_query_nifty(self, temp_db, valid_citation):
        from capital_market_sector import database
        row = {
            "period": "2024-09-30",
            "index_name": "NIFTY 50",
            "open_price": 25820.0,
            "high_price": 25950.0,
            "low_price": 25780.0,
            "close_price": 25810.85,
            "change_points": 35.5,
            "change_pct": 0.14,
            "volume_shares": 350000000.0,
            "turnover_cr": 45000.0,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("nifty_snapshot", [row])
        assert written == 1

        rows = database.query_latest_rows("nifty_snapshot", 10)
        assert len(rows) == 1
        assert rows[0]["close_price"] == 25810.85


class TestCapitalMarketAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from capital_market_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["sector"] == "capital_market_sector"
