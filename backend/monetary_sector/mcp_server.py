"""Monetary Sector FastMCP Server.

Exposes 6 tools discoverable via MCP registry:
  - get_policy_rates
  - get_money_supply
  - get_system_liquidity
  - get_monetary_stance_snapshot
  - get_realtime_monetary_news
  - clear_monetary_cache
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from monetary_sector import client, database as db
from monetary_sector.client import MonetaryDataUnavailableError
from monetary_sector.models import (
    CacheClearResponse,
    DataFreshness,
    MonetaryNewsResponse,
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
    description="Fetches the latest sourced repo rate and MPC stance label snapshot.",
    tags={"monetary", "mpc", "stance", "rbi"},
)
async def get_monetary_stance_snapshot() -> MonetaryStanceResponse | UnavailableResponse:
    try:
        records = await client.fetch_monetary_stance_snapshot()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MonetaryStanceResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_monetary_stance_snapshot", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="clear_monetary_cache",
    title="Clear Monetary Sector Cache",
    description=(
        "Deletes cached rows from the monetary sector DuckDB tables (policy rates, "
        "money supply, system liquidity, monetary stance) while preserving the "
        "fetch_log audit. Use it to prove the live-or-unavailable path: with no "
        "cache, failed live MCP fetches raise instead of serving stale rows."
    ),
    tags={"monetary", "cache", "maintenance"},
)
async def clear_monetary_cache() -> CacheClearResponse | UnavailableResponse:
    try:
        cleared = db.clear_cached_tables()
        total = sum(cleared.values())
        return CacheClearResponse(
            status="cache_cleared",
            cleared_tables=cleared,
            total_rows_deleted=total,
            message=(
                f"Cleared {total} cached rows. Subsequent queries pull live MCP data; "
                "if all MCP servers are unreachable they now report unavailable."
            ),
        )
    except Exception as exc:
        return UnavailableResponse(tool="clear_monetary_cache", reason=f"Unexpected error: {exc}", error_detail=repr(exc))


@mcp_server.tool(
    name="get_realtime_monetary_news",
    title="Real-Time MPC & Policy Intelligence",
    description=(
        "Enriches monetary analysis with real-time MPC news, RBI press releases, "
        "and policy commentary using Tavily AI Search (TVLY_KEY_1). "
        "Plain HTTPS fetch with no subprocess, mirroring the finance sector news tool."
    ),
    tags={"monetary", "news", "mpc", "rbi", "realtime", "tavily"},
)
async def get_realtime_monetary_news(
    query: Annotated[
        str,
        Field(default="RBI monetary policy repo rate MPC stance India", description="Monetary search query."),
    ] = "RBI monetary policy repo rate MPC stance India",
    max_results: Annotated[
        int,
        Field(default=5, ge=1, le=10, description="Maximum news articles to retrieve."),
    ] = 5,
) -> MonetaryNewsResponse | UnavailableResponse:
    """Return real-time MPC news and RBI policy updates for a topic."""
    try:
        from monetary_sector.models import TavilyNewsItem

        items = await client.fetch_mpc_news_via_tavily_mcp(query=query, max_results=max_results)
        return MonetaryNewsResponse(
            status=DataFreshness.LIVE if items else DataFreshness.UNAVAILABLE,
            query=query,
            news_items=[
                TavilyNewsItem(
                    title=item["title"],
                    url=item["url"],
                    content=item["snippet"],
                    published_date=item.get("date"),
                    source=item.get("source", "Tavily AI Search"),
                )
                for item in items
            ],
            total_results=len(items),
        )
    except Exception as exc:
        logger.exception("get_realtime_monetary_news: unexpected error")
        return UnavailableResponse(
            tool="get_realtime_monetary_news",
            reason=f"News search failed: {exc}",
            error_detail=repr(exc),
        )


@mcp_server.resource("monetary://catalog")
def get_catalog() -> str:
    import json
    return json.dumps({
        "sector": "monetary_sector",
        "authority": "Reserve Bank of India (RBI)",
        "indicators_owned": ["repo_rate", "sdf_rate", "msf_rate", "crr", "slr", "m1", "m2", "m3", "system_liquidity"],
        "tables": {
            "policy_rates": "/banking/select-economic-indicators",
            "money_supply": "/banking/money-stock-measures",
            "system_liquidity": "/banking/liquidity-operations",
        },
        "citation_policy": "Strict provenance citation required for all observations.",
    }, indent=2)


@mcp_server.prompt()
def analyze_monetary_policy(focus_area: str = "rates_stance_liquidity") -> str:
    """Prompt template for analyzing India's monetary policy stance and liquidity."""
    return (
        f"Perform a comprehensive review of India's monetary policy "
        f"focusing on {focus_area}. "
        f"Fetch the latest policy repo rate, SDF/MSF corridor, CRR/SLR, M3 money "
        f"growth, system liquidity operations, and the MPC stance label. "
        f"Strictly enforce the 'No Source, No Answer' policy with official RBI "
        f"DBIE citations. Never infer a real policy rate without headline CPI, "
        f"a net LAF total, or a stance beyond the sourced policy-rate table."
    )
