# KNOWLEDGE GRAPH — Implementation Instructions for a Coding/Reasoning Agent

> **Purpose:** This document is the execution-level specification for implementing the macroeconomic Knowledge Graph (KG) and wiring it into the existing MacroGraph platform.
>
> **Authority:** This document is the implementation source of truth for the KG work.
>
> **Conceptual prerequisite:** Read `KNOWLEDGE_GRAPH_CAUSAL_GRAPHRAG_EXPLAINED.md` first if it exists in the repository. That document explains concepts. **This document controls implementation details, interfaces, formulas, file boundaries, and acceptance criteria.**
>
> **Agent directive:** Implement the requested functionality directly. Do not ask the user to choose between alternatives. Do not redesign the architecture. Do not replace fixed decisions with personally preferred patterns.

---

# 1. Mission

Build and wire a deterministic macroeconomic Knowledge Graph that provides four capabilities:

1. **Causal retrieval**
   - Find transmission paths between canonical macroeconomic indicators.
   - Retrieve upstream/downstream causal neighborhoods.
   - Retrieve downstream shock impacts.

2. **Shock propagation**
   - Simulate a macroeconomic shock over the causal graph.
   - Propagate sign, confidence, and lag deterministically.
   - Produce explainable forecast deltas and confidence bands.

3. **Explainability**
   - Return the exact traversed `relation_id`s.
   - Preserve mechanisms for every traversed relationship.
   - Generate Mermaid causal diagrams.

4. **GraphRAG enrichment**
   - Enrich the existing multi-agent macroeconomic analysis pipeline with KG structure.
   - Fuse numeric observations, causal structure, and documentary evidence without inventing unsupported claims.

The KG is **not** a replacement for the existing sector agents, FastMCP data retrieval, DuckDB fact store, Qdrant text store, or A2A communication.

---

# 2. Highest-Priority Non-Negotiable Rules

These rules override implementation convenience.

## 2.1 File boundary

Only create or modify the files explicitly listed in Section 6.

If an existing implementation requires a change outside those files:

- do **not** silently modify the extra file;
- first determine whether the requested functionality can be implemented within the allowed files;
- if it genuinely cannot, stop that portion rather than redesigning the repository.

Do not create helper files, alternate implementations, migration files, scripts, or additional packages unless explicitly authorized.

## 2.2 Fixed technology stack

Use:

- Python 3.12
- Pydantic v2
- NetworkX 3.x
- `networkx.MultiDiGraph`
- statsmodels
- FastAPI
- LangGraph
- existing repository configuration/dependency management

Do not introduce another graph library.

Forbidden graph libraries include:

- igraph
- graph-tool
- rustworkx
- Neo4j as the hot-path replacement for NetworkX
- custom graph implementations replacing NetworkX

## 2.3 One canonical ontology

There must be exactly one canonical ontology object:

```python
ontology
```

The ontology is the source of truth for:

- indicators
- causal relationships
- node metadata
- edge metadata

NetworkX is constructed from that ontology.

Neo4j is synchronized from that ontology.

Never independently redefine the same nodes or relationships in NetworkX and Neo4j.

## 2.4 Storage responsibilities

Keep responsibilities strictly separated:

| Component | Responsibility |
|---|---|
| Ontology | Canonical indicator and causal relationship definitions |
| NetworkX | In-memory causal traversal and graph reasoning |
| Neo4j | Optional persistent mirror |
| DuckDB | Numeric/time-series facts |
| FastMCP | Sector-owned live/current data retrieval |
| Qdrant | Documentary/text evidence |
| A2A | Peer-agent reasoning/conclusion exchange |
| LangGraph | Analysis workflow orchestration |

The KG must not become a second fact store or document store.

## 2.5 Query failure behavior

Graph query methods must be defensive.

Missing:

- source node
- target node
- path
- Neo4j configuration
- optional Qdrant evidence

must not crash the analysis workflow.

For graph retrieval:

- return `[]` where a list is expected;
- return the required empty dictionary shape where a dictionary is expected;
- API endpoints return HTTP 200 for unknown graph indicators unless an explicitly documented unexpected server error occurs.

## 2.6 Causal claims require provenance

Every generated economic causal claim must be traceable to traversed relationships.

The implementation must preserve:

```text
relation_id
```

for traversed edges.

Do not create causal prose that cannot be traced to the graph path or to explicitly supplied documentary evidence.

## 2.7 Exact identifiers are contractual

Do not rename:

- indicator IDs
- relation IDs
- Pydantic fields
- endpoint paths
- function signatures
- taxonomy values
- simulation constants
- response keys

unless this specification is explicitly changed.

---

# 3. Fixed Architecture

## 3.1 In-memory graph

Use:

```python
networkx.MultiDiGraph
```

Reason:

- fast in-memory traversal;
- supports multiple causal relationships between the same pair of indicators;
- no external server dependency for normal API/orchestrator execution.

NetworkX is the **hot-path query engine**.

## 3.2 Neo4j

Neo4j is optional.

It is enabled only when:

```text
NEO4J_URI
```

is configured.

Neo4j is a **persistent mirror**, not the orchestrator's primary query path.

Synchronization direction:

```text
ontology -> Neo4j
```

Never:

```text
Neo4j -> ontology
```

Never permit ad-hoc writes to Neo4j outside the synchronization method.

The application must start normally when Neo4j is unavailable or unconfigured.

## 3.3 Numeric data

Numeric/time-series data remains in DuckDB and/or sector-owned MCP retrieval.

The KG stores:

- structure
- causal relationships
- lag
- sign
- confidence
- mechanism
- assumptions

The KG does **not** store complete time series.

The only numeric values allowed inside the KG simulation implementation are the explicitly specified simulation baselines and computed scenario values.

## 3.4 Text evidence

Qdrant remains the documentary evidence store.

Examples:

- MPC minutes
- Budget speech
- Economic Survey
- policy documents
- other existing documentary sources

The KG does not store document chunks.

GraphRAG combines graph structure and Qdrant evidence at synthesis time.

## 3.5 Pathfinding

Pathfinding is strictly **unweighted hop-based BFS**.

Use:

```python
nx.shortest_path(...)
```

Do not use:

```python
nx.dijkstra_path(...)
```

Do not weight pathfinding by confidence.

Confidence is used after path selection for:

- ranking;
- attenuation;
- confidence reporting.

Path semantics are:

> shortest = fewest causal transmission hops.

## 3.6 Path aggregation

For a selected path:

```text
total_lag = sum(per-hop lag)
```

and:

```text
cumulative_confidence = product(per-hop confidence)
```

No alternative aggregation is permitted.

---

# 4. How the Coding Agent Must Reason Before Editing

Before writing code, inspect the existing repository implementation.

## 4.1 Inspect first

Determine:

1. whether the target files already exist;
2. the existing `backend/core/data/schema.py`;
3. existing Pydantic conventions;
4. existing configuration/settings access;
5. existing LangGraph state definition;
6. existing orchestrator nodes;
7. existing `/health` endpoint;
8. existing `/api/v1/analyze` endpoint;
9. existing A2A execution node;
10. existing synthesis node;
11. existing `main.py` application construction;
12. existing dependency versions;
13. existing Neo4j usage, if any;
14. existing tests and test conventions.

## 4.2 Preserve existing behavior

When target files already contain working functionality:

- preserve unrelated functionality;
- add the KG functionality;
- do not rewrite unrelated sector-agent code;
- do not change existing API behavior unless this specification explicitly requires it.

## 4.3 Resolve conflicts using this priority order

If repository code and this specification appear inconsistent:

1. explicit requirements in this document;
2. existing interfaces that this document explicitly says must remain;
3. existing project conventions needed to make the specified implementation run;
4. otherwise preserve existing code.

Do not invent an architectural compromise.

## 4.4 Do not infer missing economics

If an indicator or relationship is not specified:

- do not invent an economic relationship;
- do not invent a baseline;
- do not invent a source;
- do not invent a confidence score;
- do not invent a mechanism.

Only append new ontology data when explicitly authorized by the task.

---

# 5. Exact File Layout

Implement exactly these files:

```text
backend/core/data/schema.py
backend/core/knowledge_graph/ontology.py
backend/core/knowledge_graph/networkx_engine.py
backend/core/knowledge_graph/neo4j_store.py
backend/core/knowledge_graph/__init__.py
backend/core/econometrics/causal_engine.py
backend/core/orchestrator/graph.py
backend/main.py
backend/demo_platform.py
```

Responsibilities:

| File | Responsibility |
|---|---|
| `schema.py` | Canonical Pydantic models and causal taxonomy |
| `ontology.py` | Single canonical KG definition and singleton |
| `networkx_engine.py` | In-memory graph construction and traversal |
| `neo4j_store.py` | Optional ontology-to-Neo4j mirror |
| `knowledge_graph/__init__.py` | Public KG re-exports |
| `causal_engine.py` | Granger testing and deterministic shock simulation |
| `orchestrator/graph.py` | KG enrichment node and LangGraph wiring |
| `main.py` | KG/API integration |
| `demo_platform.py` | Startup graph-count demonstration |

---

# 6. Data Contracts

## 6.1 SectorEnum

Use exactly these values:

```text
real_economy
prices_inflation
monetary_banking
fiscal
external
capital_markets
agriculture_rural
labour_employment
```

When stored on NetworkX nodes, use:

```python
sector.value
```

not the enum representation.

---

# 7. Causal Relation Taxonomy

Use exactly these five tiers and preserve this order:

```python
THEORY = "THEORY"
STATISTICAL_ASSOCIATION = "STATISTICAL_ASSOCIATION"
LAGGED_RELATIONSHIP = "LAGGED_RELATIONSHIP"
GRANGER_PREDICTIVE = "GRANGER_PREDICTIVE"
STRUCTURAL_CAUSAL_MODEL = "STRUCTURAL_CAUSAL_MODEL"
```

## 7.1 Classification rules

Assign relationship type exactly as follows:

| Evidence | Type |
|---|---|
| Textbook/economic theory only | `THEORY` |
| Correlation + p-value, no lag | `STATISTICAL_ASSOCIATION` |
| Cross-correlation at lag `k` | `LAGGED_RELATIONSHIP` |
| Granger test p-value `< 0.05` | `GRANGER_PREDICTIVE` |
| Explicit mandate/accounting identity with stated assumptions | `STRUCTURAL_CAUSAL_MODEL` |

Do not promote or demote a relationship merely because another type seems more sophisticated.

Important distinction:

> `GRANGER_PREDICTIVE` means predictive precedence in the specified statistical test. It must not be described as proof of structural causality.

---

# 8. CanonicalIndicator Model

Implement the exact fields:

```python
indicator_id: str
name: str
sector: SectorEnum
subsector: Optional[str]
unit: str
frequency: str
source_authority: str
source_url: Optional[str] = None
description: Optional[str] = None
```

## 8.1 ID validation

`indicator_id` must match:

```regex
^in\.macro\.[a-z_]+\.[a-z_0-9]+$
```

Examples:

```text
in.macro.prices.cpi_headline
in.macro.real.gdp_growth
in.macro.capmarkets.nifty_50
```

Reject invalid IDs.

## 8.2 Frequency validation

Frequency must be one of:

```text
daily
weekly
fortnightly
monthly
quarterly
annual
seasonal
policy_cycle
```

Do not silently normalize arbitrary frequency strings.

---

# 9. CausalRelationship Model

Implement:

```python
relation_id: str = "rel-<8 hex>"
source_indicator_id: str
target_indicator_id: str
relation_type: CausalRelationType
transmission_lag_months: int >= 0
elasticity_sign: str
empirical_p_value: Optional[float]
confidence_score: float in [0.0, 1.0]
mechanism_description: str
documented_assumptions: List[str]
```

## 9.1 Relation ID

If omitted, generate:

```python
f"rel-{uuid4().hex[:8]}"
```

Do not generate sequential IDs.

## 9.2 Sign

Only:

```text
+
-
```

are valid.

Never use:

```text
ambiguous
unknown
positive
negative
```

in this field.

## 9.3 P-value

`empirical_p_value` may be:

- a float for statistical/empirical relationships;
- `None` only for `THEORY`.

## 9.4 Confidence

Must satisfy:

```text
0.0 <= confidence_score <= 1.0
```

Default unknown confidence:

```text
0.8
```

Curated priors should remain in the specified range:

```text
0.82–0.98
```

## 9.5 Mechanism

Required.

Minimum length:

```text
10 characters
```

It must describe the economic transmission mechanism in plain language.

## 9.6 Assumptions

Required.

At least one explicit assumption is required.

The assumptions define the identification/interpretation boundary of the relationship.

---

# 10. Ontology Validation

`ontology._build_ontology()` must reject:

- self-loops;
- unknown source indicators;
- unknown target indicators;
- empty mechanism descriptions;
- empty assumptions;
- confidence outside `[0,1]`;
- negative lag;
- invalid indicator IDs;
- invalid relation signs.

Target must not equal source.

All relationship endpoints must exist before the relationship enters the graph.

The ontology must be internally valid before the NetworkX graph is built.

---

# 11. Fixed Seed Ontology

Seed exactly these 20 indicators.

Do not alter their IDs.

```text
in.macro.real.gdp_growth
in.macro.real.iip_growth
in.macro.real.gfcf_investment
in.macro.prices.cpi_headline
in.macro.prices.cpi_food
in.macro.prices.wpi_all
in.macro.prices.brent_crude
in.macro.monetary.repo_rate
in.macro.monetary.bank_credit_growth
in.macro.fiscal.debt_to_gdp
in.macro.fiscal.central_capex
in.macro.external.forex_reserves
in.macro.external.usd_inr
in.macro.external.trade_balance
in.macro.capmarkets.nifty_50
in.macro.capmarkets.bank_nifty
in.macro.capmarkets.india_vix
in.macro.agri.monsoon_departure
in.macro.agri.foodgrain_production
in.macro.labour.epfo_additions
```

Use the following exact metadata:

```text
in.macro.real.gdp_growth | Quarterly Real GDP Growth Rate | real_economy | % YoY | quarterly | MoSPI
in.macro.real.iip_growth | Index of Industrial Production Growth | real_economy | % YoY | monthly | MoSPI
in.macro.real.gfcf_investment | Gross Fixed Capital Formation | real_economy | % of GDP | quarterly | MoSPI
in.macro.prices.cpi_headline | All India CPI Combined Headline Inflation | prices_inflation | % YoY | monthly | MoSPI
in.macro.prices.cpi_food | Consumer Food Price Index Inflation | prices_inflation | % YoY | monthly | MoSPI
in.macro.prices.wpi_all | Wholesale Price Index All Commodities | prices_inflation | % YoY | monthly | Office of Economic Adviser
in.macro.prices.brent_crude | Brent Crude Oil Benchmark Price | prices_inflation | USD/barrel | daily | EIA / Markets
in.macro.monetary.repo_rate | RBI Policy Repo Rate | monetary_banking | % p.a. | policy_cycle | RBI
in.macro.monetary.bank_credit_growth | Bank Credit Growth | monetary_banking | % YoY | fortnightly | RBI
in.macro.fiscal.debt_to_gdp | General Government Debt to GDP Ratio | fiscal | % of GDP | annual | IMF
in.macro.fiscal.central_capex | Central Government Capital Expenditure | fiscal | INR Crore | monthly | CGA / MoF
in.macro.external.forex_reserves | Foreign Exchange Reserves of India | external | Billion USD | weekly | RBI
in.macro.external.usd_inr | USD/INR Exchange Rate | external | INR/USD | daily | RBI / Markets
in.macro.external.trade_balance | Merchandise Trade Balance | external | Billion USD | monthly | Ministry of Commerce
in.macro.capmarkets.nifty_50 | NIFTY 50 Benchmark Index | capital_markets | points | daily | NSE
in.macro.capmarkets.bank_nifty | NIFTY Bank Index | capital_markets | points | daily | NSE
in.macro.capmarkets.india_vix | India VIX Volatility Index | capital_markets | points | daily | NSE
in.macro.agri.monsoon_departure | Southwest Monsoon LPA Rainfall Departure | agriculture_rural | % departure | seasonal | IMD
in.macro.agri.foodgrain_production | Foodgrain Production Volume | agriculture_rural | Million Tonnes | annual | Ministry of Agriculture
in.macro.labour.epfo_additions | EPFO Monthly Net Payroll Additions | labour_employment | Count (Thousands) | monthly | EPFO / MoSPI
```

Seed exactly these 12 relationships:

```text
brent_crude -> wpi_all | LAGGED_RELATIONSHIP | 1 | + | 0.001 | 0.95 | Crude surge passes into fuel and manufacturing input costs.
wpi_all -> cpi_headline | GRANGER_PREDICTIVE | 2 | + | 0.008 | 0.90 | Producer prices filter downstream into retail CPI basket.
cpi_headline -> repo_rate | STRUCTURAL_CAUSAL_MODEL | 1 | + | 0.002 | 0.95 | RBI MPC hikes repo when CPI breaches 4% midpoint target.
repo_rate -> bank_credit_growth | GRANGER_PREDICTIVE | 3 | - | 0.015 | 0.88 | Higher repo raises MCLR/EBLR, dampening loan demand.
bank_credit_growth -> iip_growth | STATISTICAL_ASSOCIATION | 2 | + | 0.025 | 0.82 | Credit finances industrial inventory and working capital.
iip_growth -> gdp_growth | STRUCTURAL_CAUSAL_MODEL | 1 | + | 0.001 | 0.98 | IIP is direct supply-side input to GVA/GDP.
brent_crude -> trade_balance | THEORY | 1 | - | 0.004 | 0.92 | India imports ~85% crude; higher prices widen trade deficit.
trade_balance -> usd_inr | STATISTICAL_ASSOCIATION | 1 | + | 0.010 | 0.86 | Wider deficit raises USD demand, depreciating INR.
repo_rate -> bank_nifty | LAGGED_RELATIONSHIP | 1 | - | 0.020 | 0.85 | Tightening compresses NIMs and raises discount rates.
central_capex -> gfcf_investment | THEORY | 2 | + | 0.005 | 0.90 | Public capex crowds in private fixed capital formation.
monsoon_departure -> foodgrain_production | THEORY | 3 | + | 0.003 | 0.92 | Adequate rainfall raises sown area and Kharif yields.
foodgrain_production -> cpi_food | STATISTICAL_ASSOCIATION | 2 | - | 0.012 | 0.89 | Higher output builds buffer stocks, stabilizing food prices.
```

Each edge must contain at least one `documented_assumptions` string from the existing `ontology.py` if such assumptions already exist there. Preserve those strings verbatim when the repository already provides them.

**Do not fabricate missing assumption text.**

---

# 12. NetworkX Engine

File:

```text
backend/core/knowledge_graph/networkx_engine.py
```

Class:

```python
NetworkXGraphEngine
```

Singleton:

```python
graph_engine = NetworkXGraphEngine()
```

## 12.1 Graph type

Use only:

```python
nx.MultiDiGraph()
```

## 12.2 Build behavior

`_build_graph()` must:

1. call `self.graph.clear()`;
2. add every ontology indicator as a node;
3. add every ontology relationship as an edge.

Node attributes:

```text
name
sector
subsector
unit
frequency
source_authority
```

Edge attributes:

```text
relation
relation_type
lag_months
elasticity
confidence
mechanism
```

Edge key:

```python
rel.relation_id
```

Do not store time-series data or document text.

---

# 13. NetworkX Retrieval Contracts

## 13.1 Shortest transmission path

Signature:

```python
get_shortest_transmission_path(
    source_id: str,
    target_id: str
) -> List[CausalRelationship]
```

Algorithm:

1. If source missing: return `[]`.
2. If target missing: return `[]`.
3. Call `nx.shortest_path`.
4. Catch:
   - `NetworkXNoPath`
   - `NodeNotFound`
5. For every consecutive `(u, v)`:
   - obtain `graph.get_edge_data(u, v)`;
   - choose the parallel edge with maximum `confidence`;
   - append its `relation`.
6. Preserve path order.
7. Do not sort the relationships afterward.
8. Do not filter by confidence.
9. Do not replace BFS with weighted pathfinding.

### Parallel-edge decision

If multiple causal relationships connect the same source and target:

> For path materialization, select the highest-confidence relationship for that hop.

This does not change the graph itself.

---

# 14. Causal Neighborhood

Signature:

```python
get_causal_neighborhood(
    indicator_id: str,
    depth: int = 2
) -> dict
```

For an unknown indicator return:

```python
{
    "indicator_id": indicator_id,
    "upstream": [],
    "downstream": [],
    "upstream_drivers": [],
    "downstream_impacts": []
}
```

For a known indicator:

- `upstream` = predecessor relationships;
- `downstream` = successor relationships.

Relationship objects must be serialized with:

```python
relation.model_dump()
```

The `depth` parameter is accepted for compatibility.

Required current behavior is **one-hop**.

Do not silently implement recursive k-hop traversal.

---

# 15. Downstream Shock Fan-Out

Signature:

```python
get_downstream_impacts(
    shock_indicator_id: str
) -> List[dict]
```

Algorithm:

1. Unknown node -> `[]`.
2. Get:
   ```python
   nx.descendants(graph, shock_indicator_id)
   ```
3. For every reachable target:
   - retrieve the shortest transmission path;
   - skip if no path.
4. Calculate:
   ```python
   total_lag = sum(r.transmission_lag_months for r in path)
   ```
5. Calculate:
   ```python
   cumulative_confidence = product(r.confidence_score for r in path)
   ```
6. Round cumulative confidence to 2 decimals in the output.
7. Emit exactly:
   ```text
   target_indicator_id
   target_name
   sector
   path_length_hops
   total_lag_months
   cumulative_confidence
   transmission_chain
   ```
8. `transmission_chain` contains mechanism descriptions in path order.
9. Sort only by:
   ```text
   path_length_hops ascending
   cumulative_confidence descending
   ```

Do not introduce additional ranking criteria.

---

# 16. Mermaid Renderer

Signature:

```python
generate_mermaid_diagram(
    focus_indicator_ids: Optional[List[str]] = None
) -> str
```

The output starts exactly with:

```text
graph LR
```

Node form:

```text
<clean_id>["<Human Name>"]
```

Edge form:

```text
<clean_src> -->|"+ (1M) [LAGGED_RELATIONSHIP]"| <clean_dst>
```

Cleaning rule:

```python
raw.replace(".", "_").replace("-", "_")
```

Escape `"` in names by replacing it with `'`.

## 16.1 Focus behavior

If `focus_indicator_ids` is provided:

- include those indicators;
- include their one-hop predecessors;
- include their one-hop successors;
- include only edges where both endpoints belong to the resulting set.

If no focus is provided:

- render the full graph.

Do not render arbitrary unrelated nodes when focus mode is active.

---

# 17. Econometric Engine

File:

```text
backend/core/econometrics/causal_engine.py
```

Class:

```python
CausalEconometricEngine
```

Singleton:

```python
causal_engine
```

It holds:

```python
self.graph = graph_engine
```

---

# 18. Granger Causality

Signature:

```python
test_granger_causality(
    data: pd.DataFrame,
    cause_col: str,
    effect_col: str,
    max_lag: int = 2
) -> dict
```

## 18.1 Missing columns

Return exactly:

```python
{
    "is_significant": False,
    "p_value": None,
    "optimal_lag": None,
    "error": "Columns not found"
}
```

## 18.2 Sample size

Create:

```python
subset = data[[effect_col, cause_col]].dropna()
```

The effect column must be first because statsmodels expects:

```text
[y, x]
```

If:

```python
len(subset) < 10
```

return an insufficient-sample result with:

```text
Insufficient sample size (N < 10)
```

## 18.3 Test

Use:

```python
grangercausalitytests(
    subset,
    maxlag=max_lag,
    verbose=False
)
```

For each lag:

```python
lag_res[0]["ssr_ftest"][1]
```

is the p-value.

Select the minimum p-value and corresponding lag.

Return:

```python
{
    "cause": cause_col,
    "effect": effect_col,
    "optimal_lag": best_lag,
    "p_value": round(min_p, 4),
    "is_significant": min_p < 0.05
}
```

Wrap the test in `try/except`.

On exception:

```python
{
    "cause": cause_col,
    "effect": effect_col,
    "optimal_lag": None,
    "p_value": None,
    "is_significant": False,
    "error": str(err)
}
```

Do not:

- auto-select lag using AIC;
- substitute another statistical test;
- change the significance threshold;
- interpret Granger significance as proof of structural causality.

---

# 19. Shock Simulation

Signature:

```python
simulate_scenario(
    scenario_name: str,
    shock_variable: str,
    shock_magnitude: float,
    horizon_periods: int = 4,
    baseline_values: Optional[Dict[str, float]] = None
) -> ScenarioResult
```

## 19.1 Fixed baselines

When `baseline_values is None`, use exactly:

```python
{
    "in.macro.prices.brent_crude": 78.50,
    "in.macro.prices.wpi_all": 2.45,
    "in.macro.prices.cpi_headline": 4.26,
    "in.macro.monetary.repo_rate": 6.25,
    "in.macro.monetary.bank_credit_growth": 13.80,
    "in.macro.real.iip_growth": 4.20,
    "in.macro.real.gdp_growth": 5.40,
    "in.macro.external.trade_balance": -22.50,
    "in.macro.external.usd_inr": 86.40,
    "in.macro.capmarkets.bank_nifty": 51500.0,
    "in.macro.agri.monsoon_departure": 0.0,
    "in.macro.agri.foodgrain_production": 328.85,
    "in.macro.prices.cpi_food": 4.80,
}
```

Unknown shock baseline:

```text
100.0
```

Unknown downstream target baseline:

```text
5.0
```

Do not fetch live values inside the simulation function.

The simulation is deterministic.

---

# 20. Exact Shock Propagation Algorithm

Do not modify this algorithm.

1. Retrieve:
   ```python
   downstream_impacts = self.graph.get_downstream_impacts(shock_variable)
   ```

2. Seed the shock variable:

```python
forecasts[shock_variable] = {
    "baseline": baseline,
    "shocked_period_1": baseline + shock_magnitude,
    "delta": shock_magnitude,
    "pct_change": (
        round(shock_magnitude / baseline * 100, 2)
        if baseline != 0 else 0.0
    ),
    "confidence": 1.0,
    "transmission_lag": 0
}
```

3. For every downstream impact:
   - resolve the shortest path again;
   - skip if no path.

4. Calculate:

```python
cum_multiplier = 1.0

for r in path:
    sign = 1.0 if r.elasticity_sign == "+" else -1.0
    decay = 0.55 * r.confidence_score
    cum_multiplier *= (sign * decay)
    traversed_relations.append(r.relation_id)

delta = round(shock_magnitude * cum_multiplier * 0.15, 2)
shocked_target = round(target_base + delta, 2)

ci_low = round(
    shocked_target - abs(delta * 0.25),
    2
)

ci_high = round(
    shocked_target + abs(delta * 0.25),
    2
)
```

## 20.1 Fixed constants

These are contractual:

```text
0.55
0.15
0.25
```

Do not:

- tune them;
- expose them as user parameters;
- move them into API request fields;
- replace them with a different attenuation model.

## 20.2 Target output

Every non-shock target contains exactly:

```text
indicator_name
sector
baseline
shocked_peak
delta
confidence_band
transmission_lag_months
confidence_score
mechanism_summary
```

where:

```text
confidence_band = [ci_low, ci_high]
```

and:

```text
mechanism_summary = " -> ".join(transmission_chain)
```

## 20.3 Provenance

Return:

```python
ScenarioResult(
    scenario_name=...,
    shock_variable=...,
    shock_magnitude=...,
    horizon_periods=...,
    forecasted_impacts=forecasts,
    provenance_chain=deduped_traversed_relations
)
```

The provenance chain must be deduplicated while preserving first-seen order.

---

# 21. Neo4j Mirror

File:

```text
backend/core/knowledge_graph/neo4j_store.py
```

Class:

```python
Neo4jKnowledgeGraphStore
```

Singleton:

```python
neo4j_store
```

## 21.1 Configuration

Read Neo4j connection details from the existing `settings` mechanism:

- `NEO4J_URI`
- Neo4j username
- Neo4j password

Do not create a second configuration system.

If `NEO4J_URI` is unset:

- all methods must return safe empty/false values;
- application startup must continue;
- no connection attempt should crash the process.

## 21.2 Synchronization

Implement:

```python
sync_ontology(onto=None)
```

Upsert:

```text
(:Indicator {
    id,
    name,
    sector,
    unit
})
```

and:

```text
(:Indicator)-[:AFFECTS {
    type,
    lag,
    sign,
    confidence
}]->(:Indicator)
```

Return `True` on successful synchronization.

## 21.3 Read helpers

Provide read helpers mirroring NetworkX path/neighborhood signatures where needed.

They are optional/persistence utilities only.

They must **not** be used by the normal orchestrator hot path.

## 21.4 Write discipline

No ad-hoc Neo4j writes.

All graph synchronization must originate from:

```text
ontology -> sync_ontology()
```

---

# 22. Orchestrator Integration

File:

```text
backend/core/orchestrator/graph.py
```

Implement:

```python
kg_causal_enrichment_node(state) -> dict
```

## 22.1 Required placement

The fixed graph order is:

```text
decompose
    ->
parallel_a2a_execute
    ->
kg_causal_enrichment
    ->
synthesis
    ->
END
```

Do not place KG enrichment before sector-agent observations are collected.

Do not make KG enrichment replace A2A execution.

---

# 23. KG Enrichment Node Algorithm

## 23.1 Collect indicators

From:

```text
collected_observations
```

collect:

```python
obs["indicator_id"]
```

Deduplicate while preserving first-seen order.

If:

```text
scenario_shock.variable
```

exists and is not already present, append it.

Do not add arbitrary indicators.

## 23.2 Pairwise causal paths

For every ordered pair:

```text
(u, v)
```

where:

```text
u != v
```

call:

```python
graph_engine.get_shortest_transmission_path(u, v)
```

If non-empty, append:

```python
{
    "from": u,
    "to": v,
    "hops": len(path),
    "total_lag_months": sum(
        r.transmission_lag_months for r in path
    ),
    "relations": [
        r.model_dump()
        for r in path
    ]
}
```

Do not compute weighted alternatives.

## 23.3 Scenario

If `scenario_shock` is present, call:

```python
causal_engine.simulate_scenario(
    name,
    shock_variable,
    magnitude
)
```

Defaults:

```text
variable = in.macro.prices.brent_crude
magnitude = 20.0
name = Simulated Macro Shock
```

Store:

```python
res.model_dump()
```

as:

```text
scenario_result
```

Otherwise:

```text
scenario_result = None
```

## 23.4 Mermaid

Generate:

```python
graph_engine.generate_mermaid_diagram(
    focus_indicator_ids=ind_ids[:5] or None
)
```

## 23.5 Return shape

Return exactly:

```python
{
    "causal_paths": ...,
    "scenario_result": ...,
    "mermaid_diagram": ...,
    "status": "enriched"
}
```

---

# 24. Synthesis Integration

The existing synthesis stage must consume KG enrichment rather than independently reconstructing causal paths.

The final analysis report must render these sections when applicable:

1. Indicator matrix
2. Mermaid causal graph
3. Shock table
4. Taxonomy note

Use this taxonomy note verbatim:

```text
Transmission edges classified according to 5-tier taxonomy (THEORY -> STATISTICAL -> LAGGED -> GRANGER -> STRUCTURAL_CAUSAL_MODEL).
```

The synthesis model must not invent numbers.

---

# 25. GraphRAG Fusion Order

The order is mandatory:

## Step 1 — Numeric observations

Get numbers through the existing:

```text
FastMCP / DuckDB
```

sector-owner mechanism.

Only the owner agent should fetch its sector data.

## Step 2 — KG structure

Add:

- `causal_paths`
- downstream impacts
- Mermaid graph

## Step 3 — Documentary narrative

Use Qdrant excerpts from sources such as:

- MPC minutes
- Budget speech
- Economic Survey

Evidence must retain:

```text
source authority
title
date
verbatim excerpt
```

## Step 4 — LLM synthesis

The LLM may synthesize only from Steps 1–3.

If Qdrant is unavailable:

- continue using numeric observations + KG;
- explicitly mark documentary narrative as unavailable;
- never invent a quotation or evidence.

---

# 26. Agent Boundary Rules

The architecture must preserve:

```text
A2A != FastMCP
```

A2A is for:

- agent-to-agent reasoning;
- sharing conclusions.

FastMCP is for:

- raw/current data retrieval.

No A2A call should be used as a substitute for raw data retrieval.

No agent may directly import another sector's MCP or DB module.

No cross-sector database shortcuts.

---

# 27. API Contracts

Implement in:

```text
backend/main.py
```

No authentication changes are required.

## 27.1 GET /health

Return existing health information plus:

```text
knowledge_graph_nodes
knowledge_graph_edges
```

Values must come from the live NetworkX graph:

```python
graph.number_of_nodes()
graph.number_of_edges()
```

Do not hardcode counts.

---

## 27.2 GET /api/v1/kg/path

Parameters:

```text
source_id
target_id
```

Return:

```json
{
  "source": "...",
  "target": "...",
  "hops": 0,
  "total_lag_months": 0,
  "relationships": []
}
```

For a valid path:

- `hops = len(relationships)`
- `total_lag_months = sum(path lags)`
- relationships are serialized `CausalRelationship.model_dump()` values.

Unknown source/target:

- HTTP 200;
- `hops = 0`;
- `relationships = []`;
- no exception.

---

## 27.3 GET /api/v1/kg/impacts

Parameter:

```text
shock_id
```

Return:

```json
{
  "shock_indicator_id": "...",
  "reachable_targets_count": 0,
  "downstream_impacts": []
}
```

Use the NetworkX downstream impact contract exactly.

---

## 27.4 POST /api/v1/simulate

Body:

```json
{
  "scenario_name": "...",
  "shock_variable": "...",
  "shock_magnitude": 20.0,
  "horizon_periods": 4
}
```

Return:

```python
ScenarioResult.model_dump()
```

Only unexpected exceptions should become:

```text
500
```

with:

```json
{
  "detail": "Simulation error: ..."
}
```

---

## 27.5 POST /api/v1/analyze

Body:

```json
{
  "query": "...",
  "scenario_shock": {
    "variable": "...",
    "magnitude": 20.0,
    "name": "..."
  }
}
```

`scenario_shock` is optional.

Return:

```json
{
  "query": "...",
  "status": "...",
  "target_sectors": [],
  "collected_observations": [],
  "causal_paths": [],
  "scenario_result": null,
  "mermaid_diagram": "...",
  "report_markdown": "...",
  "confidence_score": 0.0
}
```

Preserve any existing required response fields already used by the application.

---

# 28. Public Re-Exports

`backend/core/knowledge_graph/__init__.py` should re-export the intended public KG components:

- ontology
- NetworkX engine
- Neo4j store
- relevant canonical models if existing project conventions require them

Do not create duplicate classes through re-export files.

The actual implementation must live in the specified source modules.

---

# 29. Demo Platform

`backend/demo_platform.py` must print live graph counts at startup:

```text
Canonical Nodes: N | 5-Tier Causal Edges: M
```

The values must be calculated from the actual graph.

Do not print hardcoded:

```text
20
12
```

because the ontology may later be extended.

---

# 30. Build Order

Execute implementation in exactly this sequence.

## Phase 1 — Schema

Implement:

```text
backend/core/data/schema.py
```

Complete:

- `SectorEnum`
- `CausalRelationType`
- `CanonicalIndicator`
- `CausalRelationship`
- `ScenarioResult`
- validation

Then run import/model validation.

## Phase 2 — Ontology

Implement:

```text
ontology.py
```

Complete:

- canonical indicators;
- canonical relationships;
- validation;
- singleton.

Then verify:

```text
>= 20 nodes
>= 12 relationships
```

and that the exact seed IDs exist.

## Phase 3 — NetworkX

Implement:

```text
networkx_engine.py
```

Complete:

- graph build;
- shortest path;
- neighborhood;
- downstream impacts;
- Mermaid.

Then verify the Brent-to-GDP path.

## Phase 4 — Econometrics

Implement:

```text
causal_engine.py
```

Complete:

- Granger function;
- deterministic simulation.

Then verify sign propagation.

## Phase 5 — Neo4j

Implement:

```text
neo4j_store.py
```

Complete:

- optional configuration;
- one-way sync;
- safe no-Neo4j behavior.

Test startup without Neo4j.

## Phase 6 — Orchestrator

Implement:

```text
kg_causal_enrichment_node
```

and wire it:

```text
decompose -> parallel_a2a_execute -> kg_causal_enrichment -> synthesis -> END
```

## Phase 7 — API

Implement/extend:

```text
main.py
```

Expose all required endpoints without breaking unrelated routes.

## Phase 8 — Demo

Implement live count reporting.

## Phase 9 — End-to-end validation

Run all tests and acceptance checks in Section 33.

---

# 31. Implementation Quality Rules

## 31.1 Do not overengineer

Do not add:

- caching;
- parallel graph traversal;
- graph databases as primary storage;
- embeddings;
- vectorized graph representations;
- background synchronization;
- event buses;
- additional abstraction layers;
- generic plugin architectures.

The graph is intentionally small.

With approximately 20 nodes, straightforward traversal is preferred.

## 31.2 Do not prematurely optimize

The expected graph is small.

The specified:

```text
descendants + BFS per target
```

approach is intentional.

Do not replace it with a complex optimization.

## 31.3 Preserve deterministic behavior

Given the same ontology and inputs:

- paths should be deterministic;
- simulation output should be deterministic;
- Mermaid output should be deterministic enough for tests;
- API shapes should be stable.

Avoid unordered transformations where ordering is contractually specified.

## 31.4 Serialization

Use Pydantic's:

```python
.model_dump()
```

for Pydantic model serialization.

Do not manually reconstruct model dictionaries when the model itself can provide the contract.

---

# 32. Test Requirements

Tests must cover at least:

## Schema

- valid indicator ID;
- invalid indicator ID;
- invalid frequency;
- invalid relationship sign;
- negative lag;
- invalid confidence;
- empty mechanism;
- empty assumptions;
- self-loop;
- unknown endpoint.

## NetworkX

- graph is `MultiDiGraph`;
- expected node count;
- expected edge count;
- unknown source returns `[]`;
- unknown target returns `[]`;
- no-path returns `[]`;
- shortest path uses hops;
- parallel edges select highest confidence;
- cumulative confidence uses multiplication;
- total lag uses summation;
- downstream sorting;
- Mermaid starts with `graph LR`.

## Econometrics

- missing columns;
- insufficient sample;
- valid Granger result;
- exception handling;
- p-value threshold;
- optimal lag;
- simulation sign propagation;
- fixed attenuation constants;
- confidence-band width;
- provenance.

## Neo4j

- disabled configuration does not crash;
- sync method is the only write path;
- safe empty behavior without Neo4j.

## Orchestrator

- KG runs after A2A;
- scenario is optional;
- scenario shock is included in indicator IDs;
- causal paths are generated;
- Mermaid is generated;
- status is `"enriched"`.

## API

- health counts;
- valid path;
- unknown path;
- downstream impacts;
- simulation;
- analysis;
- no 404 for unknown graph indicators.

---

# 33. Mandatory Acceptance Tests

All of these must pass.

## Acceptance 1 — Graph health

```text
GET /health
```

must report:

```text
knowledge_graph_nodes >= 20
knowledge_graph_edges >= 12
```

using live graph counts.

## Acceptance 2 — Brent-to-GDP path

```text
GET /api/v1/kg/path?source_id=in.macro.prices.brent_crude&target_id=in.macro.real.gdp_growth
```

must return:

```text
hops = 6
```

with this exact conceptual chain:

```text
brent_crude
 -> wpi_all
 -> cpi_headline
 -> repo_rate
 -> bank_credit_growth
 -> iip_growth
 -> gdp_growth
```

The mechanisms must remain in path order.

## Acceptance 3 — Brent downstream impacts

```text
GET /api/v1/kg/impacts?shock_id=in.macro.prices.brent_crude
```

must include at least:

```text
cpi_headline
repo_rate
usd_inr
```

and must be sorted by:

```text
hops ascending
confidence descending
```

## Acceptance 4 — Oil shock

Call:

```json
{
  "scenario_name": "Oil Surge",
  "shock_variable": "in.macro.prices.brent_crude",
  "shock_magnitude": 20
}
```

Expected properties:

- CPI delta is positive;
- credit delta is directionally negative;
- every non-shock entry has a confidence band;
- confidence-band width is:
  ```text
  |delta| * 0.5
  ```
- provenance chain is non-empty.

## Acceptance 5 — Analyze

Run an oil-related analysis query.

The returned `report_markdown` must contain:

- indicator table;
- Mermaid block;
- taxonomy note;
- no invented numeric values outside supplied observations and simulation outputs.

## Acceptance 6 — Unknown indicator

```text
GET /api/v1/kg/path?source_id=foo&target_id=bar
```

must return HTTP 200 with:

```text
hops: 0
relationships: []
```

---

# 34. Expected Direction Checks

The implementation must preserve these directional relationships:

```text
Brent crude
  +-> WPI
  +-> CPI
  +-> Repo
  --> Credit because repo -> credit is negative
  --> IIP
  --> GDP
```

For the direct Brent -> trade balance edge:

```text
Brent increase -> trade balance deterioration
```

For:

```text
trade balance -> USD/INR
```

the specified sign is positive because a wider deficit increases USD demand and depreciates INR.

For:

```text
repo rate -> bank nifty
```

the sign is negative.

Do not reverse signs based on intuitive interpretation of the target variable.

The sign stored in the ontology is authoritative.

---

# 35. Provenance Requirements

There are three distinct provenance layers.

## 35.1 Relationship provenance

Every path contains the complete `CausalRelationship` model, including:

```text
relation_id
relation_type
mechanism_description
documented_assumptions
confidence_score
transmission_lag_months
elasticity_sign
```

## 35.2 Simulation provenance

`ScenarioResult.provenance_chain` contains traversed `relation_id`s.

Do not replace relation IDs with mechanism text.

## 35.3 Documentary provenance

Qdrant evidence retains:

```text
source authority
title
date
verbatim excerpt
```

Do not merge documentary evidence and causal relation IDs into one ambiguous provenance field.

---

# 36. No-Hallucination Rules

The implementation must enforce these distinctions:

### Graph fact

Example:

```text
repo_rate -> bank_credit_growth
```

comes from ontology.

### Numeric fact

Example:

```text
CPI = 4.26
```

comes from:

- specified simulation baseline, or
- live MCP/DuckDB observation.

### Documentary fact

Example:

```text
policy statement from MPC minutes
```

comes from Qdrant evidence.

The synthesis layer must not fabricate any of these.

If data is unavailable:

```text
unavailable
```

is preferable to an invented value.

---

# 37. What Must Never Be Done

The following will fail review.

## Architecture

- Do not introduce another graph library.
- Do not replace NetworkX with Neo4j.
- Do not make Neo4j mandatory.
- Do not duplicate ontology definitions.
- Do not move time-series storage into the KG.
- Do not store document chunks in the KG.

## Traversal

- Do not use Dijkstra.
- Do not use confidence-weighted shortest paths.
- Do not invent a different path scoring formula.
- Do not change cumulative confidence from multiplication.
- Do not change total lag from summation.

## Simulation

- Do not change:
  ```text
  0.55
  0.15
  0.25
  ```
- Do not expose these as user parameters.
- Do not replace the baseline dictionary.
- Do not add live-data fetching inside simulation.
- Do not silently clamp negative values.

## Causal taxonomy

- Do not treat Granger as proof of structural causality.
- Do not change the p-value threshold from `0.05`.
- Do not add an unapproved sixth relation type.

## Agent architecture

- Do not use A2A for raw data retrieval.
- Do not use MCP as peer-agent reasoning.
- Do not import another sector's DB/MCP implementation directly.

## Codebase

- Do not rewrite unrelated sectors.
- Do not modify unrelated files.
- Do not add dependencies unless already required by the fixed architecture and repository.
- Do not create speculative abstractions.

---

# 38. Handling Common Implementation Questions

## Q: What if the target file already exists?

Preserve unrelated existing behavior and integrate the specified KG functionality into it.

## Q: What if a dependency is already installed at a different version?

Use the repository's existing dependency management and the fixed architecture. Do not redesign around a different library.

## Q: What if Neo4j is unavailable?

The application must continue. NetworkX remains authoritative for runtime queries.

## Q: What if Qdrant is unavailable?

Use numeric observations + KG structure. Mark documentary narrative unavailable. Never invent a quote.

## Q: What if an indicator is unknown?

Return the specified empty result. Do not create an ad-hoc node.

## Q: What if there are multiple edges between two nodes?

For shortest-path materialization, select the edge with maximum confidence.

## Q: Why not use confidence to choose the route?

Because the contract defines path length as the meaning of "shortest transmission path." Confidence is a post-selection score, not the routing metric.

## Q: Why not use Neo4j for all queries?

Because Neo4j is explicitly a persistent mirror. NetworkX is the runtime hot path.

## Q: Why not dynamically learn graph relationships?

Not in this implementation. Relationships are curated and/or explicitly produced by the specified econometric process.

## Q: Can more indicators be added?

Only if the task explicitly authorizes extending the seed ontology. The 20 required indicators and 12 required relationships must not be edited or removed.

## Q: Can the simulation use real-time data?

Not inside the simulation implementation. The simulation accepts an optional explicit baseline dictionary and otherwise uses the fixed deterministic baselines.

## Q: What if a baseline is missing?

Use:

```text
100.0
```

for the shock indicator and:

```text
5.0
```

for unknown downstream targets.

## Q: What if a path does not exist?

Return the empty result. Do not raise.

## Q: What if the requested feature seems to require another file?

First attempt implementation within the authorized files. Do not silently expand the scope.

---

# 39. Final Implementation Checklist

Before declaring the task complete, verify every item.

## Schema

- [ ] Exact enum values exist.
- [ ] Exact Pydantic fields exist.
- [ ] Indicator regex works.
- [ ] Relationship validation works.
- [ ] ScenarioResult exists.

## Ontology

- [ ] 20 seed indicators exist.
- [ ] 12 seed edges exist.
- [ ] All endpoints are valid.
- [ ] No self-loops.
- [ ] Signs are only `+`/`-`.
- [ ] Confidence values are valid.
- [ ] Assumptions are present.
- [ ] Singleton exists.

## NetworkX

- [ ] Uses `MultiDiGraph`.
- [ ] Singleton exists.
- [ ] Graph is built from ontology.
- [ ] Unknown nodes return safe results.
- [ ] BFS shortest path is used.
- [ ] Highest-confidence parallel edge is selected.
- [ ] Downstream impacts are correctly sorted.
- [ ] Mermaid renderer works.

## Econometrics

- [ ] Granger implementation uses `ssr_ftest`.
- [ ] Default max lag is 2.
- [ ] Threshold is `< 0.05`.
- [ ] Simulation constants are unchanged.
- [ ] Fixed baselines are unchanged.
- [ ] Provenance IDs are preserved.

## Neo4j

- [ ] Optional.
- [ ] No startup failure without Neo4j.
- [ ] Ontology is the source of synchronization.
- [ ] No ad-hoc writes.

## Orchestration

- [ ] A2A executes before KG enrichment.
- [ ] KG executes before synthesis.
- [ ] Scenario is optional.
- [ ] Causal paths are returned.
- [ ] Mermaid is returned.

## GraphRAG

- [ ] Numeric data comes first.
- [ ] KG structure comes second.
- [ ] Qdrant evidence comes third.
- [ ] Synthesis is constrained to those inputs.
- [ ] Missing Qdrant does not cause fabricated narrative.

## API

- [ ] `/health`
- [ ] `/api/v1/kg/path`
- [ ] `/api/v1/kg/impacts`
- [ ] `/api/v1/simulate`
- [ ] `/api/v1/analyze`

all satisfy their contracts.

## Validation

- [ ] Brent -> GDP = 6 hops.
- [ ] Brent impacts include CPI, repo, USD/INR.
- [ ] Oil shock direction checks pass.
- [ ] Confidence-band width check passes.
- [ ] Provenance is non-empty.
- [ ] Unknown node returns HTTP 200.
- [ ] Mermaid starts with `graph LR`.
- [ ] No invented numeric values appear in analysis output.
- [ ] Existing unrelated functionality still works.

---

# 40. Definition of Done

The implementation is complete only when:

1. The KG can be imported without errors.
2. The canonical ontology successfully constructs the NetworkX graph.
3. The graph contains at least 20 nodes and 12 relationships.
4. All required traversal contracts work.
5. Shock simulation follows the exact specified algorithm.
6. Neo4j is optional and non-fatal.
7. The KG enrichment node is correctly positioned in LangGraph.
8. All required API endpoints work.
9. GraphRAG fusion follows the fixed order.
10. Required acceptance tests pass.
11. No forbidden architecture or behavior was introduced.
12. Only the authorized files were modified.

Do not declare success merely because imports work.

The final implementation must be validated through the actual graph behavior and endpoint contracts.

---

# 41. Final Agent Directive

**Execute the implementation from top to bottom.**

Do not ask for architectural choices that this document has already resolved.

Do not redesign fixed components.

Do not add speculative functionality.

Do not replace exact algorithms with "better" alternatives.

When the repository contains existing compatible infrastructure, integrate with it rather than duplicating it.

When something is unavailable, fail safely according to the contracts above.

When something is unspecified, preserve existing repository behavior rather than inventing a new design.

The objective is a **small, deterministic, explainable, testable causal Knowledge Graph integrated into MacroGraph**, not a generalized graph platform.

**Implementation must be additive, contract-driven, provenance-preserving, and reviewable.**
