"""Monetary Sector FastAPI Sub-Application."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from monetary_sector import client
from monetary_sector.client import MonetaryDataUnavailableError
from monetary_sector.models import (
    DataFreshness,
    MoneySupplyResponse,
    MonetaryStanceResponse,
    PolicyRatesResponse,
    SystemLiquidityResponse,
)

app = FastAPI(
    title="Monetary & Liquidity Sector API",
    description="HTTP endpoints for Monetary Policy & Liquidity data.",
    version="1.0.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "sector": "monetary_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    return {
        "sector": "monetary_sector",
        "version": "1.0.0",
        "authority": "Reserve Bank of India (RBI)",
        "owns": ["repo_rate", "sdf_rate", "msf_rate", "crr", "slr", "m1", "m2", "m3", "system_liquidity"],
    }


@app.get("/policy-rates", response_model=PolicyRatesResponse, tags=["Monetary"])
async def policy_rates(lookback_months: int = Query(default=12, ge=1, le=60)) -> PolicyRatesResponse:
    try:
        records = await client.fetch_policy_rates(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return PolicyRatesResponse(status=freshness, total_records=len(records), records=records)
    except MonetaryDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/money-supply", response_model=MoneySupplyResponse, tags=["Monetary"])
async def money_supply(lookback_months: int = Query(default=12, ge=1, le=60)) -> MoneySupplyResponse:
    try:
        records = await client.fetch_money_supply(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MoneySupplyResponse(status=freshness, total_records=len(records), records=records)
    except MonetaryDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/system-liquidity", response_model=SystemLiquidityResponse, tags=["Monetary"])
async def system_liquidity(
    lookback_months: int = Query(default=6, ge=1, le=36),
) -> SystemLiquidityResponse:
    try:
        records = await client.fetch_system_liquidity(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SystemLiquidityResponse(status=freshness, total_records=len(records), records=records)
    except MonetaryDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/stance", response_model=MonetaryStanceResponse, tags=["Monetary"])
async def monetary_stance() -> MonetaryStanceResponse:
    try:
        records = await client.fetch_monetary_stance_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MonetaryStanceResponse(status=freshness, total_records=len(records), records=records)
    except MonetaryDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
