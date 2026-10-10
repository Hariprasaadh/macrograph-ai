"""Prices & Inflation Sector FastMCP Server.

Exposes official MoSPI CPI/WPI observations with IMF fallback for headline CPI.
Strict Provenance: every response includes observation-level citation metadata.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from .client import (
    fetch_cpi_inflation,
    fetch_cpi_subgroups,
    fetch_wpi_inflation,
    retrieve_prices,
)
from .market_client import fetch_inflation_market_proxies, fetch_realtime_prices_news
from .models import PriceRequest, PricesIntent, PricesResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP Server — metadata used by MCP registries and discovery layers
# ---------------------------------------------------------------------------

mcp_server = FastMCP(
    name="Prices & Inflation Sector MCP Server",
    instructions=(
        "Provides official Indian price statistics: MoSPI CPI (headline and subgroups) "
        "and WPI, with IMF CPI as an explicitly-selected fallback for headline comparisons. "
        "All values carry mandatory citation metadata (source authority, dataset reference, "
        "series code, observation period, retrieval URL). "
        "No Source, No Answer: values without citations are a protocol violation. "
        "On failure, a PricesResult with status=unavailable is returned instead of "
        "hardcoded or estimated values."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server


# ---------------------------------------------------------------------------
# Tool 1 — Generic price retrieval (single source-aware entry point)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_price_data",
    title="Price Data Retrieval (CPI / WPI)",
    description=(
        "Retrieves one or more Prices series from the explicitly selected source. "
        "Source: MoSPI e-Sankhyiki by default; IMF SDMX only when source='imf' is selected. "
        "Live fetch via domain MCP with per-request failure isolation."
    ),
    tags={"prices", "cpi", "wpi", "inflation", "india", "mospi", "imf"},
)
async def get_price_data(
    source: Annotated[
        str,
        Field(default="mospi", description="Explicit source: 'mospi' or 'imf'."),
    ] = "mospi",
    indicator: Annotated[
        str,
        Field(default="cpi", description="Indicator family: 'cpi' or 'wpi'."),
    ] = "cpi",
    operation: Annotated[
        str,
        Field(default="latest", description="Operation: 'latest', 'trend', or 'comparison'."),
    ] = "latest",
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=120, description="Number of months of history to return."),
    ] = 12,
    filters: Annotated[
        dict[str, Any] | None,
        Field(default=None, description="Scope filters: category, sector, geography, periods."),
    ] = None,
    requests: Annotated[
        list[dict[str, Any]] | None,
        Field(default=None, description="Explicit PriceRequest list; overrides indicator/filters."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve one or more Prices series from the explicitly selected source."""
    try:
        filters = filters or {}
        intent = PricesIntent(
            source=source,  # type: ignore[arg-type]
            operation=operation,  # type: ignore[arg-type]
            lookback_months=lookback_months,
            requests=[PriceRequest.model_validate(r) for r in requests]
            if requests is not None
            else [
                PriceRequest(
                    indicator=indicator,  # type: ignore[arg-type]
                    category=filters.get("category", "headline"),
                    sector=filters.get("sector", "combined"),  # type: ignore[arg-type]
                )
            ],
            geography=filters.get("geography", "India"),
            countries=filters.get("countries", []),
            base_year=filters.get("base_year"),
            start_period=filters.get("start_period"),
            end_period=filters.get("end_period"),
            errors=filters.get("errors", []),
        )
        return (await retrieve_prices(intent)).model_dump(mode="json")
    except Exception as exc:
        logger.exception("get_price_data: unexpected error")
        return PricesResult(
            status="unavailable",
            error=f"Unexpected error: {exc}",
            errors=[{"request": "prices_mcp", "reason": repr(exc)}],
        ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Tool 2 — CPI headline / category inflation
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_cpi_inflation",
    title="CPI Inflation (MoSPI)",
    description=(
        "Retrieves MoSPI CPI monthly inflation, preserving official category names. "
        "Source: MoSPI e-Sankhyiki CPI dataset. "
        "Live fetch via MoSPI MCP with unavailable isolation per subgroup."
    ),
    tags={"prices", "cpi", "inflation", "india", "mospi"},
)
async def get_cpi_inflation(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=120, description="Number of months of history to return."),
    ] = 12,
    geography: Annotated[
        str,
        Field(default="India", description="Geography label (default 'India')."),
    ] = "India",
    category: Annotated[
        str | None,
        Field(default=None, description="Official CPI category; None selects headline."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve MoSPI CPI monthly inflation, preserving official category names."""
    try:
        return (await fetch_cpi_inflation(lookback_months, geography, category)).model_dump(mode="json")
    except Exception as exc:
        logger.exception("get_cpi_inflation: unexpected error")
        return PricesResult(
            status="unavailable",
            source="MoSPI",
            error=f"Unexpected error: {exc}",
            errors=[{"request": "cpi", "reason": repr(exc)}],
        ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Tool 3 — CPI subgroups
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_cpi_subgroups",
    title="CPI Subgroups (Food, Fuel, Housing, Health, Transport)",
    description=(
        "Retrieves requested CPI categories, isolating unavailable subgroups. "
        "Source: MoSPI e-Sankhyiki CPI dataset. "
        "Each unavailable subgroup is reported in errors, never estimated."
    ),
    tags={"prices", "cpi", "subgroups", "inflation", "india", "mospi"},
)
async def get_cpi_subgroups(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=120, description="Number of months of history to return."),
    ] = 12,
    categories: Annotated[
        list[str] | None,
        Field(default=None, description="CPI categories; defaults to food/fuel/housing/health/transport."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve requested CPI categories, isolating unavailable subgroups."""
    try:
        return (await fetch_cpi_subgroups(lookback_months, categories)).model_dump(mode="json")
    except Exception as exc:
        logger.exception("get_cpi_subgroups: unexpected error")
        return PricesResult(
            status="unavailable",
            source="MoSPI",
            error=f"Unexpected error: {exc}",
            errors=[{"request": "cpi-subgroups", "reason": repr(exc)}],
        ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Tool 4 — WPI inflation
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_wpi_inflation",
    title="WPI Inflation (Official Wholesale Prices)",
    description=(
        "Retrieves WPI YoY from official inflation or matching prior-year indices. "
        "Source: MoSPI e-Sankhyiki WPI dataset. "
        "Live fetch via MoSPI MCP with unavailable isolation."
    ),
    tags={"prices", "wpi", "inflation", "india", "mospi"},
)
async def get_wpi_inflation(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=120, description="Number of months of history to return."),
    ] = 12,
    category: Annotated[
        str | None,
        Field(default=None, description="Official WPI category; None selects headline."),
    ] = None,
) -> dict[str, Any]:
    """Retrieve WPI YoY from official inflation or matching prior-year indices."""
    try:
        return (await fetch_wpi_inflation(lookback_months, category)).model_dump(mode="json")
    except Exception as exc:
        logger.exception("get_wpi_inflation: unexpected error")
        return PricesResult(
            status="unavailable",
            source="MoSPI",
            error=f"Unexpected error: {exc}",
            errors=[{"request": "wpi", "reason": repr(exc)}],
        ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Tool 5 — Inflation Market Proxies (Yahoo Finance)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_inflation_market_proxies",
    title="Inflation Market Proxies (Crude, Gold, USD/INR, Nifty)",
    description=(
        "Fetches live market context for inflation analysis: WTI crude, gold, "
        "USD/INR, and Nifty 50 via Yahoo Finance. These are context signals, "
        "never CPI/WPI measurements."
    ),
    tags={"prices", "market", "crude", "gold", "usd-inr", "yfinance"},
)
async def get_inflation_market_proxies() -> dict[str, Any]:
    """Return live inflation-sensitive market proxy quotes."""
    try:
        return await fetch_inflation_market_proxies()
    except Exception as exc:
        logger.exception("get_inflation_market_proxies: unexpected error")
        return {"status": "unavailable", "proxies": [], "total": 0,
                "error_message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 6 — Real-Time Inflation News & Intelligence (Tavily)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_realtime_inflation_news",
    title="Real-Time Inflation Releases & RBI Commentary",
    description=(
        "Enriches inflation intelligence with real-time CPI/WPI release coverage "
        "and RBI commentary using Tavily AI Search (TVLY_KEY_3)."
    ),
    tags={"prices", "news", "inflation", "rbi", "realtime", "tavily"},
)
async def get_realtime_inflation_news(
    query: Annotated[
        str,
        Field(default="India CPI inflation MoSPI release latest", description="Inflation search query."),
    ] = "India CPI inflation MoSPI release latest",
    max_results: Annotated[
        int,
        Field(default=5, ge=1, le=10, description="Maximum news articles to retrieve."),
    ] = 5,
) -> dict[str, Any]:
    """Return real-time inflation news and policy updates for a topic."""
    try:
        return await fetch_realtime_prices_news(query=query, max_results=max_results)
    except Exception as exc:
        logger.exception("get_realtime_inflation_news: unexpected error")
        return {"status": "unavailable", "query": query, "news_items": [],
                "total_results": 0, "error_message": str(exc)}


# ---------------------------------------------------------------------------
# Resources — Read-only reference catalogs (FastMCP Resource)
# ---------------------------------------------------------------------------

@mcp.resource("prices://catalog")
def get_catalog() -> str:
    """Read-only catalog of official MoSPI/IMF table references and indicator mappings."""
    import json

    return json.dumps(
        {
            "sector": "prices_sector",
            "authorities": ["Ministry of Statistics and Programme Implementation (MoSPI)", "International Monetary Fund (IMF)"],
            "tables": {
                "cpi": "mospi.CPI (Consumer Price Index, Group/Item endpoint)",
                "wpi": "mospi.WPI (Wholesale Price Index)",
                "imf_cpi": "imf.CPI (IND.CPI._T.YOY_PCH_PA_PT.M)",
            },
            "ownership": "CPI, WPI, Core/Food inflation are owned by prices_sector. Peer agents must consume via A2A, never re-fetch.",
            "citation_policy": "Strict provenance citation required for all observations.",
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompts — Reusable analysis prompt templates (FastMCP Prompt)
# ---------------------------------------------------------------------------

@mcp.prompt()
def analyze_price_inflation(focus_area: str = "cpi_headline_and_subgroups") -> str:
    """Prompt template for analyzing Indian price inflation dynamics."""
    return (
        "Perform a comprehensive review of Indian price inflation "
        f"focusing on {focus_area}. "
        "Fetch latest MoSPI CPI headline and subgroups (food, fuel and light, housing, "
        "health, transport) plus WPI headline YoY. "
        "Strictly enforce the 'No Source, No Answer' policy with official MoSPI/IMF citations. "
        "Never estimate unavailable subgroups; report them as unavailable."
    )
