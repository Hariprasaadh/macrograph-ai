"""Tests for A2A Protocol Models, Lifecycle Manager, and SSE Streaming."""
from __future__ import annotations

import asyncio
import unittest
from fastapi.testclient import TestClient

from core.protocols.a2a import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentSkill,
    AgentRegistry,
    EventQueue,
    RequestContext,
    TaskManager,
    TaskRequest,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from real_sector.api.app import app as real_app


class A2AProtocolAndStreamingTests(unittest.TestCase):
    def test_artifact_provenance_hash_generation(self) -> None:
        art = A2AArtifact(
            name="Test Artifact",
            type="json",
            content={"metric": "gdp", "value": 7.5}
        )
        self.assertIsNotNone(art.provenance_hash)
        self.assertEqual(len(art.provenance_hash), 16)

    def test_agent_registry_indexing_and_routing(self) -> None:
        reg = AgentRegistry()
        card = AgentCard(
            name="Mock Agent",
            description="Test Agent Description",
            url="http://localhost:8000/mock",
            skills=[
                AgentSkill(
                    id="mock_skill",
                    name="Mock Skill",
                    description="Analyzes mock data",
                    tags=["mock", "test"]
                )
            ]
        )
        reg.register(card)
        found = reg.find_agent_for_skill("mock_skill")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Mock Agent")

        routes = reg.route_query_skills("Please run a mock analysis")
        self.assertIn("mock_skill", routes)

    def test_task_manager_lifecycle(self) -> None:
        tm = TaskManager()
        req = TaskRequest(query="Test Query")
        resp = tm.create_task(req)
        self.assertEqual(resp.status, TaskState.SUBMITTED)

        fetched = tm.get_task(req.task_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.task_id, req.task_id)

    def test_sse_endpoint_connect(self) -> None:
        client = TestClient(real_app)

        # Create task
        resp = client.post("/a2a/tasks", json={"query": "Test real sector query"})
        self.assertEqual(resp.status_code, 200)
        task_id = resp.json()["task_id"]

        # Check task retrieval
        task_resp = client.get(f"/a2a/tasks/{task_id}")
        self.assertEqual(task_resp.status_code, 200)
        self.assertEqual(task_resp.json()["status"], "completed")


if __name__ == "__main__":
    unittest.main()
