"""Real Sector FastAPI Sub-Application."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException, Query

from real_sector import client
from real_sector import database as db
from real_sector.client import RealSectorDataUnavailableError
from real_sector.models import (
    CoreIndustriesResponse,
    DataFreshness,
    IIPSectoralResponse,
    IIPUseBasedResponse,
    ManufacturingGVAResponse,
    MarketContextResponse,
    RealSectorJoinedResponse,
)
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Initialise schema and seed baseline data on startup."""
    try:
        db.initialise_schema(seed_baseline=True)
        logger.info("Real sector DuckDB initialised and seeded.")
    except Exception as exc:
        logger.error("Real sector DB init failed: %s", exc)
    yield


app = FastAPI(
    title="Real Sector & Industrial Output API",
    version="1.0.0",
    lifespan=_lifespan,
)


def create_app() -> FastAPI:
    return app


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "sector": "real_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    return {
        "sector": "real_sector",
        "version": "1.0.0",
        "authorities": ["MoSPI", "DPIIT", "RBI", "NSE"],
        "owns": [
            "iip_general", "iip_manufacturing", "iip_mining", "iip_electricity",
            "iip_capital_goods", "iip_consumer_durables", "core_steel", "core_cement",
            "manufacturing_gva",
        ],
    }


@app.get("/iip-sectoral", response_model=IIPSectoralResponse, tags=["Real Sector"])
async def iip_sectoral(lookback_months: int = Query(default=12, ge=1, le=60)) -> IIPSectoralResponse:
    try:
        records = await client.fetch_iip_sectoral(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IIPSectoralResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/iip-use-based", response_model=IIPUseBasedResponse, tags=["Real Sector"])
async def iip_use_based(lookback_months: int = Query(default=12, ge=1, le=60)) -> IIPUseBasedResponse:
    try:
        records = await client.fetch_iip_use_based(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IIPUseBasedResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/core-industries", response_model=CoreIndustriesResponse, tags=["Real Sector"])
async def core_industries(lookback_months: int = Query(default=12, ge=1, le=60)) -> CoreIndustriesResponse:
    try:
        records = await client.fetch_core_industries(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return CoreIndustriesResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/manufacturing-gva", response_model=ManufacturingGVAResponse, tags=["Real Sector"])
async def manufacturing_gva(lookback_quarters: int = Query(default=8, ge=1, le=32)) -> ManufacturingGVAResponse:
    try:
        records = await client.fetch_manufacturing_gva(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ManufacturingGVAResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/joined-diagnostic", response_model=RealSectorJoinedResponse, tags=["Real Sector"])
async def joined_diagnostic() -> RealSectorJoinedResponse:
    try:
        records = await client.fetch_joined_real_indicators()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return RealSectorJoinedResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/market-context", response_model=MarketContextResponse, tags=["Real Sector"])
async def market_context() -> MarketContextResponse:
    try:
        records = await client.fetch_infrastructure_market_context()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketContextResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
