"""Fiscal & Public Finance Sector package.

A specialized macroeconomic intelligence agent for Indian Government Finances,
Union Budget, Sovereign Debt, and Taxation.
"""
from __future__ import annotations

from fiscal_sector.agent import fiscal_agent_node, is_direct_fiscal_query
from fiscal_sector.executor import FiscalSectorAgentExecutor
from fiscal_sector.mcp_server import mcp_server

__all__ = [
    "mcp_server",
    "fiscal_agent_node",
    "is_direct_fiscal_query",
    "FiscalSectorAgentExecutor",
]
