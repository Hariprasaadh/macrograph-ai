"""External Sector FastAPI Sub-Application."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from external_sector import client
from external_sector.client import ExternalDataUnavailableError
from external_sector.models import (
    DataFreshness,
    ForexReservesResponse,
    TradeBalanceResponse,
)

app = FastAPI(
    title="External Sector API",
    description="HTTP endpoints for External Sector data.",
    version="1.0.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "sector": "external_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    return {
        "sector": "external_sector",
        "version": "1.0.0",
        "authority": "Reserve Bank of India (RBI)",
        "owns": ["forex_reserves", "exports", "imports", "trade_balance", "bop", "usd_inr", "reer", "neer"],
    }


@app.get("/forex-reserves", response_model=ForexReservesResponse, tags=["External"])
async def forex_reserves(lookback_weeks: int = Query(default=12, ge=1, le=52)) -> ForexReservesResponse:
    try:
        records = await client.fetch_forex_reserves(lookback_weeks)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ForexReservesResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/trade-balance", response_model=TradeBalanceResponse, tags=["External"])
async def trade_balance(lookback_months: int = Query(default=12, ge=1, le=60)) -> TradeBalanceResponse:
    try:
        records = await client.fetch_trade_balance(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TradeBalanceResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
