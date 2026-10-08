"""UI-facing A2A surfaces: trace step events, done-payload summary, registry and SSE endpoint."""
from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.orchestrator.a2a_stream import a2a_summary, trace_step_events
from core.protocols.a2a.trace import trace_store


def _node(request_id: str, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "request_id": request_id, "parent_request_id": None, "sender_agent": "orchestrator",
        "receiver_agent": "monetary_sector", "task": "sector_analysis", "depth": 0,
        "started_at": "t", "status": status, "error_codes": [], "duration_ms": None, **extra,
    }


def test_new_node_emits_running_step_once():
    emitted: dict[str, str] = {}
    first = trace_step_events([_node("r1", "pending")], emitted, 2)
    assert [(e["step"], e["status"], e["request_id"]) for e in first] == [(2, "running", "r1")]
    assert trace_step_events([_node("r1", "pending")], emitted, 3) == []


def test_status_change_emits_update_for_same_request():
    emitted: dict[str, str] = {}
    trace_step_events([_node("r1", "pending")], emitted, 2)
    done = trace_step_events([_node("r1", "success", duration_ms=1500.0)], emitted, 3)
    assert done[0]["status"] == "completed" and done[0]["request_id"] == "r1"
    assert "1.5s" in done[0]["detail"]


def test_failure_surfaces_error_codes_and_partial_is_distinct():
    emitted: dict[str, str] = {}
    failed = trace_step_events([_node("r1", "failed", error_codes=["AGENT_TIMEOUT"])], emitted, 1)
    assert failed[0]["status"] == "failed" and "AGENT_TIMEOUT" in failed[0]["detail"]
    partial = trace_step_events([_node("r2", "partial")], emitted, 2)
    assert partial[0]["status"] == "partial"


def test_summary_defaults_are_safe_for_missing_state():
    summary = a2a_summary({})
    assert summary["routed_agents"] == [] and summary["errors"] == [] and summary["trace"] == []


@pytest.fixture(scope="module")
def client():
    import main
    return TestClient(main.app)


def test_registry_exposes_ids_tasks_and_declared_edges(client):
    body = client.get("/a2a/registry").json()
    ids = {a.get("agent_id") for a in body["agents"]}
    assert {"monetary_sector", "finance_sector", "fiscal_sector"} <= ids
    edges = {(d["consumer"], d["provider"], d["task"]) for d in body["dependencies"]}
    assert ("finance_sector", "monetary_sector", "repo_rate") in edges
    assert all(d["rationale"] for d in body["dependencies"])


def test_orchestrator_stream_reports_live_trace_and_a2a_summary(client, monkeypatch):
    import api.chat as chat_api
    from core.protocols.a2a.messages import A2ARequest

    class FakeGraph:
        def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
            conv = state["conversation_id"]
            request = A2ARequest(
                conversation_id=conv, sender_agent="orchestrator", receiver_agent="monetary_sector",
                task="sector_analysis",
            )
            trace_store.begin(request)
            time.sleep(0.6)
            return {
                "final_report": "Report body", "citations": [], "collected_observations": [],
                "target_sectors": ["monetary"], "conversation_id": conv,
                "routed_agents": ["monetary_sector"], "routing_method": "lexical",
                "a2a_errors": [], "a2a_trace": trace_store.get_trace(conv), "status": "a2a_completed",
            }

    monkeypatch.setattr(chat_api, "macro_orchestrator_graph", FakeGraph())
    events = []
    with client.stream("POST", "/api/v1/chat/stream", json={"message": "repo rate outlook", "agent": "orchestrator"}) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    steps = [e for e in events if e["type"] == "step"]
    assert any(s.get("request_id") and s["status"] == "running" for s in steps)
    done = events[-1]
    assert done["type"] == "done"
    assert done["a2a"]["routed_agents"] == ["monetary_sector"]
    assert done["a2a"]["trace"][0]["receiver_agent"] == "monetary_sector"
    assert done["confidence_score"] is None


def test_orchestrator_stream_survives_graph_failure(client, monkeypatch):
    import api.chat as chat_api

    class BrokenGraph:
        def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("graph exploded with secret detail")

    monkeypatch.setattr(chat_api, "macro_orchestrator_graph", BrokenGraph())
    events = []
    with client.stream("POST", "/api/v1/chat/stream", json={"message": "repo rate", "agent": "orchestrator"}) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    done = events[-1]
    assert done["type"] == "done" and done["status"] == "failed"
    assert "secret detail" not in json.dumps(done)
    assert done["a2a"]["conversation_id"]
