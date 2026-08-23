"""Tests for LangGraph Multi-Agent Orchestrator and Unified FastAPI Gateway."""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from main import app
from core.orchestrator.graph import macro_orchestrator_graph
from core.orchestrator.state import OrchestratorState


class LangGraphOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_check_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["sectors_active"], 8)
        self.assertGreater(data["knowledge_graph_nodes"], 0)

    def test_langgraph_orchestrator_workflow_execution(self) -> None:
        initial_state: OrchestratorState = {
            "query": "Assess the impact of rising global crude prices on Indian CPI inflation and RBI repo rate.",
            "scenario_shock": {
                "name": "Crude Oil Surge (+20 USD)",
                "variable": "in.macro.prices.brent_crude",
                "magnitude": 20.0
            }
        }
        final_state = macro_orchestrator_graph.invoke(initial_state)

        self.assertEqual(final_state["status"], "completed")
        self.assertIn("prices_inflation", final_state["target_sectors"])
        self.assertGreater(len(final_state["collected_observations"]), 0)
        self.assertGreater(len(final_state["causal_paths"]), 0)
        self.assertIsNotNone(final_state["scenario_result"])
        self.assertIn("graph LR", final_state["mermaid_diagram"])
        self.assertIn("# Indian Macroeconomic Intelligence Report", final_state["final_report"])

    def test_api_v1_analyze_endpoint(self) -> None:
        payload = {
            "query": "What is the relationship between GDP growth, bank credit, and inflation in India?",
            "scenario_shock": None
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertIn("report_markdown", data)
        self.assertIn("mermaid_diagram", data)

    def test_api_v1_simulate_endpoint(self) -> None:
        payload = {
            "scenario_name": "Monetary Tightening (+50 bps)",
            "shock_variable": "in.macro.monetary.repo_rate",
            "shock_magnitude": 0.50,
            "horizon_periods": 4
        }
        response = self.client.post("/api/v1/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["scenario_name"], "Monetary Tightening (+50 bps)")
        self.assertIn("forecasted_impacts", data)

    def test_api_v1_kg_path_endpoint(self) -> None:
        response = self.client.get(
            "/api/v1/kg/path?source_id=in.macro.prices.brent_crude&target_id=in.macro.monetary.repo_rate"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["hops"], 0)
        self.assertGreater(data["total_lag_months"], 0)


if __name__ == "__main__":
    unittest.main()
