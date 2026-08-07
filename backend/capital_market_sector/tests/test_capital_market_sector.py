from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from capital_market_sector.clients.market_data_client import CapitalMarketsDataClient
from capital_market_sector.agents.executor import CapitalMarketsAgentExecutor
from capital_market_sector.agents.tools import SectorToolRegistry
from capital_market_sector.api.app import create_app
from capital_market_sector.protocols.a2a_protocol import EventQueue, RequestContext, TaskRequest, TaskStatus
from capital_market_sector.protocols.mcp_protocol import handle_mcp_rpc


class CapitalMarketSectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = CapitalMarketsDataClient()

    def test_all_five_capital_market_fetchers(self) -> None:
        nifty = self.client.get_nifty_50()
        sensex = self.client.get_sensex()
        vix = self.client.get_india_vix()
        earnings = self.client.get_corporate_earnings()
        primary = self.client.get_primary_market_activity()
        flows = self.client.get_mf_flows()

        self.assertFalse(nifty.empty)
        self.assertEqual(nifty["indicator_name"].iloc[-1], "NIFTY 50")
        self.assertIn("value", nifty.columns)

        self.assertFalse(sensex.empty)
        self.assertEqual(sensex["indicator_name"].iloc[-1], "SENSEX")
        self.assertIn("value", sensex.columns)

        self.assertFalse(vix.empty)
        self.assertEqual(vix["indicator_name"].iloc[-1], "India VIX")
        self.assertIn("value", vix.columns)

        self.assertFalse(earnings.empty)
        self.assertTrue((earnings["indicator_name"].isin(["EPS", "PAT (Billion INR)"])).all())

        self.assertFalse(primary.empty)
        self.assertTrue((primary["indicator_name"].isin(["IPO Count", "Debt Issuance (INR Crore)"])).all())

        self.assertFalse(flows.empty)
        self.assertTrue((flows["indicator_name"].isin(["Equity Net Flow", "DII Net Purchase"])).all())

    def test_mcp_tools_export_and_rpc(self) -> None:
        registry = SectorToolRegistry(self.client)
        mcp_tools = registry.mcp_tools()
        self.assertEqual(len(mcp_tools), 5)
        names = {t.name for t in mcp_tools}
        self.assertEqual(names, {
            "get_equity_snapshot",
            "get_vix_snapshot",
            "get_earnings_snapshot",
            "get_primary_market_snapshot",
            "get_mf_flows_snapshot",
        })

        resp = handle_mcp_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, registry)
        self.assertEqual(len(resp["result"]["tools"]), 5)

        call_resp = handle_mcp_rpc({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_equity_snapshot", "arguments": {"include_source_metadata": True}}
        }, registry)
        self.assertFalse(call_resp["result"]["isError"])
        self.assertIn("agent", call_resp["result"]["content"][0]["text"])

    def test_a2a_agent_card_and_executor(self) -> None:
        executor = CapitalMarketsAgentExecutor(self.client)
        card = executor.get_agent_card()
        self.assertEqual(card.name, "Capital Markets Macroeconomic Agent")
        self.assertEqual(len(card.skills), 5)

        async def run_task() -> object:
            task_request = TaskRequest(
                query="Please analyze NIFTY 50 and VIX",
                skills_required=["equity_market_analysis"]
            )
            ctx = RequestContext(task_id=task_request.task_id, request=task_request)
            q = EventQueue()
            return await executor.execute(ctx, q)

        task_res = asyncio.run(run_task())
        self.assertEqual(task_res.status, TaskStatus.COMPLETED)
        self.assertEqual(len(task_res.artifacts), 2)

    def test_fastapi_endpoints(self) -> None:
        app = create_app(self.client)
        tc = TestClient(app)

        resp = tc.get("/.well-known/agent.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Capital Markets Macroeconomic Agent")

        task_payload = {
            "query": "Check NIFTY 50 and VIX levels",
            "skills_required": ["equity_market_analysis", "volatility_analysis"]
        }
        resp = tc.post("/a2a/tasks", json=task_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "completed")

        mcp_req = {"jsonrpc": "2.0", "id": 9, "method": "tools/list"}
        resp = tc.post("/mcp", json=mcp_req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["result"]["tools"]), 5)


if __name__ == "__main__":
    unittest.main()
