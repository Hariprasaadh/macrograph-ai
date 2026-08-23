"""FastMCP Tool Server for Finance Sector Macroeconomic Intelligence."""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastmcp import FastMCP
from .clients.finance_data_client import FinanceDataClient
from .agents.tools import FinanceToolRegistry

# Initialize FastMCP Server for Finance Sector
mcp_server = FastMCP(
    name="Finance Sector Macroeconomic Tools",
    instructions="Provides standard tools for GDP growth, CPI inflation, RBI repo rate, Debt-to-GDP, and Forex reserves."
)

_client = FinanceDataClient()
_registry = FinanceToolRegistry(_client)


@mcp_server.tool(
    name="get_gdp_growth_snapshot",
    description="Fetches Real GDP growth rate from MoSPI Power BI API data service."
)
def get_gdp_growth_snapshot(prices: str = "Constant") -> Dict[str, Any]:
    return _registry.invoke("get_gdp_growth_snapshot", {"prices": prices}).model_dump()


@mcp_server.tool(
    name="get_cpi_inflation_snapshot",
    description="Fetches headline Consumer Price Index (CPI) inflation rate against RBI tolerance bands (2%-6%)."
)
def get_cpi_inflation_snapshot() -> Dict[str, Any]:
    return _registry.invoke("get_cpi_inflation_snapshot", {}).model_dump()


@mcp_server.tool(
    name="get_repo_rate_snapshot",
    description="Fetches RBI Policy Repo Rate, SDF, MSF, Bank Rate, and CRR."
)
def get_repo_rate_snapshot() -> Dict[str, Any]:
    return _registry.invoke("get_repo_rate_snapshot", {}).model_dump()


@mcp_server.tool(
    name="get_debt_to_gdp_snapshot",
    description="Fetches General Government Debt-to-GDP ratio for fiscal sustainability."
)
def get_debt_to_gdp_snapshot() -> Dict[str, Any]:
    return _registry.invoke("get_debt_to_gdp_snapshot", {}).model_dump()


@mcp_server.tool(
    name="get_forex_reserves_snapshot",
    description="Fetches Foreign Exchange Reserves (Billion USD) and import cover buffers."
)
def get_forex_reserves_snapshot() -> Dict[str, Any]:
    return _registry.invoke("get_forex_reserves_snapshot", {}).model_dump()
