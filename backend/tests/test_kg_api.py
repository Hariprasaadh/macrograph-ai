"""HTTP contracts for the knowledge graph, simulation and analyze endpoints."""
from __future__ import annotations

import importlib
import json

import pytest
from fastapi.testclient import TestClient

BRENT = "in.macro.prices.brent_crude"
GDP = "in.macro.real.gdp_growth"
CPI = "in.macro.prices.cpi_headline"
CREDIT = "in.macro.monetary.bank_credit_growth"


@pytest.fixture(scope="module")
def client():
    main = importlib.import_module("main")
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_reports_live_graph_counts(client):
    body = client.get("/health").json()
    assert body["knowledge_graph_nodes"] >= 20
    assert body["knowledge_graph_edges"] >= 12
    assert body["neo4j_enabled"] is False


def test_brent_to_gdp_path(client):
    body = client.get("/api/v1/kg/path", params={"source_id": BRENT, "target_id": GDP}).json()
    assert body["hops"] == 6
    assert body["total_lag_months"] == sum(r["transmission_lag_months"] for r in body["relationships"])
    assert body["relationships"][0]["target_indicator_id"] == "in.macro.prices.wpi_all"
    assert body["relationships"][-1]["target_indicator_id"] == GDP


def test_unknown_path_is_http_200_and_empty(client):
    res = client.get("/api/v1/kg/path", params={"source_id": "foo", "target_id": "bar"})
    assert res.status_code == 200
    assert res.json()["hops"] == 0 and res.json()["relationships"] == []


def test_impacts_and_unknown_impacts(client):
    body = client.get("/api/v1/kg/impacts", params={"shock_id": BRENT}).json()
    ids = {i["target_indicator_id"] for i in body["downstream_impacts"]}
    assert {CPI, "in.macro.monetary.repo_rate", "in.macro.external.usd_inr"} <= ids
    assert body["reachable_targets_count"] == len(body["downstream_impacts"])
    unknown = client.get("/api/v1/kg/impacts", params={"shock_id": "foo"})
    assert unknown.status_code == 200 and unknown.json()["reachable_targets_count"] == 0


def test_simulate_oil_surge(client):
    res = client.post("/api/v1/simulate", json={"scenario_name": "Oil Surge", "shock_variable": BRENT, "shock_magnitude": 20})
    body = res.json()
    assert res.status_code == 200
    assert body["forecasted_impacts"][CPI]["delta"] > 0
    assert body["forecasted_impacts"][CREDIT]["delta"] < 0
    assert body["provenance_chain"]


def test_analyze_returns_kg_enrichment(client, monkeypatch):
    main = importlib.import_module("main")
    llm = importlib.import_module("core.orchestrator.graph").llm_client
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "synthesis text")
    res = client.post("/api/v1/analyze", json={
        "query": "Impact of a crude oil price surge on inflation",
        "scenario_shock": {"variable": BRENT, "magnitude": 20.0, "name": "Oil Surge"},
    })
    assert res.status_code == 200
    body = res.json()
    for key in ("query", "status", "target_sectors", "collected_observations", "causal_paths",
                "scenario_result", "mermaid_diagram", "report_markdown", "confidence_score"):
        assert key in body
    assert body["scenario_result"]["scenario_name"] == "Oil Surge"
    assert "```mermaid" in body["report_markdown"]
    assert "5-tier taxonomy" in body["report_markdown"]
    assert main.app is not None


def test_chat_done_payload_includes_causal_fields(client, monkeypatch):
    chat_api = importlib.import_module("api.chat")

    class FakeGraph:
        def invoke(self, state):
            return {
                "final_report": "report", "collected_observations": [], "citations": [],
                "mermaid_diagram": "graph LR", "causal_paths": [{"from": "a", "to": "b"}],
                "scenario_result": {"scenario_name": "s"}, "target_sectors": [], "status": "completed",
            }

    monkeypatch.setattr(chat_api, "macro_orchestrator_graph", FakeGraph())
    with client.stream("POST", "/api/v1/chat/stream", json={"message": "macro outlook", "agent": "orchestrator"}) as res:
        events = [json.loads(line[6:]) for line in res.iter_lines() if line.startswith("data: ")]
    done = next(e for e in events if e["type"] == "done")
    assert done["causal_paths"] == [{"from": "a", "to": "b"}]
    assert done["scenario_result"] == {"scenario_name": "s"}
