"""FastMCP Tool Server for Real Sector Macroeconomic Intelligence."""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastmcp import FastMCP
from .services.pipeline import RealSectorPipeline
from .agents.tools import SectorToolRegistry

# Initialize FastMCP Server for Real Sector
mcp_server = FastMCP(
    name="Real Sector Macroeconomic Tools",
    instructions="Provides standard tools for National Income, IIP, Prices/Inflation, and Agriculture."
)

_pipeline = RealSectorPipeline()
_registry = SectorToolRegistry(_pipeline)


@mcp_server.tool(
    name="get_national_income_snapshot",
    description="Fetches quarterly Real GDP (constant prices), Nominal GDP, and Gross Fixed Capital Formation (GFCF)."
)
def get_national_income_snapshot(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    return _registry.invoke("get_national_income_snapshot", {"start_date": start_date, "end_date": end_date}).model_dump()


@mcp_server.tool(
    name="get_industry_snapshot",
    description="Fetches Index of Industrial Production (IIP) use-based indicators and manufacturing output."
)
def get_industry_snapshot(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    return _registry.invoke("get_industry_snapshot", {"start_date": start_date, "end_date": end_date}).model_dump()


@mcp_server.tool(
    name="get_prices_snapshot",
    description="Fetches headline CPI, food CPI, core CPI, Wholesale Price Index (WPI), and House Price Index."
)
def get_prices_snapshot(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    return _registry.invoke("get_prices_snapshot", {"start_date": start_date, "end_date": end_date}).model_dump()


@mcp_server.tool(
    name="get_agriculture_snapshot",
    description="Fetches foodgrain production volume, crop yield, and Minimum Support Prices (MSP)."
)
def get_agriculture_snapshot(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    return _registry.invoke("get_agriculture_snapshot", {"start_date": start_date, "end_date": end_date}).model_dump()
