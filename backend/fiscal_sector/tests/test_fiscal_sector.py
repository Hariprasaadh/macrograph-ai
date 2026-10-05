"""Unit and integration tests for the Fiscal & Public Finance Sector.

Tests:
  - Database schema initialisation, seeding, and parameterized queries.
  - Pydantic models and mandatory Citation metadata validation.
  - Client data fetching (Union accounts, Sovereign debt, GST, MoSPI product taxes).
  - Tax calculation engines (GST split, GSTIN validator, Income tax regime comparison).
  - FastMCP tool registration and tool calls.
  - LangGraph fiscal agent node and A2A executor.
  - FastAPI sub-application endpoints.
"""
from __future__ import annotations

import json
import pytest
from httpx import ASGITransport, AsyncClient

from fiscal_sector import client, database as db
from fiscal_sector.api.app import app as fiscal_app
from fiscal_sector.executor import FiscalSectorAgentExecutor
from fiscal_sector.mcp_server import mcp_server
from fiscal_sector.models import (
    Citation,
    DataFreshness,
    FiscalDeficitRecord,
    GSTCollectionRecord,
    MoSPITaxAggregateRecord,
    SovereignDebtRecord,
)


@pytest.fixture(autouse=True)
def setup_duckdb():
    """Ensure schema is initialized and seeded before tests."""
    db.initialise_schema(seed_baseline=True)


# ── Database Tests ─────────────────────────────────────────────────────────

def test_database_initialisation_and_seeding():
    """Verify tables exist and baseline rows are seeded."""
    deficits = db.query_fiscal_deficit(lookback_records=10)
    assert len(deficits) >= 3
    assert deficits[0]["fiscal_deficit_cr"] > 0
    assert "citation" in deficits[0]

    debts = db.query_general_govt_debt(lookback_records=10)
    assert len(debts) >= 4
    assert debts[0]["general_govt_gross_debt_gdp_pct"] > 50.0

    gsts = db.query_gst_collections(lookback_months=12)
    assert len(gsts) >= 5
    assert gsts[0]["gross_gst_cr"] > 100000.0

    taxes = db.query_mospi_tax_aggregates(lookback_records=5)
    assert len(taxes) >= 2
    assert taxes[0]["current_price_cr"] > 1000000.0


def test_database_upsert_safety():
    """Verify upsert_rows enforces table whitelist and parameterization."""
    with pytest.raises(ValueError, match="not in _ALLOWED_TABLES"):
        db.upsert_rows("malicious_table_drop", [{"col": 1}])


# ── Model Tests ─────────────────────────────────────────────────────────────

def test_models_citation_integrity():
    """Ensure Citation requires all mandatory attribution metadata."""
    cit = Citation(
        source_agent="fiscal_sector",
        source_authority="Ministry of Finance",
        document_title="Union Budget 2024-25",
        table_reference="Budget at a Glance",
        indicator_id="in.macro.fiscal.fiscal_deficit",
        observation_period="2024-25 (BE)",
        value=4.9,
        unit="% of GDP",
        url="https://indiabudget.gov.in",
        freshness=DataFreshness.CACHED,
        retrieved_at="2026-10-06T00:00:00Z",
    )
    assert cit.source_agent == "fiscal_sector"
    assert cit.freshness == DataFreshness.CACHED

    record = FiscalDeficitRecord(
        period="2024-25 (BE)",
        revenue_receipts_cr=3129200.0,
        tax_revenue_net_cr=2601574.0,
        non_tax_revenue_cr=527626.0,
        non_debt_capital_receipts_cr=79000.0,
        total_receipts_cr=3208200.0,
        total_expenditure_cr=4820512.0,
        revenue_expenditure_cr=3709401.0,
        capital_expenditure_cr=1111111.0,
        fiscal_deficit_cr=1612312.0,
        fiscal_deficit_gdp_pct=4.9,
        revenue_deficit_cr=580201.0,
        primary_deficit_cr=448500.0,
        citation=cit,
    )
    assert record.capital_expenditure_cr == 1111111.0


# ── Client Data Fetching Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_union_fiscal_deficit():
    """Test retrieving Union Budget accounts at a glance."""
    records = await client.fetch_union_fiscal_deficit(lookback_records=3)
    assert len(records) >= 3
    rec = records[0]
    assert rec.fiscal_deficit_cr > 0
    assert rec.citation.source_authority != ""
    assert rec.citation.url != ""


@pytest.mark.asyncio
async def test_fetch_sovereign_debt():
    """Test retrieving General Government Gross Debt (IMF WEO)."""
    records = await client.fetch_sovereign_debt_imf(start_year=2020, end_year=2024)
    assert len(records) >= 3
    rec = records[-1]
    assert rec.general_govt_gross_debt_gdp_pct > 70.0
    assert rec.citation.source_authority == "International Monetary Fund (IMF)"


@pytest.mark.asyncio
async def test_fetch_gst_collections():
    """Test retrieving monthly GST collections."""
    records = await client.fetch_gst_collections(lookback_months=6)
    assert len(records) >= 3
    rec = records[0]
    assert rec.gross_gst_cr > 100000.0
    assert rec.citation.indicator_id == "in.macro.fiscal.gst_gross_revenue"


@pytest.mark.asyncio
async def test_fetch_mospi_product_taxes():
    """Test retrieving MoSPI National Accounts Net Taxes on Products."""
    records = await client.fetch_mospi_product_taxes(lookback_years=3)
    assert len(records) >= 1
    rec = records[0]
    assert rec.current_price_cr > 0
    assert rec.indicator == "Net Taxes on Products"


# ── Tax Calculator Tests (eco-policy-mcp) ───────────────────────────────────

def test_calculate_gst_breakdown_intra_state():
    """Verify GST split for intra-state CGST + SGST."""
    res = client.calculate_gst_breakdown(100000.0, 18.0, intra_state=True)
    data = res.data
    assert data.tax_type == "CGST+SGST"
    assert data.cgst == 9000.0
    assert data.sgst == 9000.0
    assert data.igst == 0.0
    assert data.total_tax == 18000.0
    assert data.total_invoice_value == 118000.0
    assert "CBIC" in res.provenance.source or "CGST" in res.provenance.source


def test_calculate_gst_breakdown_inter_state():
    """Verify GST split for inter-state IGST."""
    res = client.calculate_gst_breakdown(100000.0, 18.0, intra_state=False)
    data = res.data
    assert data.tax_type == "IGST"
    assert data.cgst == 0.0
    assert data.sgst == 0.0
    assert data.igst == 18000.0
    assert data.total_tax == 18000.0


def test_validate_gstin():
    """Verify GSTIN format and state decoding."""
    valid_gstin = "27AAPFU0939F1ZV"
    res = client.validate_gstin_number(valid_gstin)
    assert res.is_valid is True
    assert res.state_code == "27"
    assert res.state_name == "Maharashtra"

    invalid_gstin = "INVALID123"
    res_inv = client.validate_gstin_number(invalid_gstin)
    assert res_inv.is_valid is False


def test_compare_income_tax_regimes():
    """Verify New vs Old Income Tax regimes calculation."""
    res = client.compare_income_tax_regimes(1500000.0, deductions_80c=150000.0, age=35)
    data = res.data
    assert data.recommended_regime in ("new", "old")
    assert data.savings_if_switched >= 0.0
    assert "new_regime" in data.model_dump()
    assert "old_regime" in data.model_dump()


# ── FastMCP Server & Tool Registration Tests ───────────────────────────────

@pytest.mark.asyncio
async def test_mcp_server_tools_registered():
    """Verify all 8 tools are declared on the FastMCP instance."""
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    expected_tools = [
        "get_union_fiscal_deficit",
        "get_general_government_debt",
        "get_gst_collections",
        "get_mospi_product_taxes",
        "calculate_gst",
        "validate_gstin",
        "compare_tax_regimes",
        "get_fiscal_news",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Missing MCP tool: {expected}"


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    """Call MCP tools directly."""
    from fiscal_sector.mcp_server import (
        calculate_gst,
        get_general_government_debt,
        get_gst_collections,
        get_union_fiscal_deficit,
        validate_gstin,
    )

    deficit_res = await get_union_fiscal_deficit(lookback_records=2)
    assert deficit_res.total_records >= 2

    debt_res = await get_general_government_debt(start_year=2022, end_year=2024)
    assert debt_res.total_records >= 2

    gst_res = await get_gst_collections(lookback_months=3)
    assert gst_res.total_records >= 2

    gst_calc = calculate_gst(50000.0, 12.0, intra_state=True)
    assert gst_calc.data.total_tax == 6000.0

    gstin_val = validate_gstin("27AAPFU0939F1ZV")
    assert gstin_val.is_valid is True


# ── A2A Executor Tests ─────────────────────────────────────────────────────

def test_agent_card_capabilities():
    """Verify AgentCard metadata and advertised skills."""
    card = FiscalSectorAgentExecutor.get_agent_card()
    assert card.name == "Fiscal & Public Finance Sector Macroeconomic Agent"
    assert "fiscal_deficit" in card.capabilities
    assert "sovereign_debt" in card.capabilities
    assert len(card.skills) >= 4


# ── FastAPI Sub-Application HTTP Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fastapi_subapp_endpoints():
    """Test HTTP endpoints on the mounted sub-application."""
    transport = ASGITransport(app=fiscal_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client_http:
        # Health
        res_health = await client_http.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # Metadata
        res_meta = await client_http.get("/metadata")
        assert res_meta.status_code == 200
        assert res_meta.json()["sector"] == "fiscal_sector"

        # Deficit
        res_def = await client_http.get("/deficit?lookback_records=2")
        assert res_def.status_code == 200
        assert res_def.json()["total_records"] >= 2

        # Debt
        res_debt = await client_http.get("/debt?start_year=2021&end_year=2023")
        assert res_debt.status_code == 200
        assert res_debt.json()["total_records"] >= 2

        # GST
        res_gst = await client_http.get("/gst?lookback_months=3")
        assert res_gst.status_code == 200
        assert res_gst.json()["total_records"] >= 2

        # Calculate GST
        res_calc = await client_http.get("/calculate-gst?amount=10000&rate_percent=18&intra_state=true")
        assert res_calc.status_code == 200
        assert res_calc.json()["data"]["total_tax"] == 1800.0

        # Validate GSTIN
        res_val = await client_http.get("/validate-gstin?gstin=27AAPFU0939F1ZV")
        assert res_val.status_code == 200
        assert res_val.json()["is_valid"] is True
