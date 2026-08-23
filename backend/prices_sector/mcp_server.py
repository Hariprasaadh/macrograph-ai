"""Prices & Inflation Sector FastMCP Tool Server."""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.database.macro_store import macro_store

mcp_server = FastMCP(
    "prices_sector_mcp",
    instructions="FastMCP server providing Indian price indices and inflation metrics (CPI, WPI, Food CPI, Crude oil)."
)


class PriceQueryInput(BaseModel):
    indicator: Optional[str] = Field(default="cpi_headline", description="Indicator key: cpi_headline, wpi_all, brent_crude")


@mcp_server.tool(name="get_cpi_snapshot", description="Fetches All India CPI Combined Headline inflation.")
def get_cpi_snapshot(params: PriceQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.prices.cpi_headline")
    if obs:
        return {"agent": "prices_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "prices_sector", "status": "error", "message": "CPI observation unavailable."}


@mcp_server.tool(name="get_wpi_snapshot", description="Fetches Wholesale Price Index (WPI) all commodities inflation.")
def get_wpi_snapshot(params: PriceQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.prices.wpi_all")
    if obs:
        return {"agent": "prices_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "prices_sector", "status": "error", "message": "WPI observation unavailable."}


@mcp_server.tool(name="get_crude_oil_snapshot", description="Fetches Brent Crude oil benchmark spot price.")
def get_crude_oil_snapshot(params: PriceQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.prices.brent_crude")
    if obs:
        return {"agent": "prices_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "prices_sector", "status": "error", "message": "Crude oil observation unavailable."}
