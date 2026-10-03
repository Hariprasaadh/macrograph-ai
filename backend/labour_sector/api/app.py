"""Labour Sector FastAPI Sub-Application."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from labour_sector import client
from labour_sector.client import LabourDataUnavailableError
from labour_sector.models import (
    DataFreshness,
    LabourForceParticipationResponse,
    UnemploymentResponse,
)

app = FastAPI(
    title="Labour & Employment Sector API",
    description="HTTP endpoints for Labour & Employment data.",
    version="1.0.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "sector": "labour_sector", "version": "1.0.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    return {
        "sector": "labour_sector",
        "version": "1.0.0",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "owns": ["plfs_unemployment_rate", "plfs_lfpr", "plfs_wpr", "epfo_payroll_additions"],
    }


@app.get("/unemployment", response_model=UnemploymentResponse, tags=["Labour"])
async def unemployment() -> UnemploymentResponse:
    try:
        records = await client.fetch_unemployment_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return UnemploymentResponse(status=freshness, total_records=len(records), records=records)
    except LabourDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/lfpr", response_model=LabourForceParticipationResponse, tags=["Labour"])
async def lfpr() -> LabourForceParticipationResponse:
    try:
        records = await client.fetch_labour_force_participation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return LabourForceParticipationResponse(status=freshness, total_records=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
