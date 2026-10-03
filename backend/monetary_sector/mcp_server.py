"""Monetary Sector FastMCP Server.

Exposes 4 tools discoverable via MCP registry:
  - get_policy_rates
  - get_money_supply
  - get_system_liquidity
  - get_monetary_stance_snapshot
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from monetary_sector import client, database as db
from monetary_sector.client import MonetaryDataUnavailableError
from monetary_sector.models import (
    DataFreshness,
    MoneySupplyResponse,
    MonetaryStanceResponse,
    PolicyRatesResponse,
    SystemLiquidityResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="Monetary & Liquidity Sector MCP Server",
    instructions=(
        "Provides official RBI monetary policy data for India: "
        "Repo Rate, Reverse Repo, SDF, MSF, CRR, SLR, Money Supply (M1, M2, M3), "
        "System Liquidity, and MPC Policy Stance. "
        "Data is sourced from the RBIH DBIE MCP deployment's latest scrape, not real-time. "
        "All values carry mandatory citation metadata."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


@mcp_server.tool(
    name="get_policy_rates",
    title="RBI Policy Rates & Reserve Requirements",
    description="Fetches the rates and reserve ratios published in the RBIH DBIE Select Economic Indicators snapshot.",
    tags={"monetary", "repo", "rates", "rbi", "crr", "slr"},
)
async def get_policy_rates(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> PolicyRatesResponse | UnavailableResponse:
    try:
        records = await client.fetch_policy_rates(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return PolicyRatesResponse(status=freshness, records=records, total_records=len(records))
    except MonetaryDataUnavailableError as exc:
        return UnavailableResponse(tool="get_policy_rates", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_policy_rates", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_money_supply",
    title="Money Supply Aggregates (M1, M2, M3)",
    description="Fetches published money-stock aggregates from the RBIH DBIE Money Stock Measures table.",
    tags={"monetary", "money-supply", "m1", "m3", "rbi"},
)
async def get_money_supply(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> MoneySupplyResponse | UnavailableResponse:
    try:
        records = await client.fetch_money_supply(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MoneySupplyResponse(status=freshness, records=records, total_records=len(records))
    except MonetaryDataUnavailableError as exc:
        return UnavailableResponse(tool="get_money_supply", reason=str(exc))
    except Exception as exc:
        return UnavailableResponse(tool="get_money_supply", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_system_liquidity",
    title="RBI System Liquidity Indicators",
    description="Fetches RBI liquidity-operation components from the RBIH DBIE snapshot; it does not infer a net LAF total.",
    tags={"monetary", "liquidity", "laf", "rbi"},
)
async def get_system_liquidity(
    lookback_months: Annotated[int, Field(default=6, ge=1, le=36)] = 6,
) -> SystemLiquidityResponse | UnavailableResponse:
    try:
        records = await client.fetch_system_liquidity(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return SystemLiquidityResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_system_liquidity", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_monetary_stance_snapshot",
    title="Monetary Policy Committee Stance Snapshot",
    description="Fetches latest Repo rate, policy stance label, real policy rate, and M3 growth.",
    tags={"monetary", "mpc", "stance", "rbi"},
)
async def get_monetary_stance_snapshot() -> MonetaryStanceResponse | UnavailableResponse:
    try:
        records = await client.fetch_monetary_stance_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MonetaryStanceResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_monetary_stance_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp.resource("monetary://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "monetary_sector",
        "authority": "Reserve Bank of India (RBI)",
        "indicators_owned": ["repo_rate", "sdf_rate", "msf_rate", "crr", "slr", "m1", "m2", "m3", "system_liquidity"],
    }, indent=2)
