from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from real_sector.agents.executor import RealSectorAgentExecutor
from real_sector.agents.tools import SectorToolRegistry
from real_sector.api.app import create_app
from real_sector.config import DEFAULT_DATA_DIR
from real_sector.protocols.a2a_protocol import EventQueue, RequestContext, TaskRequest, TaskStatus
from real_sector.protocols.mcp_protocol import handle_mcp_rpc
from real_sector.services.pipeline import RealSectorPipeline


class RealSectorPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = RealSectorPipeline(DEFAULT_DATA_DIR)
        cls.tables = cls.pipeline.refresh(persist=False)

    def test_all_available_source_areas_are_ingested(self) -> None:
        self.assertGreater(len(self.tables["agri_production"]), 0)
        self.assertGreater(len(self.tables["industry_iip"]), 0)
        self.assertGreater(len(self.tables["gdp_quarterly"]), 0)
        self.assertGreater(len(self.tables["cpi_combined"]), 0)
        self.assertGreater(len(self.tables["wpi_monthly"]), 0)

    def test_each_sector_is_exposed_as_a_separate_llm_tool(self) -> None:
        registry = SectorToolRegistry(self.pipeline)
        names = {item["function"]["name"] for item in registry.openai_functions()}
        self.assertEqual(names, {"get_agriculture_snapshot", "get_industry_snapshot", "get_national_income_snapshot", "get_prices_snapshot"})
        for name in names:
            response = registry.invoke(name)
            self.assertEqual(response.agent, name.removeprefix("get_").removesuffix("_snapshot"))

    def test_mcp_tools_schema_export_and_rpc(self) -> None:
        registry = SectorToolRegistry(self.pipeline)
        mcp_tools = registry.mcp_tools()
        self.assertEqual(len(mcp_tools), 4)
        tool_names = {t.name for t in mcp_tools}
        self.assertEqual(tool_names, {"get_agriculture_snapshot", "get_industry_snapshot", "get_national_income_snapshot", "get_prices_snapshot"})

        # Test JSON-RPC tools/list
        list_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        list_resp = handle_mcp_rpc(list_req, registry)
        self.assertEqual(list_resp["id"], 1)
        self.assertIn("tools", list_resp["result"])
        self.assertEqual(len(list_resp["result"]["tools"]), 4)

        # Test JSON-RPC tools/call
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_national_income_snapshot", "arguments": {}}
        }
        call_resp = handle_mcp_rpc(call_req, registry)
        self.assertEqual(call_resp["id"], 2)
        self.assertFalse(call_resp["result"]["isError"])
        self.assertIn("national_income", call_resp["result"]["content"][0]["text"])

    def test_a2a_agent_card_and_executor(self) -> None:
        executor = RealSectorAgentExecutor(self.pipeline)
        card = executor.get_agent_card()
        self.assertEqual(card.name, "Real Sector Macroeconomic Agent")
        self.assertGreaterEqual(len(card.skills), 5)

        # Test Async Execution
        async def run_task():
            req = TaskRequest(
                query="Provide a comprehensive real sector macroeconomic report",
                skills_required=["real_sector_comprehensive_synthesis"]
            )
            context = RequestContext(task_id=req.task_id, request=req)
            queue = EventQueue()
            resp = await executor.execute(context, queue)
            return resp

        resp = asyncio.run(run_task())
        self.assertEqual(resp.status, TaskStatus.COMPLETED)
        self.assertEqual(len(resp.artifacts), 2)
        artifact_types = {art.type for art in resp.artifacts}
        self.assertEqual(artifact_types, {"json", "markdown"})

    def test_fastapi_a2a_and_mcp_endpoints(self) -> None:
        app = create_app(self.pipeline)
        client = TestClient(app)

        # Test Agent Card discovery
        resp = client.get("/.well-known/agent.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Real Sector Macroeconomic Agent")

        # Test A2A Task creation
        task_payload = {
            "query": "What is current GDP and inflation?",
            "skills_required": ["national_income_analysis", "price_inflation_analysis"]
        }
        resp = client.post("/a2a/tasks", json=task_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(len(data["artifacts"]), 2)
        task_id = data["task_id"]

        # Test Task retrieval
        resp = client.get(f"/a2a/tasks/{task_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["task_id"], task_id)

        # Test MCP RPC endpoint
        mcp_payload = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}
        resp = client.post("/mcp", json=mcp_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["result"]["tools"]), 4)


if __name__ == "__main__":
    unittest.main()
