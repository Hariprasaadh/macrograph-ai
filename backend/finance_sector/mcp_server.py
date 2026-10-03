"""Finance & Banking Sector FastMCP Server.

Exposes official RBI DBIE, yfinance market data, and Tavily real-time news tools.
Strict Provenance: every response includes Citation metadata.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from finance_sector import database as db
from finance_sector import client
from finance_sector.client import FinanceDataUnavailableError
from finance_sector.market_client import (
    fetch_banking_market_indicators,
    fetch_realtime_finance_news,
)
from finance_sector.models import (
    AssetQualityResponse,
    BankCreditGrowthResponse,
    BankGroup,
    BankingMarketResponse,
    DataFreshness,
    DepositsAndCDResponse,
    FinanceNewsResponse,
    LendingRatesResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP Server — metadata used by MCP registries and discovery layers
# ---------------------------------------------------------------------------

mcp_server = FastMCP(
    name="Finance & Banking Sector MCP Server",
    instructions=(
        "Provides official RBI macroeconomic data for India's Scheduled Commercial Banks. "
        "All values carry mandatory citation metadata (source, table, period, URL). "
        "No Source, No Answer: values without citations are a protocol violation. "
        "Data is fetched live from RBI DBIE, yfinance, and Tavily; on failure, the most "
        "recent cached data from the sector's dedicated DuckDB store is returned with freshness=CACHED."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server


# ---------------------------------------------------------------------------
# Tool 1 — Bank Credit Growth & Sectoral Deployment
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_bank_credit_growth",
    title="Bank Credit Growth & Sectoral Deployment",
    description=(
        "Fetches non-food gross bank credit outstanding and its sectoral deployment "
        "(Agriculture, Industry, MSME, Services, Retail/Personal Loans) from RBI DBIE. "
        "Source: RBI Scheduled Commercial Banks — Sectoral Deployment of Non-Food Gross Bank Credit. "
        "Live fetch from https://dbie.rbihub.in/data/bank-credit-by-sector.json with DuckDB fallback."
    ),
    tags={"finance", "credit", "banking", "india", "rbi"},
)
async def get_bank_credit_growth(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=60, description="Number of months of history to return."),
    ] = 12,
) -> BankCreditGrowthResponse | UnavailableResponse:
    """Return non-food gross credit and sectoral deployment for the past N months.

    Every record includes a Citation with source authority, DBIE table reference,
    observation period, and retrieval URL.
    """
    try:
        records = await client.fetch_bank_credit_growth(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return BankCreditGrowthResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except FinanceDataUnavailableError as exc:
        logger.error("get_bank_credit_growth: %s", exc)
        return UnavailableResponse(
            tool="get_bank_credit_growth",
            reason=str(exc),
        )
    except Exception as exc:
        logger.exception("get_bank_credit_growth: unexpected error")
        return UnavailableResponse(
            tool="get_bank_credit_growth",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 2 — Asset Quality & Capital Adequacy
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_asset_quality",
    title="Asset Quality & Capital Adequacy (NPA & CRAR)",
    description=(
        "Fetches Gross NPA (%), Net NPA (%), and Capital to Risk-Weighted Assets Ratio (CRAR %) "
        "for Scheduled Commercial Banks, broken down by bank group (PSBs, Private, Foreign, SFBs). "
        "Sources: RBI DBIE financial_sector.r330 (NPA) and financial_sector.r329 (CRAR). "
        "Live fetch from https://data-api.dbie.rbihub.in with DuckDB fallback."
    ),
    tags={"finance", "npa", "crar", "asset-quality", "banking", "india", "rbi"},
)
async def get_asset_quality(
    bank_group: Annotated[
        BankGroup,
        Field(
            default=BankGroup.ALL_SCB,
            description=(
                "Filter by bank group: ALL_SCB, PUBLIC_SECTOR, PRIVATE_SECTOR, "
                "FOREIGN_BANKS, or SMALL_FINANCE."
            ),
        ),
    ] = BankGroup.ALL_SCB,
    lookback_quarters: Annotated[
        int,
        Field(default=8, ge=1, le=32, description="Number of quarters of history to return."),
    ] = 8,
) -> AssetQualityResponse | UnavailableResponse:
    """Return NPA ratios and CRAR for the selected bank group and horizon.

    Note: This tool owns bank balance sheet solvency.
    The Policy Repo Rate is NOT fetched here — it is received from monetary_sector via A2A.
    """
    try:
        records = await client.fetch_asset_quality(bank_group, lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return AssetQualityResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except FinanceDataUnavailableError as exc:
        logger.error("get_asset_quality: %s", exc)
        return UnavailableResponse(
            tool="get_asset_quality",
            reason=str(exc),
        )
    except Exception as exc:
        logger.exception("get_asset_quality: unexpected error")
        return UnavailableResponse(
            tool="get_asset_quality",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 3 — Lending Rates & Policy Transmission
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_lending_and_deposit_rates",
    title="Lending Rates & Policy Transmission (WALR, MCLR, WADTDR)",
    description=(
        "Fetches commercial bank lending and deposit rates: "
        "Weighted Average Lending Rate (WALR fresh & outstanding), "
        "1-Year Median MCLR, and Weighted Average Domestic Term Deposit Rate (WADTDR). "
        "Computes lending spread over the RBI Policy Repo Rate when repo is provided via A2A. "
        "Source: RBI DBIE financial_sector.r531_key_rates. "
        "NOTE: This sector does NOT own the Policy Repo Rate — that belongs to monetary_sector."
    ),
    tags={"finance", "walr", "mclr", "wadtdr", "lending-rates", "banking", "india", "rbi"},
)
async def get_lending_and_deposit_rates(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=60, description="Number of months of history to return."),
    ] = 12,
    repo_rate_from_a2a: Annotated[
        float | None,
        Field(
            default=None,
            description=(
                "Policy Repo Rate (%) received from monetary_sector via A2A. "
                "When provided, lending spread over repo is computed automatically. "
                "Finance sector never fetches this independently."
            ),
        ),
    ] = None,
) -> LendingRatesResponse | UnavailableResponse:
    """Return WALR, MCLR, and WADTDR for the past N months.

    Pass repo_rate_from_a2a (from monetary_sector via A2A) to compute the
    transmission spread automatically.
    """
    try:
        records = await client.fetch_lending_rates(lookback_months)

        # Inject repo rate received via A2A and compute spread
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
            records=records,
            total_records=len(records),
        )
    except FinanceDataUnavailableError as exc:
        logger.error("get_lending_and_deposit_rates: %s", exc)
        return UnavailableResponse(
            tool="get_lending_and_deposit_rates",
            reason=str(exc),
        )
    except Exception as exc:
        logger.exception("get_lending_and_deposit_rates: unexpected error")
        return UnavailableResponse(
            tool="get_lending_and_deposit_rates",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 4 — Deposit Mobilisation & CD Ratio
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_deposits_and_cd_ratio",
    title="Deposit Mobilisation & Credit-to-Deposit Ratio",
    description=(
        "Fetches aggregate commercial bank deposits (₹ Crore, % YoY growth), "
        "CASA (Current + Savings Account) ratio, and Credit-to-Deposit (CD) ratio. "
        "Sources: RBI DBIE commercial-bank-survey.json and business-of-scheduled-banks.json. "
        "High values of CD ratio signal intermediation stress. "
        "Live fetch from RBI DBIE CDN with DuckDB fallback."
    ),
    tags={"finance", "deposits", "cd-ratio", "casa", "banking", "india", "rbi"},
)
async def get_deposits_and_cd_ratio(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=60, description="Number of months of history to return."),
    ] = 12,
) -> DepositsAndCDResponse | UnavailableResponse:
    """Return deposit growth, CASA ratio, and CD ratio for the past N months."""
    try:
        records = await client.fetch_deposits_and_cd_ratio(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return DepositsAndCDResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except FinanceDataUnavailableError as exc:
        logger.error("get_deposits_and_cd_ratio: %s", exc)
        return UnavailableResponse(
            tool="get_deposits_and_cd_ratio",
            reason=str(exc),
        )
    except Exception as exc:
        logger.exception("get_deposits_and_cd_ratio: unexpected error")
        return UnavailableResponse(
            tool="get_deposits_and_cd_ratio",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 5 — Banking Market Equities & Indices (yfinance)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_banking_market_indicators",
    title="Banking Market Equities & Nifty Bank Index",
    description=(
        "Fetches live market valuation, current price, day return, P/E, P/B, and 52-week "
        "range for the Nifty Bank index (^NSEBANK) and major Indian commercial banks "
        "(SBI, HDFC Bank, ICICI Bank, Kotak Mahindra, Axis Bank) via Yahoo Finance."
    ),
    tags={"finance", "market", "equities", "nifty-bank", "valuation", "yfinance"},
)
async def get_banking_market_indicators() -> BankingMarketResponse | UnavailableResponse:
    """Return live quotes and valuation metrics for banking sector equities."""
    try:
        return await fetch_banking_market_indicators()
    except Exception as exc:
        logger.exception("get_banking_market_indicators: unexpected error")
        return UnavailableResponse(
            tool="get_banking_market_indicators",
            reason=f"Market data fetch failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 6 — Real-Time Financial News & Intelligence (Tavily)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_realtime_finance_news",
    title="Real-Time Banking & Regulatory Intelligence",
    description=(
        "Enriches banking intelligence with real-time news, RBI regulatory notifications, "
        "and MPC policy commentary using Tavily AI Search (TVLY_KEY_1)."
    ),
    tags={"finance", "news", "regulatory", "rbi", "realtime", "tavily"},
)
async def get_realtime_finance_news(
    query: Annotated[
        str,
        Field(default="RBI monetary policy commercial bank credit growth India", description="Financial search query."),
    ] = "RBI monetary policy commercial bank credit growth India",
    max_results: Annotated[
        int,
        Field(default=5, ge=1, le=10, description="Maximum news articles to retrieve."),
    ] = 5,
) -> FinanceNewsResponse | UnavailableResponse:
    """Return real-time banking news and regulatory updates for a topic."""
    try:
        return await fetch_realtime_finance_news(query=query, max_results=max_results)
    except Exception as exc:
        logger.exception("get_realtime_finance_news: unexpected error")
        return UnavailableResponse(
            tool="get_realtime_finance_news",
            reason=f"News search failed: {exc}",
            error_detail=repr(exc),
        )



# ---------------------------------------------------------------------------
# Resources — Read-only reference catalogs (FastMCP Resource)
# ---------------------------------------------------------------------------

@mcp.resource("finance://catalog")
def get_catalog() -> str:
    """Read-only catalog of official RBI DBIE table references and indicator mappings."""
    import json
    return json.dumps(
        {
            "sector": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "tables": {
                "bank_credit": "financial_sector.r1130_food_non_food_credit_of_scheduled_commercial_banks",
                "sectoral_deployment": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                "asset_quality": "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou",
                "capital_adequacy": "financial_sector.r329_distribution_of_scheduled_commercial_banks_by_crar",
                "lending_rates": "financial_sector.r531_key_rates",
                "deposits_and_business": "financial_sector.r689_business_of_scheduled_banks",
            },
            "citation_policy": "Strict provenance citation required for all observations.",
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompts — Reusable analysis prompt templates (FastMCP Prompt)
# ---------------------------------------------------------------------------

@mcp.prompt()
def analyze_banking_system(focus_area: str = "credit_and_asset_quality") -> str:
    """Prompt template for analyzing the health and stability of India's banking sector."""
    return (
        f"Perform a comprehensive macroeconomic review of India's Scheduled Commercial Banks "
        f"focusing on {focus_area}. "
        f"Fetch latest credit growth, Gross/Net NPA ratios, CRAR capital adequacy, "
        f"lending rates (WALR/MCLR), and CD ratio. "
        f"Strictly enforce the 'No Source, No Answer' policy with official RBI DBIE citations."
    )

