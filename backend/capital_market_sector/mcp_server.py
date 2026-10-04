"""Capital Markets Sector FastMCP Server.

Exposes official FastMCP tools covering all 10 domain responsibilities:
1. get_nifty_snapshot: NIFTY 50 & Equity Index Snapshot
2. get_market_history: Historical Returns & Valuations
3. get_india_vix: India Volatility Index & Regime
4. get_market_breadth: NSE Market Breadth (Advances/Declines)
5. get_gsec_yield_snapshot: RBI G-Sec SGL Yield Curve (10Y, 5Y, 2Y)
6. get_mutual_fund_flows: AMFI Mutual Fund Inflows & SIP Data
7. get_fpi_equity_flows: NSDL / SEBI FPI & DII Equity Activity
8. get_corporate_earnings_valuation: Listed Corporate EPS, P/E & Growth
9. get_sectoral_performance: NSE Sectoral Indices Rotation
10. get_primary_market_ipos: Primary Market IPO & QIP Mobilization
11. get_investor_participation: Demat Accounts & Retail Distribution
12. get_market_economy_linkages: Equity Risk Premium & Buffett Indicator
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from capital_market_sector import client, database as db
from capital_market_sector.client import CapitalMarketDataUnavailableError
from capital_market_sector.models import (
    CorporateEarningsResponse,
    DataFreshness,
    FpiFlowsResponse,
    GSecYieldResponse,
    IndiaVixResponse,
    InvestorParticipationResponse,
    MarketBreadthResponse,
    MarketEconomyLinkageResponse,
    MarketHistoryResponse,
    MutualFundFlowsResponse,
    NiftySnapshotResponse,
    PrimaryMarketResponse,
    SectoralPerformanceResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="Capital Markets Sector MCP Server",
    instructions=(
        "Provides official Indian capital markets data: "
        "NIFTY 50 index levels, India VIX volatility, market breadth, "
        "historical equity valuations, RBI monthly SGL G-Sec transaction yields, "
        "AMFI mutual fund & SIP flows, NSDL/SEBI FPI equity investments, "
        "corporate earnings & EPS, sectoral index performance, primary IPO mobilization, "
        "demat account investor participation, and equity risk premium linkages."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


# ── 1. NIFTY Snapshot ────────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_nifty_snapshot",
    title="NIFTY 50 & Equity Index Snapshot",
    description="Fetches latest open, high, low, close, volume, and turnover for NIFTY 50 index.",
    tags={"capital_markets", "nifty", "nse", "equity", "index"},
)
async def get_nifty_snapshot() -> NiftySnapshotResponse | UnavailableResponse:
    """Fetch NIFTY 50 equity index snapshot from official / provider feed."""
    try:
        records = await client.fetch_nifty_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return NiftySnapshotResponse(status=freshness, records=records, total_records=len(records))
    except CapitalMarketDataUnavailableError as exc:
        return UnavailableResponse(tool="get_nifty_snapshot", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_nifty_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 2. Market History ────────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_market_history",
    title="Historical Equity Index Returns & Valuations",
    description="Fetches historical equity index performance, P/E ratio, P/B ratio, and dividend yield.",
    tags={"capital_markets", "nifty", "history", "valuations", "pe_ratio"},
)
async def get_market_history(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> MarketHistoryResponse | UnavailableResponse:
    """Fetch historical NIFTY 50 returns, P/E, P/B, and dividend yield."""
    try:
        records = await client.fetch_market_history(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketHistoryResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_market_history", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 3. India VIX ─────────────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_india_vix",
    title="India Volatility Index (India VIX)",
    description="Fetches India VIX volatility index level and volatility regime classification.",
    tags={"capital_markets", "vix", "volatility", "nse", "risk"},
)
async def get_india_vix(
    lookback_days: Annotated[int, Field(default=30, ge=1, le=180)] = 30,
) -> IndiaVixResponse | UnavailableResponse:
    """Fetch India VIX index level and risk regime classification."""
    try:
        records = await client.fetch_india_vix(lookback_days)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IndiaVixResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_india_vix", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 4. Market Breadth ────────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_market_breadth",
    title="NSE Equity Market Breadth",
    description="Fetches advances, declines, unchanged stock counts, and Advance/Decline ratio.",
    tags={"capital_markets", "breadth", "advances_declines", "nse"},
)
async def get_market_breadth() -> MarketBreadthResponse | UnavailableResponse:
    """Fetch NSE market breadth (advances, declines, advance/decline ratio)."""
    try:
        records = await client.fetch_market_breadth()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketBreadthResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_market_breadth", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 5. G-Sec Yield Snapshot ──────────────────────────────────────────────────

@mcp_server.tool(
    name="get_gsec_yield_snapshot",
    title="Government Securities (G-Sec) Yield Curve",
    description="Fetches monthly RBI SGL transaction yields at labeled 10Y, 5Y, and 2Y G-Sec maturities.",
    tags={"capital_markets", "gsec", "yields", "bonds", "rbi", "yield_curve"},
)
async def get_gsec_yield_snapshot() -> GSecYieldResponse | UnavailableResponse:
    """Fetch RBI month-end SGL transaction yields across 10Y, 5Y, and 2Y maturities."""
    try:
        records = await client.fetch_gsec_yield_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSecYieldResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_gsec_yield_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 6. Mutual Fund Flows ─────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_mutual_fund_flows",
    title="AMFI Mutual Fund Flows & SIP Activity",
    description="Fetches official AMFI monthly equity inflows, SIP contributions, and total industry AUM.",
    tags={"capital_markets", "mutual_funds", "amfi", "sip", "flows"},
)
async def get_mutual_fund_flows() -> MutualFundFlowsResponse | UnavailableResponse:
    """Fetch official AMFI mutual fund flows, SIP contributions, and AUM."""
    try:
        records = await client.fetch_mutual_fund_flows()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MutualFundFlowsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_mutual_fund_flows", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 7. FPI Equity Flows ──────────────────────────────────────────────────────

@mcp_server.tool(
    name="get_fpi_equity_flows",
    title="FPI & DII Institutional Equity Investment",
    description="Fetches official NSDL / SEBI FPI equity gross purchases, sales, net investment, and DII net flows.",
    tags={"capital_markets", "fpi", "fii", "dii", "institutional_flows"},
)
async def get_fpi_equity_flows() -> FpiFlowsResponse | UnavailableResponse:
    """Fetch official NSDL / SEBI Foreign Portfolio Investment (FPI) equity flows."""
    try:
        records = await client.fetch_fpi_equity_flows()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return FpiFlowsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_fpi_equity_flows", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 8. Corporate Earnings & Valuation ────────────────────────────────────────

@mcp_server.tool(
    name="get_corporate_earnings_valuation",
    title="Corporate Earnings, EPS & Valuation Ratios",
    description="Fetches NIFTY 50 TTM EPS, P/E, P/B, dividend yield, and corporate PAT growth.",
    tags={"capital_markets", "earnings", "eps", "pe_ratio", "valuation"},
)
async def get_corporate_earnings_valuation() -> CorporateEarningsResponse | UnavailableResponse:
    """Fetch corporate earnings, EPS, and valuation ratios for listed equities."""
    try:
        records = await client.fetch_corporate_earnings_valuation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return CorporateEarningsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_corporate_earnings_valuation", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 9. Sectoral Market Performance ───────────────────────────────────────────

@mcp_server.tool(
    name="get_sectoral_performance",
    title="NSE Sectoral Indices Performance & Rotation",
    description="Fetches comparative performance across Bank, IT, Auto, Pharma, and FMCG sectors vs NIFTY 50.",
    tags={"capital_markets", "sectoral", "bank_nifty", "it", "rotation"},
)
async def get_sectoral_performance() -> SectoralPerformanceResponse | UnavailableResponse:
    """Fetch NSE sectoral index performance and identify leading/lagging sectors."""
    try:
        records = await client.fetch_sectoral_performance()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SectoralPerformanceResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_sectoral_performance", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 10. Primary Capital Markets (IPOs) ───────────────────────────────────────

@mcp_server.tool(
    name="get_primary_market_ipos",
    title="Primary Market Equity Mobilization (IPOs & QIPs)",
    description="Fetches primary capital market equity resource mobilization via IPOs, QIPs, and rights issues.",
    tags={"capital_markets", "ipo", "qip", "primary_market", "fundraising"},
)
async def get_primary_market_ipos() -> PrimaryMarketResponse | UnavailableResponse:
    """Fetch primary equity market fundraising proceeds and issue counts."""
    try:
        records = await client.fetch_primary_market_ipos()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return PrimaryMarketResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_primary_market_ipos", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 11. Investor Participation & Demat Accounts ──────────────────────────────

@mcp_server.tool(
    name="get_investor_participation",
    title="Investor Participation & Demat Account Growth",
    description="Fetches total active Demat accounts (NSDL + CDSL), monthly additions, and retail turnover share.",
    tags={"capital_markets", "demat", "retail", "investor_participation"},
)
async def get_investor_participation() -> InvestorParticipationResponse | UnavailableResponse:
    """Fetch Demat account counts, additions, and market structure participation."""
    try:
        records = await client.fetch_investor_participation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return InvestorParticipationResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_investor_participation", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


# ── 12. Market-Economy Linkages ──────────────────────────────────────────────

@mcp_server.tool(
    name="get_market_economy_linkages",
    title="Market-Economy Linkages (Equity Risk Premium & Buffett Indicator)",
    description="Computes Equity Risk Premium (Earnings Yield - 10Y G-Sec) and Market Cap to GDP ratio.",
    tags={"capital_markets", "equity_risk_premium", "buffett_indicator", "macro_linkages"},
)
async def get_market_economy_linkages() -> MarketEconomyLinkageResponse | UnavailableResponse:
    """Compute Equity Risk Premium and Market Cap-to-GDP valuation linkages."""
    try:
        records = await client.fetch_market_economy_linkages()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketEconomyLinkageResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_market_economy_linkages", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp.resource("capitalmarkets://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "capital_market_sector",
        "authority": "National Stock Exchange of India (NSE) / RBI / SEBI / AMFI",
        "indicators_owned": [
            "nifty_50", "india_vix", "market_breadth", "gsec_10y_yield", "gsec_yield_curve",
            "mutual_fund_flows", "sip_inflow", "fpi_equity_flows", "corporate_earnings_ttm_eps",
            "sectoral_indices", "primary_market_ipos", "demat_accounts", "equity_risk_premium",
        ],
    }, indent=2)
