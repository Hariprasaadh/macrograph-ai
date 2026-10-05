"""Fiscal Sector FastAPI sub-application.

Mounted by backend/main.py at /fiscal-sector.
Provides HTTP access to FastMCP tool results, tax calculators, and sector metadata.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

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
)

app = FastAPI(
    title="Fiscal & Public Finance Sector API",
    description=(
        "HTTP endpoints for the Fiscal & Public Finance Sector Agent. "
        "Covers Union Budget deficit, Capex spending, IMF WEO General Government Debt, "
        "GST monthly collections, MoSPI product taxes, and CBIC/CBDT tax calculators. "
        "All responses include mandatory citation metadata."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Health check for the fiscal sector sub-application."""
    return {"status": "healthy", "sector": "fiscal_sector", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Metadata Discovery
# ---------------------------------------------------------------------------

@app.get("/metadata", tags=["Registry"])
async def sector_metadata() -> dict[str, Any]:
    """Returns sector capability metadata for MCP registry discovery."""
    return {
        "sector": "fiscal_sector",
        "version": "1.0.0",
        "domain": "India — Fiscal & Public Finance",
        "authorities": [
            "Ministry of Finance, Government of India (CGA / Budget Division)",
            "International Monetary Fund (IMF) World Economic Outlook (WEO)",
            "Ministry of Statistics and Programme Implementation (MoSPI)",
            "Goods and Services Tax Council / CBIC",
            "Central Board of Direct Taxes (CBDT)",
        ],
        "data_sources": [
            "Controller General of Accounts (CGA) Accounts at a Glance",
            "IMF SDMX 3.0 WEO Dataflow (IND.GGXWDG_NGDP.A, IND.GGXCNL_NGDP.A)",
            "MoSPI eSankhyiki FastMCP Server (NAS Product Taxes)",
            "CBIC / GST Council Monthly Press Releases",
            "eco-policy-mcp Tax Computation Engine",
        ],
        "citation_policy": "No Source, No Answer — every value carries mandatory citation metadata.",
        "tools": [
            {
                "name": "get_union_fiscal_deficit",
                "description": "Union Government accounts: Revenue receipts, Capex, and Fiscal Deficit (% of GDP and ₹ Crore).",
                "authority": "CGA / Ministry of Finance",
            },
            {
                "name": "get_general_government_debt",
                "description": "General Government Gross Debt and Net Lending/Borrowing (% of GDP) under IMF WEO standards.",
                "authority": "International Monetary Fund (IMF)",
            },
            {
                "name": "get_gst_collections",
                "description": "Monthly gross GST revenue collections and components (CGST, SGST, IGST, Cess).",
                "authority": "Ministry of Finance / GST Council",
            },
            {
                "name": "get_mospi_product_taxes",
                "description": "Net Taxes on Products from National Accounts Statistics.",
                "authority": "MoSPI eSankhyiki",
            },
            {
                "name": "calculate_gst",
                "description": "Calculates exact CGST+SGST vs IGST split for invoice amounts.",
                "authority": "CBIC / CGST Act, 2017",
            },
            {
                "name": "validate_gstin",
                "description": "Validates 15-digit GSTIN and decodes issuing state.",
                "authority": "GST Council",
            },
            {
                "name": "compare_tax_regimes",
                "description": "Compares New vs Old Income Tax regimes under FY 2025-26 & FY 2026-27 rules.",
                "authority": "Income Tax Department / Finance Act",
            },
            {
                "name": "get_fiscal_news",
                "description": "Real-time Ministry of Finance PIB press releases via Tavily AI.",
                "authority": "Press Information Bureau (PIB)",
            },
        ],
        "owns": [
            "fiscal_deficit_cr",
            "fiscal_deficit_gdp_pct",
            "capital_expenditure_capex",
            "general_govt_gross_debt_gdp",
            "net_lending_borrowing_gdp",
            "gst_gross_revenue_cr",
            "cgst_sgst_igst_breakdown",
            "mospi_net_product_taxes",
        ],
        "collaborates_via_a2a_with": [
            {"sector": "monetary_sector", "inbound": "Repo rate & liquidity stance", "outbound": "Fiscal deficit & borrowing program"},
            {"sector": "real_sector", "inbound": "GDP & GVA growth", "outbound": "Capex impulse & tax buoyancy"},
            {"sector": "prices_sector", "inbound": "CPI & WPI inflation", "outbound": "Indirect tax & fuel cess trends"},
            {"sector": "finance_sector", "inbound": "Bank credit to infrastructure", "outbound": "Government market borrowing absorption"},
        ],
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/deficit", response_model=FiscalDeficitResponse, tags=["Pillar 1: Union Accounts"])
async def get_deficit(
    lookback_records: int = Query(default=5, ge=1, le=20, description="Number of budgetary records to return"),
) -> FiscalDeficitResponse:
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
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/debt", response_model=SovereignDebtResponse, tags=["Pillar 2: Sovereign Debt"])
async def get_debt(
    start_year: int = Query(default=2018, ge=2000, le=2030),
    end_year: int = Query(default=2025, ge=2000, le=2030),
) -> SovereignDebtResponse:
    """Return General Government Gross Debt (% of GDP) from IMF WEO."""
    try:
        records = await client.fetch_sovereign_debt_imf(start_year, end_year)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SovereignDebtResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch IMF sovereign debt: {exc}")


@app.get("/gst", response_model=GSTCollectionResponse, tags=["Pillar 3: GST Collections"])
async def get_gst(
    lookback_months: int = Query(default=12, ge=1, le=36),
) -> GSTCollectionResponse:
    """Return monthly gross GST revenue collections."""
    try:
        records = await client.fetch_gst_collections(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSTCollectionResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except FiscalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/taxes", response_model=MoSPITaxAggregateResponse, tags=["Pillar 4: MoSPI Product Taxes"])
async def get_taxes(
    lookback_years: int = Query(default=5, ge=1, le=15),
) -> MoSPITaxAggregateResponse:
    """Return MoSPI National Accounts Net Taxes on Products."""
    try:
        records = await client.fetch_mospi_product_taxes(lookback_years)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MoSPITaxAggregateResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch MoSPI product taxes: {exc}")


@app.get("/calculate-gst", response_model=GSTSplitResponse, tags=["Pillar 5: Tax Calculators"])
def calc_gst(
    amount: float = Query(gt=0, description="Base amount before tax in ₹"),
    rate_percent: float = Query(ge=0, le=50, description="GST rate percentage"),
    intra_state: bool = Query(default=True, description="True for intra-state (CGST+SGST), False for inter-state (IGST)"),
) -> GSTSplitResponse:
    """Calculate GST breakup."""
    try:
        return client.calculate_gst_breakdown(amount, rate_percent, intra_state=intra_state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/validate-gstin", response_model=GSTINValidationResponse, tags=["Pillar 5: Tax Calculators"])
def check_gstin(
    gstin: str = Query(min_length=15, max_length=15, description="15-character GSTIN string"),
) -> GSTINValidationResponse:
    """Validate GSTIN and decode issuing state."""
    try:
        return client.validate_gstin_number(gstin)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/compare-tax", response_model=IncomeTaxComparisonResponse, tags=["Pillar 5: Tax Calculators"])
def tax_comparison(
    gross_salary: float = Query(gt=0, description="Annual gross salary in ₹"),
    deductions_80c: float = Query(default=150000.0, ge=0, le=150000.0),
    other_deductions: float = Query(default=0.0, ge=0),
    age: int = Query(default=35, ge=18, le=100),
) -> IncomeTaxComparisonResponse:
    """Compare New vs Old Tax Regimes under the Finance Act."""
    try:
        return client.compare_income_tax_regimes(
            gross_salary=gross_salary,
            deductions_80c=deductions_80c,
            other_deductions=other_deductions,
            age=age,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/news", response_model=FiscalNewsResponse, tags=["Pillar 6: Fiscal News"])
async def get_news(
    query: str = Query(default="site:pib.gov.in Ministry of Finance fiscal deficit GST capex"),
    max_results: int = Query(default=5, ge=1, le=10),
) -> FiscalNewsResponse:
    """Return real-time fiscal news and announcements via Tavily."""
    return await client.fetch_realtime_fiscal_news(query, max_results)
