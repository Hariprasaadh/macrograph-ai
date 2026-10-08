"""LangGraph Multi-Agent Macroeconomic Orchestrator Graph.

Orchestrates multi-agent research strictly through the standard A2A Protocol,
FastMCP tool servers, Knowledge Graph transmission paths, and Causal Simulation.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph

from ..protocols.a2a import agent_registry, trace_store
from ..protocols.a2a.messages import new_id
from ..protocols.a2a.router import route_query
from ..knowledge_graph.networkx_engine import graph_engine
from ..econometrics.causal_engine import causal_engine
from .llm_client import llm_client
from .state import OrchestratorState
from .a2a_dispatch import agents_for_sectors, aggregate, delegate, run_sync
from .registry_bootstrap import bootstrap_agent_registry  # noqa: F401  (registers agents on import)



# -----------------------------------------------------------------------------
# 1. Decomposition Node (capability routing over registered Agent Cards)
# -----------------------------------------------------------------------------
_ROUTER_SYSTEM_PROMPT = "You route macroeconomic questions to sector agents. Answer with a JSON array only."


async def _llm_complete(prompt: str) -> str:
    return await llm_client.complete(prompt, _ROUTER_SYSTEM_PROMPT, True)


def decompose_node(state: OrchestratorState) -> Dict[str, Any]:
    """Selects sector agents from their Agent Cards; the LLM is consulted only when no card matches."""
    query = state.get("query", "")
    decision = run_sync(route_query(query, agent_registry, _llm_complete))
    agent_ids = [c.agent_id for c in decision.choices]

    sectors: List[str] = []
    for agent_id in agent_ids:
        card = agent_registry.get_agent(agent_id)
        sector = card.metadata.get("sector") if card else None
        if sector and sector not in sectors:
            sectors.append(sector)

    return {
        "conversation_id": state.get("conversation_id") or new_id("conv"),
        "routed_agents": agent_ids,
        "routing_method": decision.method,
        "target_sectors": sectors,
        "decomposed_tasks": [
            {"agent_id": c.agent_id, "task": c.task, "matched": c.matched} for c in decision.choices
        ],
        "status": "decomposed",
    }


# -----------------------------------------------------------------------------
# 2. Parallel A2A Execution Node
# -----------------------------------------------------------------------------
async def parallel_a2a_execute_async(state: OrchestratorState) -> Dict[str, Any]:
    """Delegates to the routed agents over A2A and merges their validated, source-bearing responses."""
    query = state.get("query", "")
    agent_ids = state.get("routed_agents") or agents_for_sectors(state.get("target_sectors", []))
    if not agent_ids:
        agent_ids = [c.agent_id for c in (await route_query(query, agent_registry)).choices]
    conversation_id = state.get("conversation_id") or new_id("conv")

    responses = await delegate(query, agent_ids, conversation_id)
    merged = aggregate(responses)
    merged["conversation_id"] = conversation_id
    merged["a2a_trace"] = trace_store.get_trace(conversation_id)
    return merged


def parallel_a2a_execute_node(state: OrchestratorState) -> Dict[str, Any]:
    """Sync entry point for LangGraph.invoke()."""
    return run_sync(parallel_a2a_execute_async(state))


# Maximum indicator pairs explored in the KG per request. O(n^2) traversal
# becomes expensive above this bound; the most important indicators appear first.
_MAX_KG_INDICATOR_PAIRS = 20


# -----------------------------------------------------------------------------
# 3. Knowledge Graph & Causal Enrichment Node
# -----------------------------------------------------------------------------
def kg_causal_enrichment_node(state: OrchestratorState) -> Dict[str, Any]:
    """Traverses Knowledge Graph transmission paths and runs impulse response scenario simulations."""
    collected_obs = state.get("collected_observations", [])
    ind_ids = list(set([obs["indicator_id"] for obs in collected_obs]))
    scenario_shock = state.get("scenario_shock")

    # If scenario shock present, ensure shocked variable is included in graph exploration
    if scenario_shock and "variable" in scenario_shock:
        shock_var = scenario_shock["variable"]
        if shock_var not in ind_ids:
            ind_ids.append(shock_var)

    # Discover transmission paths in NetworkX Knowledge Graph.
    # Cap at _MAX_KG_INDICATOR_PAIRS to avoid O(n^2) PathFinder calls.
    causal_paths = []
    sampled = ind_ids[:10]  # first 10 keeps pairs <= 90, well inside limit
    pairs_checked = 0
    for u in sampled:
        for v in sampled:
            if u == v:
                continue
            if pairs_checked >= _MAX_KG_INDICATOR_PAIRS:
                break
            pairs_checked += 1
            path = graph_engine.get_shortest_transmission_path(u, v)
            if path:
                causal_paths.append({
                    "from": u,
                    "to": v,
                    "hops": len(path),
                    "total_lag_months": sum(r.transmission_lag_months for r in path),
                    "relations": [r.model_dump() for r in path],
                })
        else:
            continue
        break

    # Execute Scenario Simulation if shock provided
    scenario_result = None
    if scenario_shock:
        shock_var = scenario_shock.get("variable", "in.macro.prices.brent_crude")
        magnitude = float(scenario_shock.get("magnitude", 20.0))
        name = scenario_shock.get("name", "Simulated Macro Shock")
        res = causal_engine.simulate_scenario(scenario_name=name, shock_variable=shock_var, shock_magnitude=magnitude)
        scenario_result = res.model_dump()

    # Dynamic Mermaid diagram syntax
    mermaid_diag = graph_engine.generate_mermaid_diagram(focus_indicator_ids=ind_ids[:5] if ind_ids else None)

    return {
        "causal_paths": causal_paths,
        "scenario_result": scenario_result,
        "mermaid_diagram": mermaid_diag,
        "status": "enriched"
    }


_REPORT_EXCERPT_CHARS = 1500


# -----------------------------------------------------------------------------
# 4. Synthesis Node
# -----------------------------------------------------------------------------
def synthesis_node(state: OrchestratorState) -> Dict[str, Any]:
    """Synthesizes structured agent artifacts into an academic macroeconomic research report."""
    query = state.get("query", "")
    observations = state.get("collected_observations", [])
    causal_paths = state.get("causal_paths", [])
    scenario_res = state.get("scenario_result")
    mermaid_diag = state.get("mermaid_diagram", "")
    citations = state.get("citations", [])

    obs_summary = "\n".join([
        f"- {o['indicator_id']}: {o['value']} {o['unit']} (Period: {o['observation_period']}, Status: {o['data_status']})"
        for o in observations
    ])

    agent_reports = "\n\n".join(
        f"[{a['agent']}]\n{a['report_markdown'][:_REPORT_EXCERPT_CHARS]}"
        for a in state.get("agent_analyses", []) if a.get("report_markdown")
    )
    a2a_errors = state.get("a2a_errors", [])
    unavailable = "\n".join(f"- {e['agent']}: {e['code']} - {e['message']}" for e in a2a_errors)

    prompt = (
        f"Synthesize a rigorous Indian macroeconomic research report answering: '{query}'\n\n"
        f"Verified A2A Domain Observations:\n{obs_summary}\n\n"
        f"Knowledge Graph Causal Transmission Paths Mapped: {len(causal_paths)}\n"
    )
    if agent_reports:
        prompt += f"\nSector Agent Reports (A2A):\n{agent_reports}\n"
    if unavailable:
        prompt += (
            "\nSector agents that could not respond (state this explicitly; do not infer their data):\n"
            f"{unavailable}\n"
        )
    if scenario_res:
        prompt += f"\nScenario Simulation: {scenario_res.get('scenario_name')}\n"

    narrative_summary = llm_client.complete_sync(
        prompt=prompt,
        system_prompt="You are a senior Indian macroeconomic intelligence analyst. Provide rigorous, source-attributed, data-driven synthesis without hardcoding numbers.",
        use_reasoning_model=True,
    )

    report_lines = [
        "# Indian Macroeconomic Intelligence Report\n",
        f"**Research Query**: *{query}*\n",
        "## 1. Executive Synthesis\n",
        narrative_summary,
        "\n## 2. A2A Empirical Indicator Matrix & Cryptographic Provenance\n",
        "| Indicator | Value | Unit | Period | Data Status | Provenance Hash |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for c in citations:
        report_lines.append(
            f"| `{c['indicator_id']}` | **{c['value']}** | {c['unit']} | {c['period']} | `{c['data_status']}` | `{c.get('provenance_hash') or 'n/a'}` |"
        )

    report_lines.append("\n## 3. Cross-Sector Causal Transmission Channels\n")
    report_lines.append("```mermaid")
    report_lines.append(mermaid_diag)
    report_lines.append("```\n")

    if scenario_res:
        report_lines.append(f"## 4. Scenario Shock Simulation: {scenario_res.get('scenario_name')}\n")
        report_lines.append(f"- **Shocked Indicator**: `{scenario_res.get('shock_variable')}` (+{scenario_res.get('shock_magnitude')})\n")
        report_lines.append("| Target Indicator | Baseline | Shocked Peak | Impact (Delta) | Transmission Lag | Confidence Band |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for tid, impact in scenario_res.get("forecasted_impacts", {}).items():
            if tid != scenario_res.get("shock_variable"):
                report_lines.append(
                    f"| **{impact.get('indicator_name', tid)}** | {impact.get('baseline')} | **{impact.get('shocked_peak')}** | {impact.get('delta'):+0.2f} | {impact.get('transmission_lag_months')}M | {impact.get('confidence_band')} |"
                )


    if state.get("a2a_sources"):
        report_lines.append("\n## 5. A2A Source Provenance\n")
        report_lines.append("| Agent | Source | Dataset / Table | Period | Retrieved |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for src in state["a2a_sources"]:
            ref = " / ".join(x for x in (src.get("dataset"), src.get("table")) if x) or "n/a"
            report_lines.append(
                f"| {src['agent']} | {src['source_name']} | {ref} | "
                f"{src.get('reporting_period') or 'n/a'} | {src['retrieved_at']} |"
            )
    if a2a_errors:
        report_lines.append("\n### Unavailable Agent Data\n")
        report_lines.extend(f"- `{e['agent']}`: {e['code']} - {e['message']}" for e in a2a_errors)

    report_lines.append("\n## 6. Methodological & Causal Classification Notes\n")
    report_lines.append("- Multi-agent data dispatched strictly via standard A2A Protocol and FastMCP tool servers.")
    report_lines.append("- Transmission edges classified according to 5-tier taxonomy (THEORY -> STATISTICAL -> LAGGED -> GRANGER -> STRUCTURAL_CAUSAL_MODEL).")

    final_report = "\n".join(report_lines)

    available = sum(
        1 for o in observations if o.get("data_status") not in ("unavailable", "unspecified", None)
    )
    confidence_score = round(available / max(len(observations), 1), 2) if observations else 0.0

    return {
        "final_report": final_report,
        "confidence_score": confidence_score,
        "status": "completed",
    }


# -----------------------------------------------------------------------------
# Construct StateGraph
# -----------------------------------------------------------------------------
def build_orchestrator_graph() -> Any:
    builder = StateGraph(OrchestratorState)

    builder.add_node("decompose", decompose_node)
    builder.add_node(
        "parallel_a2a_execute",
        RunnableLambda(parallel_a2a_execute_node, afunc=parallel_a2a_execute_async),
    )
    builder.add_node("kg_causal_enrichment", kg_causal_enrichment_node)
    builder.add_node("synthesis", synthesis_node)

    builder.set_entry_point("decompose")
    builder.add_edge("decompose", "parallel_a2a_execute")
    builder.add_edge("parallel_a2a_execute", "kg_causal_enrichment")
    builder.add_edge("kg_causal_enrichment", "synthesis")
    builder.add_edge("synthesis", END)

    return builder.compile()


macro_orchestrator_graph = build_orchestrator_graph()
