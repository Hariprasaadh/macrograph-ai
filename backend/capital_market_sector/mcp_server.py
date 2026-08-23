"""FastMCP Tool Server for Capital Markets Macroeconomic Intelligence."""
from __future__ import annotations

from typing import Any, Dict
from fastmcp import FastMCP
from .clients.market_data_client import CapitalMarketsDataClient
from .agents.tools import SectorToolRegistry

# Initialize FastMCP Server for Capital Markets
mcp_server = FastMCP(
    name="Capital Markets Sector Tools",
    instructions="Provides standard tools for NIFTY/SENSEX equities, India VIX, corporate earnings, primary market, and mutual fund flows."
)

_client = CapitalMarketsDataClient()
_registry = SectorToolRegistry(_client)


@mcp_server.tool(
    name="get_equity_snapshot",
    description="Fetches NIFTY 50 and SENSEX price momentum, latest levels, and returns."
)
def get_equity_snapshot(include_source_metadata: bool = True) -> Dict[str, Any]:
    return _registry.invoke("get_equity_snapshot", {"include_source_metadata": include_source_metadata}).model_dump()


@mcp_server.tool(
    name="get_vix_snapshot",
    description="Fetches India VIX volatility regime classification and risk-off signals."
)
def get_vix_snapshot(include_source_metadata: bool = True) -> Dict[str, Any]:
    return _registry.invoke("get_vix_snapshot", {"include_source_metadata": include_source_metadata}).model_dump()


@mcp_server.tool(
    name="get_earnings_snapshot",
    description="Fetches corporate earnings indicators including EPS and PAT."
)
def get_earnings_snapshot(include_source_metadata: bool = True) -> Dict[str, Any]:
    return _registry.invoke("get_earnings_snapshot", {"include_source_metadata": include_source_metadata}).model_dump()


@mcp_server.tool(
    name="get_primary_market_snapshot",
    description="Fetches primary market activity including IPO count and debt issuances."
)
def get_primary_market_snapshot(include_source_metadata: bool = True) -> Dict[str, Any]:
    return _registry.invoke("get_primary_market_snapshot", {"include_source_metadata": include_source_metadata}).model_dump()


@mcp_server.tool(
    name="get_mf_flows_snapshot",
    description="Fetches mutual fund and domestic institutional investor (DII) flows."
)
def get_mf_flows_snapshot(include_source_metadata: bool = True) -> Dict[str, Any]:
    return _registry.invoke("get_mf_flows_snapshot", {"include_source_metadata": include_source_metadata}).model_dump()
