---
name: knowledge-graph-agent
description: Workflows for traversing the Indian Macroeconomic Knowledge Graph using NetworkX and Neo4j, path discovery, latency summation, and Mermaid generation.
---

# Knowledge Graph Agent Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: No dummy indicator nodes, fictitious edges, or hardcoded weights may be introduced into the graph.
- **Grounding in Live Canonical Store**: All node metadata, current indicator values, and empirical edge weights must be synchronized with the live canonical data layer.
- **Explicit Error Handling**: If an indicator cannot be matched to the canonical ontology or path search fails due to isolated/unreachable nodes, the tool **must return an explicit, structured error** (`{"status": "error", "error_code": "PATH_NOT_FOUND", "message": "No valid transmission path discovered between <source> and <target>"}`).

## Domain Scope
Manages and queries the structural representation of the Indian macroeconomic system:
1. **Topological Path Traversal**: Finds the shortest transmission path between any two canonical indicator nodes.
2. **Cumulative Lag Calculation**: Sums empirical transmission lags across multi-hop paths (e.g. Brent Crude $\rightarrow$ WPI $\rightarrow$ CPI $\rightarrow$ Repo Rate $\rightarrow$ Bank Credit $\rightarrow$ Real GDP).
3. **Downstream Reachability & Impact Cascades**: Determines all indicators impacted downstream when a specific upstream variable undergoes a shock.
4. **Dynamic Mermaid Generation**: Synthesizes Mermaid diagram code for visual rendering in research reports and web dashboards.

## Core Python API
```python
from core.knowledge_graph.networkx_engine import graph_engine

# 1. Query shortest path
path = graph_engine.get_shortest_transmission_path(
    "in.macro.prices.brent_crude", 
    "in.macro.real.gdp_growth"
)
total_lag = sum(r.transmission_lag_months for r in path)

# 2. Get downstream impact cascade
impacts = graph_engine.get_downstream_impacts("in.macro.monetary.repo_rate")

# 3. Generate dynamic Mermaid syntax
mermaid_str = graph_engine.generate_mermaid_diagram(focus_indicator_ids=[...])
```

## REST API Endpoints
- `GET /api/v1/kg/path?source_id=...&target_id=...`: Shortest transmission path, hops, and cumulative lag.
- `GET /api/v1/kg/impacts?shock_id=...`: All reachable downstream indicators.
