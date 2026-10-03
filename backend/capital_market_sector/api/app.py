"""Capital Markets Sector FastAPI Sub-Application."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from capital_market_sector import client
from capital_market_sector.client import CapitalMarketDataUnavailableError
from capital_market_sector.models import (
    DataFreshness,
    GSecYieldResponse,
    IndiaVixResponse,
    NiftySnapshotResponse,
)

app = FastAPI(
    title="Capital Markets Sector API",
    description="HTTP endpoints for Capital Markets data.",
    version="1.0.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "sector": "capital_market_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    return {
        "sector": "capital_market_sector",
        "version": "1.0.0",
        "authority": "National Stock Exchange of India (NSE) / RBI",
        "owns": ["nifty_50", "india_vix", "market_breadth", "gsec_10y_yield"],
    }


@app.get("/nifty-snapshot", response_model=NiftySnapshotResponse, tags=["Capital Markets"])
async def nifty_snapshot() -> NiftySnapshotResponse:
    try:
        records = await client.fetch_nifty_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return NiftySnapshotResponse(status=freshness, total_records=len(records), records=records)
    except CapitalMarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/gsec-yields", response_model=GSecYieldResponse, tags=["Capital Markets"])
async def gsec_yields() -> GSecYieldResponse:
    try:
        records = await client.fetch_gsec_yield_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return GSecYieldResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
