"""Capital Markets Sector FastAPI Sub-Application.

Exposes RESTful endpoints for all 10 domain responsibilities with typed Pydantic responses.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from capital_market_sector import client
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
)

app = FastAPI(
    title="Capital Markets Sector API",
    description="HTTP endpoints for Indian Capital Markets data and macroeconomic analysis.",
    version="1.0.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Health check for Capital Markets sector sub-application."""
    return {"status": "healthy", "sector": "capital_market_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    """Domain metadata and indicators owned by Capital Markets sector."""
    return {
        "sector": "capital_market_sector",
        "version": "1.0.0",
        "authority": "National Stock Exchange of India (NSE) / RBI / SEBI / AMFI",
        "owns": [
            "nifty_50", "sensex", "india_vix", "market_breadth", "gsec_10y_yield",
            "gsec_yield_curve", "mutual_fund_flows", "sip_inflow", "fpi_equity_flows",
            "corporate_earnings_ttm_eps", "sectoral_indices", "primary_market_ipos",
            "demat_accounts", "equity_risk_premium",
        ],
    }


@app.get("/nifty-snapshot", response_model=NiftySnapshotResponse, tags=["Capital Markets"])
async def nifty_snapshot() -> NiftySnapshotResponse:
    """Get latest NIFTY 50 and equity index snapshot."""
    try:
        records = await client.fetch_nifty_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return NiftySnapshotResponse(status=freshness, total_records=len(records), records=records)
    except CapitalMarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/market-history", response_model=MarketHistoryResponse, tags=["Capital Markets"])
async def market_history(
    lookback_months: int = Query(default=12, ge=1, le=60, description="Lookback months"),
) -> MarketHistoryResponse:
    """Get historical equity returns and valuation ratios."""
    try:
        records = await client.fetch_market_history(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketHistoryResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/india-vix", response_model=IndiaVixResponse, tags=["Capital Markets"])
async def india_vix(
    lookback_days: int = Query(default=30, ge=1, le=180, description="Lookback days"),
) -> IndiaVixResponse:
    """Get India VIX volatility index and regime."""
    try:
        records = await client.fetch_india_vix(lookback_days)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IndiaVixResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/market-breadth", response_model=MarketBreadthResponse, tags=["Capital Markets"])
async def market_breadth() -> MarketBreadthResponse:
    """Get NSE market breadth (advances/declines/volume)."""
    try:
        records = await client.fetch_market_breadth()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketBreadthResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/gsec-yields", response_model=GSecYieldResponse, tags=["Capital Markets"])
async def gsec_yields() -> GSecYieldResponse:
    """Get RBI month-end SGL transaction yields (10Y, 5Y, 2Y)."""
    try:
        records = await client.fetch_gsec_yield_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSecYieldResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/mutual-fund-flows", response_model=MutualFundFlowsResponse, tags=["Capital Markets"])
async def mutual_fund_flows() -> MutualFundFlowsResponse:
    """Get AMFI mutual fund flows, SIP contributions, and total AUM."""
    try:
        records = await client.fetch_mutual_fund_flows()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MutualFundFlowsResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/fpi-flows", response_model=FpiFlowsResponse, tags=["Capital Markets"])
async def fpi_flows() -> FpiFlowsResponse:
    """Get NSDL / SEBI FPI & DII equity investment flows."""
    try:
        records = await client.fetch_fpi_equity_flows()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return FpiFlowsResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/corporate-earnings", response_model=CorporateEarningsResponse, tags=["Capital Markets"])
async def corporate_earnings() -> CorporateEarningsResponse:
    """Get NIFTY 50 corporate earnings, EPS, and valuation ratios."""
    try:
        records = await client.fetch_corporate_earnings_valuation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return CorporateEarningsResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/sectoral-performance", response_model=SectoralPerformanceResponse, tags=["Capital Markets"])
async def sectoral_performance() -> SectoralPerformanceResponse:
    """Get NSE sectoral indices performance and rotation."""
    try:
        records = await client.fetch_sectoral_performance()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SectoralPerformanceResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/primary-market-ipos", response_model=PrimaryMarketResponse, tags=["Capital Markets"])
async def primary_market_ipos() -> PrimaryMarketResponse:
    """Get primary market equity mobilization through IPOs, QIPs, and rights."""
    try:
        records = await client.fetch_primary_market_ipos()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return PrimaryMarketResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/investor-participation", response_model=InvestorParticipationResponse, tags=["Capital Markets"])
async def investor_participation() -> InvestorParticipationResponse:
    """Get active Demat account statistics and retail participation."""
    try:
        records = await client.fetch_investor_participation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return InvestorParticipationResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/market-economy-linkages", response_model=MarketEconomyLinkageResponse, tags=["Capital Markets"])
async def market_economy_linkages() -> MarketEconomyLinkageResponse:
    """Get Equity Risk Premium and Buffett Indicator valuation linkages."""
    try:
        records = await client.fetch_market_economy_linkages()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketEconomyLinkageResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
