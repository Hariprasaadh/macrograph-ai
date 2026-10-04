"""Pytest test suite for the Capital Markets Sector.

Validates all 10 domain responsibilities, data models, schema persistence,
FastMCP tools, and REST API endpoints.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from capital_market_sector.models import (
    Citation,
    CorporateEarningsRecord,
    DataFreshness,
    FpiFlowsRecord,
    GSecYieldRecord,
    IndiaVixRecord,
    InvestorParticipationRecord,
    MarketBreadthRecord,
    MarketEconomyLinkageRecord,
    MutualFundFlowsRecord,
    NiftySnapshotRecord,
    PrimaryMarketRecord,
    SectoralPerformanceRecord,
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
        """Capital Markets cannot own USD/INR directly (External sector owns USD/INR)."""
        rec = NiftySnapshotRecord(
            period="2024-09-30",
            index_name="NIFTY 50",
            close_price=25810.85,
            citation=valid_citation,
        )
        assert not hasattr(rec, "usd_inr_rate")

    def test_mutual_fund_flows_model(self, valid_citation):
        rec = MutualFundFlowsRecord(
            period="2024-09",
            equity_inflows_cr=34419.0,
            sip_inflow_cr=24508.0,
            total_mf_aum_lakh_cr=67.09,
            net_inflow_cr=71114.0,
            citation=valid_citation,
        )
        assert rec.sip_inflow_cr == 24508.0
        assert rec.equity_inflows_cr == 34419.0

    def test_fpi_flows_model(self, valid_citation):
        rec = FpiFlowsRecord(
            period="2024-09",
            fpi_gross_purchases_cr=395412.0,
            fpi_gross_sales_cr=338271.0,
            fpi_net_investment_cr=57141.0,
            fpi_net_investment_usd_mn=6832.0,
            dii_net_investment_cr=31859.0,
            citation=valid_citation,
        )
        assert rec.fpi_net_investment_cr == 57141.0
        assert rec.dii_net_investment_cr == 31859.0

    def test_corporate_earnings_model(self, valid_citation):
        rec = CorporateEarningsRecord(
            period="2024-09",
            index_name="NIFTY 50",
            ttm_eps=1042.50,
            pe_ratio=24.75,
            pb_ratio=4.15,
            dividend_yield_pct=1.22,
            pat_growth_yoy_pct=11.4,
            citation=valid_citation,
        )
        assert rec.ttm_eps == 1042.50
        assert rec.pe_ratio == 24.75

    def test_sectoral_performance_model(self, valid_citation):
        rec = SectoralPerformanceRecord(
            period="2024-09-30",
            nifty_50_change_pct=0.14,
            nifty_bank_change_pct=0.42,
            nifty_it_change_pct=-0.65,
            leading_sector="NIFTY Bank",
            lagging_sector="NIFTY IT",
            citation=valid_citation,
        )
        assert rec.leading_sector == "NIFTY Bank"
        assert rec.nifty_bank_change_pct == 0.42

    def test_primary_market_model(self, valid_citation):
        rec = PrimaryMarketRecord(
            period="2024-09",
            ipo_count=14,
            ipo_proceeds_cr=11450.0,
            total_equity_raised_cr=22500.0,
            citation=valid_citation,
        )
        assert rec.ipo_count == 14
        assert rec.ipo_proceeds_cr == 11450.0

    def test_investor_participation_model(self, valid_citation):
        rec = InvestorParticipationRecord(
            period="2024-09",
            total_demat_accounts_cr=17.50,
            monthly_demat_additions_lakh=44.0,
            retail_turnover_share_pct=35.8,
            institutional_holding_pct=38.2,
            citation=valid_citation,
        )
        assert rec.total_demat_accounts_cr == 17.50
        assert rec.monthly_demat_additions_lakh == 44.0

    def test_market_economy_linkage_model(self, valid_citation):
        rec = MarketEconomyLinkageRecord(
            period="2024-09",
            nifty_earnings_yield_pct=4.04,
            ten_year_gsec_yield_pct=6.78,
            equity_risk_premium_bps=-274.0,
            market_cap_to_gdp_pct=142.5,
            linkage_regime="Bond Yield Advantage",
            citation=valid_citation,
        )
        assert rec.equity_risk_premium_bps == -274.0
        assert rec.linkage_regime == "Bond Yield Advantage"


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

    def test_all_10_tables_initialized(self, temp_db):
        from capital_market_sector import database
        with database.get_connection() as con:
            tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        expected = {
            "nifty_snapshot", "market_history", "india_vix", "market_breadth",
            "gsec_yields", "mutual_fund_flows", "fpi_flows", "corporate_earnings",
            "sectoral_performance", "primary_market_ipos", "investor_participation",
            "market_economy_linkages", "fetch_log",
        }
        assert expected.issubset(tables)

    def test_canonical_baseline_seeding(self, temp_db):
        from capital_market_sector import database
        database.seed_canonical_baseline()
        mf_rows = database.query_latest_rows("mutual_fund_flows", 1)
        assert len(mf_rows) == 1
        assert mf_rows[0]["sip_inflow_cr"] == 24508.0

        fpi_rows = database.query_latest_rows("fpi_flows", 1)
        assert len(fpi_rows) == 1
        assert fpi_rows[0]["fpi_net_investment_cr"] == 57141.0


class TestCapitalMarketFastMCP:
    @pytest.mark.asyncio
    async def test_mcp_tools_list_covers_all_responsibilities(self):
        from capital_market_sector.mcp_server import mcp_server
        tools = await mcp_server.list_tools()
        names = {t.name for t in tools}
        expected = {
            "get_nifty_snapshot", "get_market_history", "get_india_vix",
            "get_market_breadth", "get_gsec_yield_snapshot", "get_mutual_fund_flows",
            "get_fpi_equity_flows", "get_corporate_earnings_valuation",
            "get_sectoral_performance", "get_primary_market_ipos",
            "get_investor_participation", "get_market_economy_linkages",
        }
        assert expected.issubset(names)


class TestCapitalMarketAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from capital_market_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["sector"] == "capital_market_sector"

    @pytest.mark.asyncio
    async def test_metadata_endpoint(self):
        from capital_market_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/metadata")
        assert res.status_code == 200
        owns = res.json()["owns"]
        assert "nifty_50" in owns
        assert "mutual_fund_flows" in owns
        assert "fpi_equity_flows" in owns
        assert "equity_risk_premium" in owns

    @pytest.mark.asyncio
    async def test_endpoints_return_valid_responses(self):
        from capital_market_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res_mf = await ac.get("/mutual-fund-flows")
            assert res_mf.status_code == 200
            assert res_mf.json()["records"][0]["sip_inflow_cr"] == 24508.0

            res_fpi = await ac.get("/fpi-flows")
            assert res_fpi.status_code == 200
            assert res_fpi.json()["records"][0]["fpi_net_investment_cr"] == 57141.0

            res_earn = await ac.get("/corporate-earnings")
            assert res_earn.status_code == 200
            assert res_earn.json()["records"][0]["pe_ratio"] == 24.75

            res_link = await ac.get("/market-economy-linkages")
            assert res_link.status_code == 200
            assert "equity_risk_premium_bps" in res_link.json()["records"][0]
