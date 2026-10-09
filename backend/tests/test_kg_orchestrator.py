"""KG enrichment node, synthesis grounding and graph wiring."""
from __future__ import annotations

from core.orchestrator import graph as orchestrator_graph
from core.orchestrator.graph import kg_causal_enrichment_node, synthesis_node

BRENT = "in.macro.prices.brent_crude"
WPI = "in.macro.prices.wpi_all"
CPI = "in.macro.prices.cpi_headline"
REPO = "in.macro.monetary.repo_rate"


def obs(indicator_id: str, value: float = 1.0) -> dict:
    return {
        "indicator_id": indicator_id, "value": value, "unit": "%", "observation_period": "2025-01",
        "data_status": "live", "period": "2025-01", "provenance_hash": "abc",
    }


def test_kg_runs_after_a2a_and_before_synthesis():
    edges = {(e.source, e.target) for e in orchestrator_graph.macro_orchestrator_graph.get_graph().edges}
    assert ("parallel_a2a_execute", "kg_causal_enrichment") in edges
    assert ("kg_causal_enrichment", "synthesis") in edges
    assert ("parallel_a2a_execute", "synthesis") not in edges


def test_enrichment_finds_paths_without_scenario():
    out = kg_causal_enrichment_node({"collected_observations": [obs(BRENT), obs(CPI), obs(REPO)]})
    assert out["status"] == "enriched"
    assert out["scenario_result"] is None
    assert out["mermaid_diagram"].startswith("graph LR")
    pairs = {(p["from"], p["to"]) for p in out["causal_paths"]}
    assert (BRENT, CPI) in pairs and (CPI, REPO) in pairs and (BRENT, REPO) in pairs
    assert (REPO, BRENT) not in pairs
    brent_cpi = next(p for p in out["causal_paths"] if (p["from"], p["to"]) == (BRENT, CPI))
    assert brent_cpi["hops"] == 2 and brent_cpi["total_lag_months"] == 3
    assert all("relation_id" in r for r in brent_cpi["relations"])


def test_enrichment_is_deterministic_and_ignores_unknown_ids():
    state = {"collected_observations": [obs("in.macro.finance.something"), obs(BRENT), obs(BRENT), obs(WPI)]}
    first = kg_causal_enrichment_node(state)
    assert first == kg_causal_enrichment_node(state)
    assert [(p["from"], p["to"]) for p in first["causal_paths"]] == [(BRENT, WPI)]


def test_enrichment_tolerates_missing_indicator_id():
    out = kg_causal_enrichment_node({"collected_observations": [{"value": 1}, obs(BRENT)]})
    assert out["status"] == "enriched"


def test_scenario_shock_is_included_and_simulated():
    out = kg_causal_enrichment_node({
        "collected_observations": [obs(CPI)],
        "scenario_shock": {"variable": BRENT, "magnitude": 20.0, "name": "Oil Surge"},
    })
    assert out["scenario_result"]["scenario_name"] == "Oil Surge"
    assert out["scenario_result"]["provenance_chain"]
    assert any(p["from"] == BRENT and p["to"] == CPI for p in out["causal_paths"])


def test_synthesis_prompt_is_grounded_in_kg(monkeypatch):
    prompts = []
    monkeypatch.setattr(
        orchestrator_graph.llm_client, "complete",
        lambda prompt, *a, **k: prompts.append(prompt) or "synthesis text",
    )
    enriched = kg_causal_enrichment_node({
        "collected_observations": [obs(BRENT), obs(WPI)],
        "scenario_shock": {"variable": BRENT, "magnitude": 20.0},
    })
    state = {"query": "oil", "collected_observations": [obs(BRENT), obs(WPI)], "citations": [obs(BRENT)], **enriched}
    report = synthesis_node(state)["final_report"]
    relation_id = enriched["causal_paths"][0]["relations"][0]["relation_id"]
    assert relation_id in prompts[0]
    assert "Crude oil price surge passes directly" in prompts[0]
    assert "Documentary evidence: unavailable" in prompts[0]
    assert "```mermaid" in report and relation_id in report
    assert (
        "Transmission edges classified according to 5-tier taxonomy "
        "(THEORY -> STATISTICAL -> LAGGED -> GRANGER -> STRUCTURAL_CAUSAL_MODEL)."
    ) in report.splitlines()


def test_offline_fallback_uses_only_supplied_evidence(monkeypatch):
    unavailable = orchestrator_graph.llm_client._unavailable_notice()
    monkeypatch.setattr(orchestrator_graph.llm_client, "complete", lambda *a, **k: unavailable)
    enriched = kg_causal_enrichment_node({"collected_observations": [obs(BRENT), obs(WPI)]})
    report = synthesis_node({"query": "oil", "collected_observations": [obs(BRENT)], **enriched})["final_report"]
    assert "LLM Synthesis Unavailable" not in report
    assert "deterministic summary" in report
    assert "Observations retrieved from sector agents: 1." in report


def test_sector_native_ids_alias_onto_ontology():
    from core.orchestrator.canonical_ids import resolve_canonical_id

    assert resolve_canonical_id("in.macro.prices.cpi_headline_combined_yoy") == CPI
    assert resolve_canonical_id(REPO) == REPO
    assert resolve_canonical_id("in.macro.agri.mandi_price") == "in.macro.agri.mandi_price"
    assert resolve_canonical_id("in.macro.real.manufacturing_gva") == "in.macro.real.manufacturing_gva"


def test_live_observations_override_default_baselines():
    live_repo = obs(REPO, 5.25)
    unusable_cpi = {**obs(CPI, 9.99), "data_status": "unavailable"}
    out = kg_causal_enrichment_node({
        "collected_observations": [live_repo, unusable_cpi],
        "scenario_shock": {"variable": BRENT, "magnitude": 20.0},
    })
    impacts = out["scenario_result"]["forecasted_impacts"]
    assert impacts[REPO]["baseline"] == 5.25
    assert impacts[CPI]["baseline"] == 4.26
    assert out["live_baseline_ids"] == [REPO]
