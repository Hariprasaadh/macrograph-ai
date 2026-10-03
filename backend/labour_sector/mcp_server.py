"""Labour & Employment Sector FastMCP Server.

Exposes 4 tools:
  - get_unemployment_snapshot
  - get_labour_force_participation
  - get_worker_population_ratio
  - get_labour_employment_conditions
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from labour_sector import client, database as db
from labour_sector.client import LabourDataUnavailableError
from labour_sector.models import (
    DataFreshness,
    LabourConditionsResponse,
    LabourForceParticipationResponse,
    UnemploymentResponse,
    UnavailableResponse,
    WorkerPopulationRatioResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="Labour & Employment Sector MCP Server",
    instructions=(
        "Provides official MoSPI PLFS labour and employment data for India: "
        "Unemployment Rate (UR %), Labour Force Participation Rate (LFPR %), "
        "Worker Population Ratio (WPR %), and EPFO formal payroll additions."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


@mcp_server.tool(
    name="get_unemployment_snapshot",
    title="PLFS Unemployment Rate (UR %)",
    description="Fetches overall, urban, rural, and youth Unemployment Rate (UR %) from MoSPI PLFS.",
    tags={"labour", "unemployment", "plfs", "mospi", "jobs"},
)
async def get_unemployment_snapshot() -> UnemploymentResponse | UnavailableResponse:
    try:
        records = await client.fetch_unemployment_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return UnemploymentResponse(status=freshness, records=records, total_records=len(records))
    except LabourDataUnavailableError as exc:
        return UnavailableResponse(tool="get_unemployment_snapshot", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_unemployment_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_labour_force_participation",
    title="Labour Force Participation Rate (LFPR %)",
    description="Fetches overall, male, female, urban, and rural LFPR (%) from MoSPI PLFS.",
    tags={"labour", "lfpr", "plfs", "female_lfpr", "mospi"},
)
async def get_labour_force_participation() -> LabourForceParticipationResponse | UnavailableResponse:
    try:
        records = await client.fetch_labour_force_participation()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return LabourForceParticipationResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_labour_force_participation", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_worker_population_ratio",
    title="Worker Population Ratio (WPR %)",
    description="Fetches overall, male, female, urban, and rural WPR (%) from MoSPI PLFS.",
    tags={"labour", "wpr", "plfs", "employment", "mospi"},
)
async def get_worker_population_ratio() -> WorkerPopulationRatioResponse | UnavailableResponse:
    try:
        records = await client.fetch_worker_population_ratio()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return WorkerPopulationRatioResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_worker_population_ratio", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_labour_employment_conditions",
    title="EPFO Payroll & Employment Quality Conditions",
    description="Fetches net EPFO formal payroll additions and employment status shares (Self-employed, Regular, Casual).",
    tags={"labour", "epfo", "payroll", "employment", "wages"},
)
async def get_labour_employment_conditions() -> LabourConditionsResponse | UnavailableResponse:
    try:
        records = await client.fetch_labour_employment_conditions()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return LabourConditionsResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_labour_employment_conditions", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp.resource("labour://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "labour_sector",
        "authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
        "indicators_owned": ["plfs_unemployment_rate", "plfs_lfpr", "plfs_wpr", "epfo_payroll_additions"],
    }, indent=2)
