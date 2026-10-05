"""Fiscal & Public Finance Sector FastMCP Server.

Exposes tools for:
  - Union Government fiscal deficit & budgetary accounts (CGA, Union Budget)
  - General Government Gross Debt & Net Lending/Borrowing (IMF WEO SDMX/MCP)
  - Goods and Services Tax (GST) monthly revenue collections
  - MoSPI National Accounts product taxes & subsidies (eSankhyiki FastMCP)
  - Indian tax calculators (GST split, GSTIN validation, Income Tax regime comparison via eco-policy-mcp)
  - Real-time fiscal news & official PIB releases (Tavily AI)

Strict Provenance: Every response includes mandatory Citation metadata satisfying No Source, No Answer.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from fiscal_sector import client
from fiscal_sector.cache_loaders import FiscalDataUnavailableError
from fiscal_sector.models import (
    DataFreshness,
    FiscalDeficitResponse,
    FiscalNewsResponse,
    GSTCollectionResponse,
    GSTINValidationResponse,
    GSTSplitResponse,
    IncomeTaxComparisonResponse,
    MoSPITaxAggregateResponse,
    SovereignDebtResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP Server Instance
# ---------------------------------------------------------------------------

mcp_server = FastMCP(
    name="Fiscal & Public Finance Sector MCP Server",
    instructions=(
        "Provides official fiscal and public finance data for India: "
        "Union Budget & CGA accounts, General Government Debt & Fiscal Balance (IMF WEO), "
        "GST monthly revenues, MoSPI National Accounts product taxes, and CBIC/CBDT tax calculators. "
        "All data carries mandatory citation metadata with source authority, document reference, and observation period. "
        "No Source, No Answer: unverified or estimated values without citations are strictly forbidden."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server


# ---------------------------------------------------------------------------
# Tool 1 — Union Fiscal Deficit & Budgetary Accounts
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_union_fiscal_deficit",
    title="Union Fiscal Deficit & Accounts at a Glance",
    description=(
        "Fetches Union Government accounts at a glance from Controller General of Accounts (CGA) and Union Budget. "
        "Returns Revenue Receipts, Tax Revenue (Net to Centre), Non-Tax Revenue, Capital Expenditure (Capex), "
        "Revenue Expenditure, and Fiscal Deficit (in ₹ Crore and as % of GDP)."
    ),
    tags={"fiscal", "deficit", "budget", "capex", "india", "cga"},
)
async def get_union_fiscal_deficit(
    lookback_records: Annotated[
        int,
        Field(default=5, ge=1, le=20, description="Number of annual/monthly budgetary accounts records to return."),
    ] = 5,
) -> FiscalDeficitResponse | UnavailableResponse:
    """Return Union Government fiscal deficit and budgetary accounts."""
    try:
        records = await client.fetch_union_fiscal_deficit(lookback_records)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return FiscalDeficitResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except FiscalDataUnavailableError as exc:
        logger.error("get_union_fiscal_deficit: %s", exc)
        return UnavailableResponse(
            tool="get_union_fiscal_deficit",
            reason=str(exc),
            suggestions=["Verify that sector DuckDB baseline data is initialized."],
        )
    except Exception as exc:
        logger.exception("get_union_fiscal_deficit: unexpected error")
        return UnavailableResponse(
            tool="get_union_fiscal_deficit",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 2 — General Government Debt & Net Lending/Borrowing (IMF WEO)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_general_government_debt",
    title="General Government Gross Debt & Fiscal Balance (IMF WEO)",
    description=(
        "Fetches General Government Gross Debt (% of GDP) and Net Lending/Borrowing (% of GDP) "
        "for India from the International Monetary Fund (IMF) World Economic Outlook (WEO) SDMX/MCP. "
        "Provides international-standard general government consolidated debt metrics."
    ),
    tags={"fiscal", "debt", "sovereign_debt", "imf", "weo", "india"},
)
async def get_general_government_debt(
    start_year: Annotated[
        int,
        Field(default=2018, ge=2000, le=2030, description="Starting calendar year for time series."),
    ] = 2018,
    end_year: Annotated[
        int,
        Field(default=2025, ge=2000, le=2030, description="Ending calendar year for time series."),
    ] = 2025,
) -> SovereignDebtResponse | UnavailableResponse:
    """Return General Government Gross Debt and Fiscal Balance from IMF WEO."""
    try:
        records = await client.fetch_sovereign_debt_imf(start_year, end_year)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SovereignDebtResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except Exception as exc:
        logger.exception("get_general_government_debt: unexpected error")
        return UnavailableResponse(
            tool="get_general_government_debt",
            reason=f"Failed to retrieve sovereign debt: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 3 — Monthly GST Revenue Collections
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_gst_collections",
    title="Monthly Gross GST Revenue Collections",
    description=(
        "Fetches monthly Gross Goods and Services Tax (GST) collections and sub-components "
        "(CGST, SGST, IGST, Compensation Cess) along with YoY growth rates. "
        "Source: Ministry of Finance / GST Council official press releases."
    ),
    tags={"fiscal", "gst", "tax_revenue", "india", "indirect_tax"},
)
async def get_gst_collections(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=36, description="Number of months of GST collections history to return."),
    ] = 12,
) -> GSTCollectionResponse | UnavailableResponse:
    """Return monthly GST revenue collections."""
    try:
        records = await client.fetch_gst_collections(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSTCollectionResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except Exception as exc:
        logger.exception("get_gst_collections: unexpected error")
        return UnavailableResponse(
            tool="get_gst_collections",
            reason=f"Failed to retrieve GST collections: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 4 — MoSPI National Accounts Product Taxes
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_mospi_product_taxes",
    title="MoSPI National Accounts Product Taxes & Subsidies",
    description=(
        "Fetches Net Taxes on Products from Ministry of Statistics and Programme Implementation (MoSPI) "
        "National Accounts Statistics (NAS) eSankhyiki FastMCP server. "
        "Reflects the tax bridge between Gross Value Added (GVA at basic prices) and GDP at market prices."
    ),
    tags={"fiscal", "mospi", "nas", "taxes_on_products", "subsidies", "gdp"},
)
async def get_mospi_product_taxes(
    lookback_years: Annotated[
        int,
        Field(default=5, ge=1, le=15, description="Number of annual National Accounts records to return."),
    ] = 5,
) -> MoSPITaxAggregateResponse | UnavailableResponse:
    """Return Net Taxes on Products from MoSPI NAS."""
    try:
        records = await client.fetch_mospi_product_taxes(lookback_years)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MoSPITaxAggregateResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except Exception as exc:
        logger.exception("get_mospi_product_taxes: unexpected error")
        return UnavailableResponse(
            tool="get_mospi_product_taxes",
            reason=f"Failed to retrieve MoSPI product taxes: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 5 — GST Calculation Breakdown (eco-policy-mcp)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="calculate_gst",
    title="GST Split Breakdown (CGST+SGST vs IGST)",
    description=(
        "Calculates exact GST split for a given base amount and rate slab (e.g. 5%, 12%, 18%, 28%). "
        "Determines CGST + SGST for intra-state transactions or IGST for inter-state transactions. "
        "Strictly computes via CBIC CGST Act rules with full mathematical provenance."
    ),
    tags={"fiscal", "gst_calculator", "cbic", "tax_split"},
)
def calculate_gst(
    amount: Annotated[float, Field(gt=0, description="Base amount before tax in ₹.")],
    rate_percent: Annotated[float, Field(ge=0, le=50, description="GST rate percentage (e.g. 5.0, 12.0, 18.0, 28.0).")],
    intra_state: Annotated[bool, Field(default=True, description="True for intra-state (CGST+SGST), False for inter-state (IGST).")] = True,
) -> GSTSplitResponse | UnavailableResponse:
    """Calculate GST breakup."""
    try:
        return client.calculate_gst_breakdown(amount, rate_percent, intra_state=intra_state)
    except Exception as exc:
        logger.exception("calculate_gst: calculation error")
        return UnavailableResponse(
            tool="calculate_gst",
            reason=f"GST calculation failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 6 — GSTIN Validation & State Decode (eco-policy-mcp)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="validate_gstin",
    title="GSTIN Validation & State Decode",
    description=(
        "Validates 15-character Goods and Services Tax Identification Number (GSTIN) "
        "format and mod-36 checksum, and decodes the issuing State / Union Territory."
    ),
    tags={"fiscal", "gstin", "validation", "gst_compliance"},
)
def validate_gstin(
    gstin: Annotated[str, Field(min_length=15, max_length=15, description="15-character GSTIN string.")],
) -> GSTINValidationResponse | UnavailableResponse:
    """Validate GSTIN and decode state code."""
    try:
        return client.validate_gstin_number(gstin)
    except Exception as exc:
        logger.exception("validate_gstin: validation error")
        return UnavailableResponse(
            tool="validate_gstin",
            reason=f"GSTIN validation failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 7 — Income Tax Regime Comparison (eco-policy-mcp)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="compare_tax_regimes",
    title="Income Tax Regime Comparison (New vs Old)",
    description=(
        "Evaluates tax liability under the New vs Old tax regimes for a given gross salary. "
        "Applies FY 2025-26 & FY 2026-27 Finance Act slabs, standard deductions (₹75k vs ₹50k), "
        "Section 87A rebate, cess, and outputs the optimal regime and switch savings."
    ),
    tags={"fiscal", "income_tax", "cbdt", "tax_regime", "finance_act"},
)
def compare_tax_regimes(
    gross_salary: Annotated[float, Field(gt=0, description="Annual gross salary in ₹.")],
    deductions_80c: Annotated[float, Field(default=150000.0, ge=0, le=150000.0, description="Section 80C deductions (max 1.5 Lakh).")] = 150000.0,
    other_deductions: Annotated[float, Field(default=0.0, ge=0, description="Other Chapter VI-A deductions (80D, etc.) in ₹.")] = 0.0,
    age: Annotated[int, Field(default=35, ge=18, le=100, description="Taxpayer age in years.")] = 35,
) -> IncomeTaxComparisonResponse | UnavailableResponse:
    """Compare New vs Old Tax Regimes."""
    try:
        return client.compare_income_tax_regimes(
            gross_salary=gross_salary,
            deductions_80c=deductions_80c,
            other_deductions=other_deductions,
            age=age,
        )
    except Exception as exc:
        logger.exception("compare_tax_regimes: error")
        return UnavailableResponse(
            tool="compare_tax_regimes",
            reason=f"Tax regime comparison failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 8 — Real-time Fiscal News & PIB Press Releases (Tavily AI)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_fiscal_news",
    title="Real-time Ministry of Finance & PIB Fiscal News",
    description=(
        "Retrieves recent official press releases and news regarding Ministry of Finance, "
        "CGA monthly deficit releases, GST collections, Capex spending, and Budget announcements."
    ),
    tags={"fiscal", "news", "pib", "ministry_of_finance", "realtime"},
)
async def get_fiscal_news(
    query: Annotated[
        str,
        Field(default="site:pib.gov.in Ministry of Finance monthly gross GST revenue collection fiscal deficit", description="Search query for official fiscal releases."),
    ] = "site:pib.gov.in Ministry of Finance monthly gross GST revenue collection fiscal deficit",
    max_results: Annotated[
        int,
        Field(default=5, ge=1, le=10, description="Maximum number of search results to return."),
    ] = 5,
) -> FiscalNewsResponse | UnavailableResponse:
    """Fetch real-time fiscal news and announcements."""
    try:
        return await client.fetch_realtime_fiscal_news(query, max_results)
    except Exception as exc:
        logger.exception("get_fiscal_news: error")
        return UnavailableResponse(
            tool="get_fiscal_news",
            reason=f"Failed to retrieve fiscal news: {exc}",
            error_detail=repr(exc),
        )
