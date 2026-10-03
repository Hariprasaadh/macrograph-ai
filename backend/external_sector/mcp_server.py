"""External Sector FastMCP Server.

Exposes 9 tools discoverable via MCP registry:
  - get_forex_reserves: Official RBI weekly forex reserves stock, FCA, Gold, SDRs, RTP, and import cover
  - get_trade_balance: Monthly merchandise exports, imports, oil vs non-oil, and trade deficit
  - get_balance_of_payments: Current account balance, CAD % GDP, capital account, and net BoP
  - get_exchange_rate_snapshot: Official reference exchange rates, REER (40-currency basket), and NEER
  - get_live_market_rates: Real-time spot FX rates (USD/INR, EUR/INR, GBP/INR, JPY/INR) and Brent crude oil
  - get_remittances_and_invisibles: Private remittances, secondary transfers, and software/services surplus
  - get_external_debt: Quarterly external debt stock, short-term debt, and reserve coverage ratio
  - get_external_flows: Net Foreign Direct Investment (FDI) and Foreign Portfolio Investment (FPI) flows
  - get_realtime_external_intelligence: Real-time web intelligence and breaking news via Tavily search
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from external_sector import client, database as db
from external_sector.client import ExternalDataUnavailableError
from external_sector.models import (
    BoPResponse,
    DataFreshness,
    ExchangeRatesResponse,
    ExternalDebtResponse,
    ExternalFlowsResponse,
    ForexReservesResponse,
    IMFExternalOutlookResponse,
    LiveMarketRatesResponse,
    RealtimeIntelligenceResponse,
    RemittancesResponse,
    TradeBalanceResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="External Sector MCP Server",
    instructions=(
        "Provides official RBI & MoSPI external sector macroeconomic data for India: "
        "Foreign Exchange Reserves, Trade Balance, Balance of Payments, "
        "USD/INR & REER/NEER exchange rates, Remittances, External Debt, "
        "Foreign Investment Flows, Live Market Rates, and Real-Time Web Intelligence via Tavily."
    ),
    version="1.1.0",
)
mcp = mcp_server
server = mcp_server


@mcp_server.tool(
    name="get_forex_reserves",
    title="India Foreign Exchange Reserves Snapshot",
    description="Fetches total forex reserves (USD Mn / ₹ Cr), FCA, Gold, SDRs, RTP, and import cover from RBI DBIE.",
    tags={"external", "forex", "reserves", "rbi", "fca", "gold", "liquidity"},
)
async def get_forex_reserves(
    lookback_weeks: Annotated[int, Field(default=12, ge=1, le=52)] = 12,
) -> ForexReservesResponse | UnavailableResponse:
    """Fetch weekly foreign exchange reserves and import cover from RBI DBIE."""
    try:
        records = await client.fetch_forex_reserves(lookback_weeks)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ForexReservesResponse(status=freshness, records=records, total_records=len(records))
    except ExternalDataUnavailableError as exc:
        return UnavailableResponse(tool="get_forex_reserves", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_forex_reserves", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_trade_balance",
    title="Merchandise Trade Balance & Composition",
    description="Fetches exports, imports, oil vs non-oil composition, and trade deficit/surplus (USD Billion).",
    tags={"external", "trade", "exports", "imports", "deficit", "crude-oil"},
)
async def get_trade_balance(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> TradeBalanceResponse | UnavailableResponse:
    """Fetch merchandise trade balance and commodity trade data from RBI DBIE and MoSPI."""
    try:
        records = await client.fetch_trade_balance(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TradeBalanceResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_trade_balance", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_balance_of_payments",
    title="Balance of Payments (BoP)",
    description="Fetches Current Account Balance (% GDP), Capital Account Balance, and overall BoP financing.",
    tags={"external", "bop", "current-account", "cad", "rbi"},
)
async def get_balance_of_payments(
    lookback_quarters: Annotated[int, Field(default=8, ge=1, le=32)] = 8,
) -> BoPResponse | UnavailableResponse:
    """Fetch quarterly Balance of Payments, current account deficit, and capital account."""
    try:
        records = await client.fetch_balance_of_payments(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return BoPResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_balance_of_payments", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_exchange_rate_snapshot",
    title="USD/INR & Effective Exchange Rates (REER/NEER)",
    description="Fetches USD/INR reference exchange rate and REER/NEER trade-weighted indices from RBI.",
    tags={"external", "usd_inr", "exchange-rate", "reer", "neer", "competitiveness"},
)
async def get_exchange_rate_snapshot(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> ExchangeRatesResponse | UnavailableResponse:
    """Fetch spot USD/INR exchange rate series and 40-currency basket REER/NEER."""
    try:
        lookback_days = lookback_months * 30
        records = await client.fetch_exchange_rate_snapshot(lookback_days)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExchangeRatesResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_exchange_rate_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_live_market_rates",
    title="Real-Time Spot FX & Brent Crude Oil Benchmark",
    description="Fetches live spot USD/INR, EUR/INR, GBP/INR, JPY/INR, and Brent crude oil price from market feeds.",
    tags={"external", "live", "spot_fx", "brent_crude", "realtime"},
)
async def get_live_market_rates() -> LiveMarketRatesResponse | UnavailableResponse:
    """Fetch real-time spot FX rates and Brent crude oil benchmark via market feeds."""
    try:
        record = await client.fetch_live_market_rates()
        return LiveMarketRatesResponse(status=DataFreshness.LIVE, record=record)
    except Exception as exc:
        return UnavailableResponse(tool="get_live_market_rates", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_remittances_and_invisibles",
    title="Private Remittances & Services Invisibles",
    description="Fetches cross-border private remittance inflows, receipts, payments, and services surplus.",
    tags={"external", "remittances", "transfers", "invisibles", "services", "nri"},
)
async def get_remittances_and_invisibles(
    lookback_years: Annotated[int, Field(default=5, ge=1, le=20)] = 5,
) -> RemittancesResponse | UnavailableResponse:
    """Fetch private remittances and services invisibles from MoSPI eSankhyiki."""
    try:
        records = await client.fetch_remittances_and_invisibles(lookback_years)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return RemittancesResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_remittances_and_invisibles", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_external_debt",
    title="External Debt Stock & Reserve Coverage",
    description="Fetches external debt stock (USD Bn / ₹ Cr), General Government debt, short-term debt, and adequacy ratios.",
    tags={"external", "external_debt", "sovereign", "debt_ratio", "vulnerability"},
)
async def get_external_debt(
    lookback_quarters: Annotated[int, Field(default=8, ge=1, le=32)] = 8,
) -> ExternalDebtResponse | UnavailableResponse:
    """Fetch quarterly external debt stock and vulnerability indicators from MoSPI eSankhyiki."""
    try:
        records = await client.fetch_external_debt(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExternalDebtResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_external_debt", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_external_flows",
    title="Foreign Investment Flows (FDI & FPI)",
    description="Fetches net Foreign Direct Investment (FDI) and Foreign Portfolio Investment (FPI) flows from BoP.",
    tags={"external", "fdi", "fpi", "capital-flows", "investment"},
)
async def get_external_flows(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> ExternalFlowsResponse | UnavailableResponse:
    """Fetch cross-border FDI and FPI investment flows."""
    try:
        records = await client.fetch_external_flows(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExternalFlowsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_external_flows", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_realtime_external_intelligence",
    title="Real-Time External Macro Intelligence (Tavily)",
    description="Fetches live breaking news, commentary, and macroeconomic context for trade, rupee, and reserves via Tavily.",
    tags={"external", "news", "intelligence", "tavily", "realtime"},
)
async def get_realtime_external_intelligence(
    query: Annotated[str, Field(default="India foreign trade, forex reserves and rupee outlook")] = "India foreign trade, forex reserves and rupee outlook",
) -> RealtimeIntelligenceResponse | UnavailableResponse:
    """Fetch real-time web intelligence and news articles using Tavily."""
    try:
        record = await client.fetch_realtime_intelligence(query=query)
        return RealtimeIntelligenceResponse(status=DataFreshness.LIVE, record=record)
    except Exception as exc:
        return UnavailableResponse(tool="get_realtime_external_intelligence", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_imf_external_outlook",
    title="IMF World Economic Outlook (WEO) Projections",
    description="Fetches medium-term multilateral projections for India's CAD (% GDP), Current Account Balance, and export growth from IMF SDMX MCP.",
    tags={"external", "imf", "weo", "projections", "cad_gdp", "multilateral"},
)
async def get_imf_external_outlook(
    start_year: Annotated[str, Field(default="2022")] = "2022",
    end_year: Annotated[str, Field(default="2027")] = "2027",
) -> IMFExternalOutlookResponse | UnavailableResponse:
    """Fetch medium-term IMF WEO external outlook projections."""
    try:
        records = await client.fetch_imf_external_outlook(start_year, end_year)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IMFExternalOutlookResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_imf_external_outlook", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.resource("external://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "external_sector",
        "authority": "Reserve Bank of India (RBI) / MoSPI eSankhyiki / IMF SDMX",
        "indicators_owned": [
            "forex_reserves", "exports", "imports", "trade_balance",
            "bop", "usd_inr", "reer", "neer", "fdi", "fpi",
            "remittances", "external_debt", "live_spot_rates",
            "realtime_intelligence", "imf_weo_outlook"
        ],
    }, indent=2)
