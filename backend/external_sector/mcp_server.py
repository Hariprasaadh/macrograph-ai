"""External Sector FastMCP Server.

Exposes 5 tools discoverable via MCP registry:
  - get_forex_reserves
  - get_trade_balance
  - get_balance_of_payments
  - get_exchange_rate_snapshot
  - get_external_flows
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
    ExternalFlowsResponse,
    ForexReservesResponse,
    TradeBalanceResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="External Sector MCP Server",
    instructions=(
        "Provides official RBI external sector macroeconomic data for India: "
        "Foreign Exchange Reserves, Trade Balance, Balance of Payments, "
        "USD/INR & REER exchange rates, and Foreign Investment Flows."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


@mcp_server.tool(
    name="get_forex_reserves",
    title="India Foreign Exchange Reserves Snapshot",
    description="Fetches total forex reserves (USD Mn / ₹ Cr), FCA, Gold, SDRs, and RTP from RBI DBIE.",
    tags={"external", "forex", "reserves", "rbi", "fca", "gold"},
)
async def get_forex_reserves(
    lookback_weeks: Annotated[int, Field(default=12, ge=1, le=52)] = 12,
) -> ForexReservesResponse | UnavailableResponse:
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
    title="Merchandise Trade Balance",
    description="Fetches exports, imports, and trade deficit/surplus (USD Billion).",
    tags={"external", "trade", "exports", "imports", "deficit"},
)
async def get_trade_balance(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> TradeBalanceResponse | UnavailableResponse:
    try:
        records = await client.fetch_trade_balance(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TradeBalanceResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_trade_balance", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_balance_of_payments",
    title="Balance of Payments (BoP)",
    description="Fetches Current Account Balance (% GDP) and Capital Account Balance.",
    tags={"external", "bop", "current-account", "rbi"},
)
async def get_balance_of_payments(
    lookback_quarters: Annotated[int, Field(default=8, ge=1, le=32)] = 8,
) -> BoPResponse | UnavailableResponse:
    try:
        records = await client.fetch_balance_of_payments(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return BoPResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_balance_of_payments", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_exchange_rate_snapshot",
    title="USD/INR & Effective Exchange Rates (REER/NEER)",
    description="Fetches USD/INR reference exchange rate and REER/NEER indices.",
    tags={"external", "usd_inr", "exchange-rate", "reer", "neer"},
)
async def get_exchange_rate_snapshot(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> ExchangeRatesResponse | UnavailableResponse:
    try:
        records = await client.fetch_exchange_rate_snapshot(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExchangeRatesResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_exchange_rate_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_external_flows",
    title="Foreign Investment Flows (FDI & FPI)",
    description="Fetches net Foreign Direct Investment (FDI) and Foreign Portfolio Investment (FPI) flows.",
    tags={"external", "fdi", "fpi", "capital-flows"},
)
async def get_external_flows(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> ExternalFlowsResponse | UnavailableResponse:
    try:
        records = await client.fetch_external_flows(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExternalFlowsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_external_flows", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp.resource("external://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "external_sector",
        "authority": "Reserve Bank of India (RBI) / Ministry of Commerce",
        "indicators_owned": ["forex_reserves", "exports", "imports", "trade_balance", "bop", "usd_inr", "reer", "neer", "fdi", "fpi"],
    }, indent=2)
