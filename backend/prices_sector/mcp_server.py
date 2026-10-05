"""Prices MCP tools: thin wrappers over the single source-aware client."""
from __future__ import annotations

from typing import Any
from fastmcp import FastMCP
from .client import fetch_cpi_inflation, fetch_cpi_subgroups, fetch_wpi_inflation, retrieve_prices
from .models import PriceRequest, PricesIntent

mcp_server = FastMCP('prices_sector_mcp', instructions='Live Prices observations with provenance. Use MoSPI by default; IMF only when explicitly selected.')


@mcp_server.tool()
async def get_price_data(source: str = 'mospi', indicator: str = 'cpi', operation: str = 'latest',
                         lookback_months: int = 12, filters: dict[str, Any] | None = None,
                         requests: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Retrieve one or more Prices series from the explicitly selected source."""
    filters = filters or {}
    intent = PricesIntent(source=source, operation=operation, lookback_months=lookback_months,
        requests=[PriceRequest.model_validate(r) for r in requests] if requests is not None else [PriceRequest(
            indicator=indicator, category=filters.get('category', 'headline'), sector=filters.get('sector', 'combined'))],
        geography=filters.get('geography', 'India'), countries=filters.get('countries', []), base_year=filters.get('base_year'),
        start_period=filters.get('start_period'), end_period=filters.get('end_period'), errors=filters.get('errors', []))
    return (await retrieve_prices(intent)).model_dump(mode='json')


@mcp_server.tool()
async def get_cpi_inflation(lookback_months: int = 12, geography: str = 'India', category: str | None = None) -> dict[str, Any]:
    """Retrieve MoSPI CPI monthly inflation, preserving official category names."""
    return (await fetch_cpi_inflation(lookback_months, geography, category)).model_dump(mode='json')


@mcp_server.tool()
async def get_cpi_subgroups(lookback_months: int = 12, categories: list[str] | None = None) -> dict[str, Any]:
    """Retrieve requested CPI categories, isolating unavailable subgroups."""
    return (await fetch_cpi_subgroups(lookback_months, categories)).model_dump(mode='json')


@mcp_server.tool()
async def get_wpi_inflation(lookback_months: int = 12, category: str | None = None) -> dict[str, Any]:
    """Retrieve WPI YoY from official inflation or matching prior-year indices."""
    return (await fetch_wpi_inflation(lookback_months, category)).model_dump(mode='json')
