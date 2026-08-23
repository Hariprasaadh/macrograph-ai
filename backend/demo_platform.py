import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.orchestrator.graph import macro_orchestrator_graph
from core.orchestrator.state import OrchestratorState
from core.knowledge_graph.networkx_engine import graph_engine
from core.econometrics.causal_engine import causal_engine
from core.protocols.a2a import agent_registry



def run_platform_demo() -> None:
    print("=" * 80)
    print(" MACROGRAPH AI — MULTI-AGENT INDIAN MACROECONOMIC INTELLIGENCE PLATFORM")
    print("=" * 80)

    # 1. Inspect A2A Agent Registry
    agents = agent_registry.list_agents()
    print(f"\n[1] Dynamic A2A Agent Registry ({len(agents)} Agents Discovered):")
    for a in agents:
        print(f"  • {a.name} (v{a.version}) -> {len(a.skills)} discoverable skills")

    # 2. Inspect Knowledge Graph Topology
    nodes_count = graph_engine.graph.number_of_nodes()
    edges_count = graph_engine.graph.number_of_edges()
    print(f"\n[2] Macroeconomic Knowledge Graph Topology:")
    print(f"  • Canonical Nodes: {nodes_count} | 5-Tier Causal Edges: {edges_count}")

    # 3. Query Shortest Transmission Path
    source = "in.macro.prices.brent_crude"
    target = "in.macro.real.gdp_growth"
    path = graph_engine.get_shortest_transmission_path(source, target)
    print(f"\n[3] Causal Transmission Path: [{source}] -> [{target}] ({len(path)} Hops):")
    for i, rel in enumerate(path, 1):
        print(f"  {i}. {rel.source_indicator_id} -> {rel.target_indicator_id} "
              f"[{rel.relation_type.value}] (Lag: {rel.transmission_lag_months}M, Elasticity: {rel.elasticity_sign})")

    # 4. Execute Multi-Agent Research Synthesis via LangGraph
    print("\n[4] Executing LangGraph Multi-Agent Research Workflow...")
    query = "Assess the impact of rising global crude prices on Indian CPI inflation, RBI repo rate policy, and corporate earnings."
    initial_state: OrchestratorState = {
        "query": query,
        "scenario_shock": {
            "name": "Global Brent Crude Oil Surge (+20 USD/barrel)",
            "variable": "in.macro.prices.brent_crude",
            "magnitude": 20.0
        }
    }

    result = macro_orchestrator_graph.invoke(initial_state)

    print("\n" + "=" * 80)
    print(" SYNTHESIZED MACROECONOMIC RESEARCH REPORT")
    print("=" * 80)
    print(result.get("final_report", ""))

    print("\n" + "=" * 80)
    print(" DYNAMIC TRANSMISSION MERMAID DIAGRAM")
    print("=" * 80)
    print(result.get("mermaid_diagram", ""))


if __name__ == "__main__":
    run_platform_demo()
