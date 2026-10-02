"""Finance Sector FastAPI sub-application.

Mounted by backend/main.py at /finance-sector.
Provides HTTP access to MCP tool results and sector metadata.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from finance_sector import client
from finance_sector.client import FinanceDataUnavailableError
from finance_sector.models import (
    AssetQualityResponse,
    BankCreditGrowthResponse,
    BankGroup,
    DataFreshness,
    DepositsAndCDResponse,
    LendingRatesResponse,
)

app = FastAPI(
    title="Finance & Banking Sector API",
    description=(
        "HTTP endpoints for the Finance & Banking Sector Agent. "
        "All responses include mandatory citation metadata. "
        "No hardcoded or estimated values."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Health check for the finance sector sub-application."""
    return {"status": "healthy", "sector": "finance_sector", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Sector metadata — MCP registry discovery endpoint
# ---------------------------------------------------------------------------

@app.get("/metadata", tags=["Registry"])
async def sector_metadata() -> dict[str, Any]:
    """Returns sector capability metadata for MCP registry discovery.

    AI agents and developer registries can call this endpoint to understand
    what indicators this sector owns, what tools it exposes, and which
    peer sectors it collaborates with via A2A.
    """
    return {
        "sector": "finance_sector",
        "version": "1.0.0",
        "domain": "India — Scheduled Commercial Banks",
        "authority": "Reserve Bank of India (RBI)",
        "data_source": "RBI DBIE (https://dev.dbie.rbihub.in)",
        "citation_policy": "No Source, No Answer — every value carries mandatory citation metadata.",
        "tools": [
            {
                "name": "get_bank_credit_growth",
                "description": "Non-food gross bank credit and sectoral deployment (Agri, Industry, MSME, Services, Retail).",
                "frequency": "Monthly / Fortnightly",
                "table": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
            },
            {
                "name": "get_asset_quality",
                "description": "Gross NPA %, Net NPA %, CRAR % by bank group (PSBs, Private, Foreign, SFBs).",
                "frequency": "Annual / Half-yearly (FSR)",
                "table": "financial_sector.r330_gross_and_net_npas / r329_crar",
            },
            {
                "name": "get_lending_and_deposit_rates",
                "description": "WALR (fresh & outstanding), 1-yr MCLR, WADTDR, lending spread over Repo.",
                "frequency": "Monthly",
                "table": "financial_sector.r531_key_rates",
            },
            {
                "name": "get_deposits_and_cd_ratio",
                "description": "Aggregate deposits (% YoY), CASA ratio, Credit-to-Deposit ratio.",
                "frequency": "Fortnightly",
                "table": "financial_sector.r689_business_of_scheduled_banks",
            },
        ],
        "owns": [
            "non_food_bank_credit_yoy",
            "sectoral_credit_agriculture",
            "sectoral_credit_industry_msme",
            "sectoral_credit_services",
            "sectoral_credit_retail",
            "gross_npa_pct",
            "net_npa_pct",
            "crar_pct",
            "walr_fresh",
            "walr_outstanding",
            "mclr_1yr_median",
            "wadtdr_fresh",
            "aggregate_deposits_yoy",
            "casa_ratio",
            "cd_ratio",
        ],
        "does_not_own": [
            "policy_repo_rate (monetary_sector)",
            "m1_m3_money_supply (monetary_sector)",
            "bank_nifty_index (capital_market_sector)",
            "g_sec_primary_issuances (fiscal_sector)",
            "forex_reserves (external_sector)",
        ],
        "a2a_inbound": [
            "repo_rate from monetary_sector",
            "headline_cpi from prices_sector",
            "gdp_gva from real_sector",
        ],
        "a2a_outbound": [
            "walr_responsiveness to monetary_sector",
            "gnpa_pcr to capital_market_sector",
            "credit_to_industry to real_sector",
        ],
    }


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

@app.get("/credit-growth", response_model=BankCreditGrowthResponse, tags=["Finance"])
async def credit_growth(
    lookback_months: int = Query(default=12, ge=1, le=60),
) -> BankCreditGrowthResponse:
    """Non-food gross bank credit and sectoral deployment."""
    try:
        records = await client.fetch_bank_credit_growth(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return BankCreditGrowthResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except FinanceDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/asset-quality", response_model=AssetQualityResponse, tags=["Finance"])
async def asset_quality(
    bank_group: BankGroup = Query(default=BankGroup.ALL_SCB),
    lookback_quarters: int = Query(default=8, ge=1, le=32),
) -> AssetQualityResponse:
    """Gross NPA, Net NPA, and CRAR by bank group."""
    try:
        records = await client.fetch_asset_quality(bank_group, lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return AssetQualityResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except FinanceDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/lending-rates", response_model=LendingRatesResponse, tags=["Finance"])
async def lending_rates(
    lookback_months: int = Query(default=12, ge=1, le=60),
    repo_rate_from_a2a: float | None = Query(
        default=None,
        description="Repo rate (%) from monetary_sector via A2A — used to compute lending spread.",
    ),
) -> LendingRatesResponse:
    """WALR, MCLR, WADTDR, and lending spread over repo."""
    try:
        records = await client.fetch_lending_rates(lookback_months)
        if repo_rate_from_a2a is not None:
            for r in records:
                if r.repo_rate_pct is None:
                    r.repo_rate_pct = repo_rate_from_a2a
                    if r.walr_fresh_pct is not None:
                        r.lending_spread_over_repo_pct = round(
                            r.walr_fresh_pct - repo_rate_from_a2a, 4
                        )
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return LendingRatesResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except FinanceDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/deposits-cd-ratio", response_model=DepositsAndCDResponse, tags=["Finance"])
async def deposits_cd_ratio(
    lookback_months: int = Query(default=12, ge=1, le=60),
) -> DepositsAndCDResponse:
    """Aggregate deposits, CASA ratio, and Credit-to-Deposit ratio."""
    try:
        records = await client.fetch_deposits_and_cd_ratio(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return DepositsAndCDResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except FinanceDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
