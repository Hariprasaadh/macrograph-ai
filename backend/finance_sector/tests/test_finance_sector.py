from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from finance_sector.agents.executor import FinanceSectorAgentExecutor
from finance_sector.agents.tools import FinanceToolRegistry
from finance_sector.api.app import create_app
from finance_sector.clients.finance_data_client import FinanceDataClient
from finance_sector.protocols.a2a_protocol import EventQueue, RequestContext, TaskRequest, TaskStatus
from finance_sector.protocols.mcp_protocol import handle_mcp_rpc


class FinanceSectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = FinanceDataClient()

    def test_all_five_finance_indicator_fetchers(self) -> None:
        gdp = self.client.get_gdp_growth()
        self.assertIn("latest_value", gdp)
        self.assertIn("indicator", gdp)

        cpi = self.client.get_cpi_inflation()
        self.assertIn("latest_value", cpi)

        repo = self.client.get_repo_rate()
        self.assertIn("latest_value", repo)
        self.assertEqual(repo["latest_value"], 6.50)

        debt = self.client.get_debt_to_gdp()
        self.assertIn("latest_value", debt)

        forex = self.client.get_forex_reserves()
        self.assertIn("latest_value", forex)
        self.assertGreater(forex["latest_value"], 100.0)

    def test_mcp_tools_export_and_rpc(self) -> None:
        registry = FinanceToolRegistry(self.client)
        mcp_tools = registry.mcp_tools()
        self.assertEqual(len(mcp_tools), 5)
        names = {t.name for t in mcp_tools}
        self.assertEqual(names, {
            "get_gdp_growth_snapshot",
            "get_cpi_inflation_snapshot",
            "get_repo_rate_snapshot",
            "get_debt_to_gdp_snapshot",
            "get_forex_reserves_snapshot"
        })

        # Test MCP tools/list
        resp = handle_mcp_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, registry)
        self.assertEqual(len(resp["result"]["tools"]), 5)

        # Test MCP tools/call for GDP growth
        call_resp = handle_mcp_rpc({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_gdp_growth_snapshot", "arguments": {"prices": "Constant"}}
        }, registry)
        self.assertFalse(call_resp["result"]["isError"])
        self.assertIn("gdp_growth", call_resp["result"]["content"][0]["text"])

    def test_a2a_agent_card_and_executor(self) -> None:
        executor = FinanceSectorAgentExecutor(self.client)
        card = executor.get_agent_card()
        self.assertEqual(card.name, "Finance Sector Macroeconomic Agent")
        self.assertEqual(len(card.skills), 6)

        async def run_task():
            req = TaskRequest(
                query="Comprehensive report on GDP growth, inflation, repo rate, debt, and forex reserves",
                skills_required=["finance_sector_comprehensive_synthesis"]
            )
            ctx = RequestContext(task_id=req.task_id, request=req)
            q = EventQueue()
            return await executor.execute(ctx, q)

        task_res = asyncio.run(run_task())
        self.assertEqual(task_res.status, TaskStatus.COMPLETED)
        self.assertEqual(len(task_res.artifacts), 2)

    def test_fastapi_endpoints(self) -> None:
        app = create_app(self.client)
        tc = TestClient(app)

        # Test Agent Card
        resp = tc.get("/.well-known/agent.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Finance Sector Macroeconomic Agent")

        # Test A2A Task creation
        task_payload = {
            "query": "Check RBI Repo rate and forex reserves",
            "skills_required": ["repo_rate_analysis", "forex_reserves_analysis"]
        }
        resp = tc.post("/a2a/tasks", json=task_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "completed")

        # Test MCP RPC endpoint
        mcp_req = {"jsonrpc": "2.0", "id": 9, "method": "tools/list"}
        resp = tc.post("/mcp", json=mcp_req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["result"]["tools"]), 5)


if __name__ == "__main__":
    unittest.main()
