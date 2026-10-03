"""Capital Markets Sector FastMCP Server.

Exposes 5 tools:
  - get_nifty_snapshot
  - get_market_history
  - get_india_vix
  - get_market_breadth
  - get_gsec_yield_snapshot
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from capital_market_sector import client, database as db
from capital_market_sector.client import CapitalMarketDataUnavailableError
from capital_market_sector.models import (
    DataFreshness,
    GSecYieldResponse,
    IndiaVixResponse,
    MarketBreadthResponse,
    MarketHistoryResponse,
    NiftySnapshotResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="Capital Markets Sector MCP Server",
    instructions=(
        "Provides official NSE and RBI capital market data for India: "
        "NIFTY 50 index levels, India VIX volatility, market breadth, "
        "historical equity index returns, and RBI monthly SGL transaction yields "
        "at labeled Government Security maturities."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


@mcp_server.tool(
    name="get_nifty_snapshot",
    title="NIFTY 50 & Equity Index Snapshot",
    description="Fetches latest open, high, low, close, volume, and turnover for NIFTY 50 index.",
    tags={"capital_markets", "nifty", "nse", "equity", "index"},
)
async def get_nifty_snapshot() -> NiftySnapshotResponse | UnavailableResponse:
    try:
        records = await client.fetch_nifty_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return NiftySnapshotResponse(status=freshness, records=records, total_records=len(records))
    except CapitalMarketDataUnavailableError as exc:
        return UnavailableResponse(tool="get_nifty_snapshot", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_nifty_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_market_history",
    title="Historical Equity Index Returns & Valuations",
    description="Fetches historical equity index performance, P/E ratio, P/B ratio, and dividend yield.",
    tags={"capital_markets", "nifty", "history", "valuations", "pe_ratio"},
)
async def get_market_history(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> MarketHistoryResponse | UnavailableResponse:
    try:
        records = await client.fetch_market_history(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketHistoryResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_market_history", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_india_vix",
    title="India Volatility Index (India VIX)",
    description="Fetches India VIX volatility index level and volatility regime classification.",
    tags={"capital_markets", "vix", "volatility", "nse", "risk"},
)
async def get_india_vix(
    lookback_days: Annotated[int, Field(default=30, ge=1, le=180)] = 30,
) -> IndiaVixResponse | UnavailableResponse:
    try:
        records = await client.fetch_india_vix(lookback_days)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IndiaVixResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_india_vix", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_market_breadth",
    title="NSE Equity Market Breadth",
    description="Fetches advances, declines, unchanged stock counts, and Advance/Decline ratio.",
    tags={"capital_markets", "breadth", "advances_declines", "nse"},
)
async def get_market_breadth() -> MarketBreadthResponse | UnavailableResponse:
    try:
        records = await client.fetch_market_breadth()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketBreadthResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_market_breadth", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_gsec_yield_snapshot",
    title="Government Securities (G-Sec) Yield Curve",
    description=(
        "Fetches monthly RBI SGL transaction yields at explicitly labeled 10Y, "
        "5Y, and 2Y G-Sec maturities, with the 2s10s difference in basis points."
    ),
    tags={"capital_markets", "gsec", "yields", "bonds", "rbi", "yield_curve"},
)
async def get_gsec_yield_snapshot() -> GSecYieldResponse | UnavailableResponse:
    try:
        records = await client.fetch_gsec_yield_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSecYieldResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_gsec_yield_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp.resource("capitalmarkets://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "capital_market_sector",
        "authority": "National Stock Exchange of India (NSE) / RBI",
        "indicators_owned": ["nifty_50", "india_vix", "market_breadth", "gsec_10y_yield", "gsec_yield_curve"],
    }, indent=2)
