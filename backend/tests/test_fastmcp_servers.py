"""Tests for FastMCP Servers across Real, Finance, and Capital Markets sectors."""
from __future__ import annotations

import asyncio
import unittest
from real_sector.mcp_server import mcp_server as real_mcp
from finance_sector.mcp_server import mcp_server as finance_mcp
from capital_market_sector.mcp_server import mcp_server as cap_mcp


class FastMCPServerTests(unittest.TestCase):
    def test_real_sector_fastmcp_tools(self) -> None:
        tools = asyncio.run(real_mcp.list_tools())
        tool_names = {t.name for t in tools}
        expected = {
            "get_national_income_snapshot",
            "get_industry_snapshot",
            "get_prices_snapshot",
            "get_agriculture_snapshot",
        }
        self.assertTrue(expected.issubset(tool_names))

    def test_finance_sector_fastmcp_tools(self) -> None:
        tools = asyncio.run(finance_mcp.list_tools())
        tool_names = {t.name for t in tools}
        expected = {
            "get_gdp_growth_snapshot",
            "get_cpi_inflation_snapshot",
            "get_repo_rate_snapshot",
            "get_debt_to_gdp_snapshot",
            "get_forex_reserves_snapshot",
        }
        self.assertTrue(expected.issubset(tool_names))

    def test_capital_markets_fastmcp_tools(self) -> None:
        tools = asyncio.run(cap_mcp.list_tools())
        tool_names = {t.name for t in tools}
        expected = {
            "get_equity_snapshot",
            "get_vix_snapshot",
            "get_earnings_snapshot",
            "get_primary_market_snapshot",
            "get_mf_flows_snapshot",
        }
        self.assertTrue(expected.issubset(tool_names))


if __name__ == "__main__":
    unittest.main()
