# KNOWLEDGE GRAPH — Deterministic Build & Use Spec for Coding Agent

> Read `KNOWLEDGE_GRAPH_CAUSAL_GRAPHRAG_EXPLAINED.md` first for concepts.
> This file is the **single source of truth for implementation**. Follow it exactly.
> Do not ask questions. Do not offer alternatives. Do not invent new libraries, paths, or schemas.
> If anything is unspecified here, keep the existing repo code unchanged.

## 0. Mission and Non-Negotiable Rules

**Mission:** Build and wire the macroeconomic Knowledge Graph (KG) so it powers (a) retrieval, (b) shock propagation, (c) explainability, (d) GraphRAG synthesis.

**Rules:**

1. Create or edit ONLY the files listed in Section 2. Touch nothing else.
2. Stack is fixed: Python 3.12, Pydantic v2, NetworkX 3.x `MultiDiGraph`, statsmodels, FastAPI, LangGraph. No other graph library.
3. Single ontology singleton drives both NetworkX and Neo4j. Never define nodes/edges in two places.
4. Every economic claim in output must cite traversed `relation_id`s. No uncited causal sentence.
5. Every graph query function must never raise on missing node or missing path. Return empty list/dict.
6. All IDs, field names, endpoint paths, and formulas below are exact. Use them verbatim.

---

## 1. Fixed Architecture Decisions (Do Not Revisit)

1. **In-memory engine:** `networkx.MultiDiGraph`. Reason: zero-latency traversal, native `shortest_path` BFS and `descendants`, no server needed for API and LangGraph.
2. **Persistent engine:** Neo4j only if `NEO4J_URI` is set. It is a mirror, never the query path for the orchestrator. Sync direction is one-way: ontology -> Neo4j.
3. **Fact store stays DuckDB.** KG stores structure and priors (lags, signs, confidences, mechanisms). KG never stores time-series values except simulation baselines dict.
4. **Text store stays Qdrant.** KG does not store document chunks. GraphRAG fuses KG paths plus Qdrant excerpts at synthesis time.
5. **Path cost is unweighted hops.** Use BFS `shortest_path`, not Dijkstra on confidence. Confidence is used for ranking and attenuation, not pathfinding. This is faster and matches "most direct channel" semantics.
6. **Cumulative confidence = product of per-hop confidences. Total lag = sum of per-hop lags.** No other aggregation.
7. **Shock attenuation formula is fixed** in Section 6. Do not tune constants without updating this spec and all tests.

---

## 2. Fixed File Layout

Implement exactly these paths. Do not rename or split:

```text
backend/core/data/schema.py                        # CanonicalIndicator, CausalRelationship, CausalRelationType, ScenarioResult
backend/core/knowledge_graph/ontology.py           # MacroeconomicOntology + global `ontology`
backend/core/knowledge_graph/networkx_engine.py    # NetworkXGraphEngine + global `graph_engine`
backend/core/knowledge_graph/neo4j_store.py        # Neo4jKnowledgeGraphStore + global `neo4j_store`
backend/core/knowledge_graph/__init__.py           # re-exports above three
backend/core/econometrics/causal_engine.py         # CausalEconometricEngine + global `causal_engine`
backend/core/orchestrator/graph.py                 # kg_causal_enrichment_node + macro_orchestrator_graph
backend/main.py                                    # /api/v1/kg/path, /api/v1/kg/impacts, /api/v1/simulate, /api/v1/analyze, /health
backend/demo_platform.py                           # prints node/edge counts on startup
```

---

## 3. Fixed Schemas (Exact Pydantic Models)

Use exactly these fields, types, and constraints. No extra required fields.

### 3.1 SectorEnum

Values: `real_economy, prices_inflation, monetary_banking, fiscal, external, capital_markets, agriculture_rural, labour_employment`. Store `sector.value` string on NetworkX node.

### 3.2 CausalRelationType (5 tiers, fixed order)

```python
THEORY = "THEORY"
STATISTICAL_ASSOCIATION = "STATISTICAL_ASSOCIATION"
LAGGED_RELATIONSHIP = "LAGGED_RELATIONSHIP"
GRANGER_PREDICTIVE = "GRANGER_PREDICTIVE"
STRUCTURAL_CAUSAL_MODEL = "STRUCTURAL_CAUSAL_MODEL"
```

Assign tiers by this rule, no exceptions:

- Textbook consensus only -> `THEORY`
- Correlation + p-value, no lag -> `STATISTICAL_ASSOCIATION`
- Cross-correlation at lag k -> `LAGGED_RELATIONSHIP`
- `grangercausalitytests` p < 0.05 -> `GRANGER_PREDICTIVE`
- Explicit mandate or accounting identity with stated assumptions -> `STRUCTURAL_CAUSAL_MODEL`

### 3.3 CanonicalIndicator (exact)

```python
indicator_id: str       # MUST match regex ^in\.macro\.[a-z_]+\.[a-z_0-9]+$  e.g. in.macro.prices.cpi_headline
name: str               # full human name
sector: SectorEnum
subsector: Optional[str]
unit: str               # e.g. "% YoY", "USD/barrel", "Billion USD", "INR/USD", "points"
frequency: str          # one of: daily, weekly, fortnightly, monthly, quarterly, annual, seasonal, policy_cycle
source_authority: str   # e.g. MoSPI, RBI, NSE, IMD, Ministry of Commerce
source_url: Optional[str] = None
description: Optional[str] = None
```

### 3.4 CausalRelationship (exact)

```python
relation_id: str = "rel-<8 hex>"   # auto via uuid4 hex[:8] if not supplied
source_indicator_id: str            # must exist in ontology
target_indicator_id: str            # must exist in ontology, must not equal source
relation_type: CausalRelationType
transmission_lag_months: int >= 0
elasticity_sign: str                # ONLY "+" or "-" . Use "+" if co-move, "-" if inverse. Never "ambiguous".
empirical_p_value: Optional[float]  # set for STATISTICAL and above; None allowed only for THEORY
confidence_score: float in [0.0, 1.0]  # default 0.8 if unknown; curated priors in 0.82-0.98
mechanism_description: str          # REQUIRED, min 10 chars, plain economics mechanism
documented_assumptions: List[str]   # REQUIRED, min 1 item, explicit identification bound
```

Validation to implement in `ontology._build_ontology`: reject self-loop, reject unknown endpoint, reject empty mechanism, reject empty assumptions, reject confidence outside [0,1], reject negative lag.

---

## 4. Fixed Ontology Seed (Minimum Graph)

Seed exactly these 20 indicators and 12 edges. You may add more later only by appending to these lists, never by editing these 12.

Indicators (id | name | sector | unit | frequency | authority):

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

Edges (source -> target | type | lag | sign | p | conf | mechanism):

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

Each edge must also carry at least one `documented_assumptions` string from the existing `ontology.py`. Copy them verbatim.

---

## 5. NetworkX Engine — Exact Implementation

Class: `NetworkXGraphEngine` in `backend/core/knowledge_graph/networkx_engine.py`. Global singleton `graph_engine = NetworkXGraphEngine()` at import.

### 5.1 Build

`_build_graph()` must:

1. Call `self.graph.clear()`.
2. For each indicator: `add_node(ind_id, name, sector, subsector, unit, frequency, source_authority)`.
3. For each relationship: `add_edge(src, dst, key=rel.relation_id, relation=rel, relation_type=rel.relation_type.value, lag_months=rel.transmission_lag_months, elasticity=rel.elasticity_sign, confidence=rel.confidence_score, mechanism=rel.mechanism_description)`.
4. Use `nx.MultiDiGraph()`. No other class.

### 5.2 Retrieval Method 1 — Shortest transmission path

Signature: `get_shortest_transmission_path(source_id: str, target_id: str) -> List[CausalRelationship]`

Algorithm (exact):

1. If either node missing, return `[]`.
2. `path_nodes = nx.shortest_path(graph, source, target)` inside try/except `(NetworkXNoPath, NodeNotFound)` returning `[]`.
3. For each consecutive pair `(u,v)`: fetch `get_edge_data(u,v)`, pick max by `confidence`, append its `relation` object.
4. Return list in path order. Do not sort or filter further.

### 5.3 Retrieval Method 2 — Causal neighborhood

Signature: `get_causal_neighborhood(indicator_id: str, depth: int = 2) -> dict`

Implementation:

1. If node missing, return `{"indicator_id": id, "upstream": [], "downstream": []}` shape-compatible (also include `upstream_drivers` and `downstream_impacts` keys for backward compat).
2. Upstream = all predecessors + their edge `relation.model_dump()`.
3. Downstream = all successors + their edge `relation.model_dump()`.
4. `depth` param accepted but 1-hop predecessors/successors is the required behavior. Do not implement k-hop BFS unless depth > 1 is explicitly needed later.

### 5.4 Retrieval Method 3 — Downstream impacts (shock fan-out)

Signature: `get_downstream_impacts(shock_indicator_id: str) -> List[dict]`

Algorithm (exact):

1. If node missing, return `[]`.
2. `reachable = nx.descendants(graph, shock_id)`.
3. For each target: `path = get_shortest_transmission_path(shock_id, target)`. Skip if empty.
4. `total_lag = sum(r.transmission_lag_months for r in path)`.
5. `cumulative_conf = product(r.confidence_score for r in path)`, rounded to 2 decimals in output.
6. Emit dict with EXACT keys: `target_indicator_id, target_name, sector, path_length_hops, total_lag_months, cumulative_confidence, transmission_chain` where `transmission_chain` is list of `mechanism_description` strings in path order.
7. Sort output by `(path_length_hops asc, cumulative_confidence desc)`. No other sort.

Complexity note: descendants + one BFS per target is O(V*(V+E)) worst case but V~20 so it is instant. Do not add caching layers or parallelization.

### 5.5 Explainability Renderer — Mermaid

Signature: `generate_mermaid_diagram(focus_indicator_ids: Optional[List[str]] = None) -> str`

Output format (exact):

```text
graph LR
    <clean_id>["<Human Name>"]
    <clean_src> -->|"+ (1M) [LAGGED_RELATIONSHIP]"| <clean_dst>
```

Rules: `clean_id = raw.replace(".", "_").replace("-", "_")`. Escape `"` in names to `'`. If `focus_indicator_ids` given, include those nodes plus their 1-hop predecessors and successors, and only edges where both ends are in that set. Else render all edges. `lag` renders as `{lag_months}M`, elasticity as stored sign, type as stored `relation_type`.

---

## 6. Causal Engine — Exact Implementation

File `backend/core/econometrics/causal_engine.py`. Class `CausalEconometricEngine`, global `causal_engine`. Holds reference `self.graph = graph_engine`.

### 6.1 Granger test (exact)

Signature: `test_granger_causality(data: pd.DataFrame, cause_col: str, effect_col: str, max_lag: int = 2) -> dict`

Steps:

1. If columns missing: return `{"is_significant": False, "p_value": None, "optimal_lag": None, "error": "Columns not found"}`.
2. `subset = data[[effect_col, cause_col]].dropna()`. Note column order effect-first as statsmodels expects `[y, x]`.
3. If `len(subset) < 10`: return insufficient-sample dict with error `"Insufficient sample size (N < 10)"`.
4. `results = grangercausalitytests(subset, maxlag=max_lag, verbose=False)`. For each lag take `lag_res[0]["ssr_ftest"][1]` as p-value. Keep min p-value and its lag.
5. Return `{"cause": cause_col, "effect": effect_col, "optimal_lag": best_lag, "p_value": round(min_p,4), "is_significant": min_p < 0.05}`.
6. Wrap in try/except returning `is_significant False` plus `error: str(err)` on exception.
7. Default `max_lag = 2`. Do not auto-select lag by AIC. Use ssr_ftest only.

### 6.2 Shock propagation simulation (exact, no deviations)

Signature:

```python
simulate_scenario(scenario_name: str, shock_variable: str, shock_magnitude: float, horizon_periods: int = 4, baseline_values: Optional[Dict[str,float]] = None) -> ScenarioResult
```

Fixed default baselines (use verbatim when `baseline_values` is None):

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

Unknown indicator baseline fallback is `100.0`. Unknown downstream target baseline fallback is `5.0`.

Propagation algorithm (implement line-for-line):

1. `downstream_impacts = self.graph.get_downstream_impacts(shock_variable)`.
2. Seed `forecasts[shock_variable] = {baseline, shocked_period_1: baseline+magnitude, delta: magnitude, pct_change: round(magnitude/baseline*100,2) if baseline != 0 else 0.0, confidence: 1.0, transmission_lag: 0}`.
3. For each impact in `downstream_impacts`: resolve `path = graph.get_shortest_transmission_path(shock_variable, target_id)`. Skip if empty.
4. Compute:
```python
cum_multiplier = 1.0
for r in path:
    sign = 1.0 if r.elasticity_sign == "+" else -1.0
    decay = 0.55 * r.confidence_score
    cum_multiplier *= (sign * decay)
    traversed_relations.append(r.relation_id)
delta = round(shock_magnitude * cum_multiplier * 0.15, 2)
shocked_target = round(target_base + delta, 2)
ci_low = round(shocked_target - abs(delta * 0.25), 2)
ci_high = round(shocked_target + abs(delta * 0.25), 2)
```
5. Store per target EXACT keys: `indicator_name, sector, baseline, shocked_peak, delta, confidence_band: [ci_low, ci_high], transmission_lag_months, confidence_score, mechanism_summary` where `mechanism_summary = " -> ".join(transmission_chain)`.
6. Return `ScenarioResult(scenario_name, shock_variable, shock_magnitude, horizon_periods, forecasted_impacts=forecasts, provenance_chain=deduped traversed_relations)`.

Constants `0.55`, `0.15`, `0.25` are fixed. Do not expose as params.

---

## 7. Neo4j Mirror — Exact Implementation

File `backend/core/knowledge_graph/neo4j_store.py`. Class `Neo4jKnowledgeGraphStore`, global `neo4j_store`.

Behavior:

1. Read connection from `settings` (`NEO4J_URI`, user, password). If unset, all methods return `False` or `[]` without raising. Never crash startup when Neo4j is absent.
2. `sync_ontology(onto=None)`: upsert every indicator as `(:Indicator {id, name, sector, unit})` and every relationship as `(:Indicator)-[:AFFECTS {type, lag, sign, confidence}]->(:Indicator)`. Return True on success.
3. Provide read helpers for path and neighborhood mirroring NetworkX signatures but they are NOT used by the orchestrator hot path.
4. Never let Neo4j diverge: no ad-hoc writes outside `sync_ontology`.

---

## 8. Orchestrator Wiring — Exact Node

File `backend/core/orchestrator/graph.py`. Function `kg_causal_enrichment_node(state) -> dict` runs AFTER `parallel_a2a_execute` and BEFORE `synthesis`. Graph order is fixed: `decompose -> parallel_a2a_execute -> kg_causal_enrichment -> synthesis -> END`.

Node steps (exact):

1. Collect `ind_ids = unique(obs["indicator_id"] for obs in collected_observations)`. If `scenario_shock.variable` present and not in list, append it.
2. For every ordered pair `(u,v)`, `u != v`: call `graph_engine.get_shortest_transmission_path(u,v)`. If non-empty append `{"from": u, "to": v, "hops": len(path), "total_lag_months": sum(...), "relations": [r.model_dump() for r in path]}`.
3. If `scenario_shock` present: call `causal_engine.simulate_scenario(name, shock_variable, magnitude)` with defaults `variable=in.macro.prices.brent_crude, magnitude=20.0, name="Simulated Macro Shock"`. Store `res.model_dump()` as `scenario_result`, else None.
4. `mermaid_diagram = graph_engine.generate_mermaid_diagram(focus_indicator_ids=ind_ids[:5] or None)`.
5. Return `{"causal_paths": ..., "scenario_result": ..., "mermaid_diagram": ..., "status": "enriched"}`.

Synthesis node must then render: Section 2 indicator matrix, Section 3 Mermaid block, Section 4 shock table (if scenario), Section 5 taxonomy note verbatim: `Transmission edges classified according to 5-tier taxonomy (THEORY -> STATISTICAL -> LAGGED -> GRANGER -> STRUCTURAL_CAUSAL_MODEL).`

---

## 9. API Contracts — Exact

Implement in `backend/main.py`. No auth. All GETs return 200 with empty lists when no path, never 404 for unknown indicator.

1. `GET /health` includes `knowledge_graph_nodes = graph.number_of_nodes()` and `knowledge_graph_edges = graph.number_of_edges()`.
2. `GET /api/v1/kg/path?source_id=X&target_id=Y` returns `{"source","target","hops","total_lag_months","relationships": [CausalRelationship.model_dump()]}`.
3. `GET /api/v1/kg/impacts?shock_id=X` returns `{"shock_indicator_id","reachable_targets_count","downstream_impacts": [...]}` per Section 5.4 shape.
4. `POST /api/v1/simulate` body `{scenario_name, shock_variable, shock_magnitude, horizon_periods=4}` returns `ScenarioResult.model_dump()`. 500 only on unexpected exception with `detail: "Simulation error: ..."`.
5. `POST /api/v1/analyze` body `{query, scenario_shock?: {variable, magnitude, name}}` runs full LangGraph and returns `{query, status, target_sectors, collected_observations, causal_paths, scenario_result, mermaid_diagram, report_markdown, confidence_score}`.

---

## 10. GraphRAG Use (Exact Fusion Order)

When answering a macro query, fuse in this fixed order. Do not reorder:

1. Numbers via FastMCP/DuckDB per sector (owner agent only).
2. Structure via KG (`causal_paths` + `downstream_impacts` + Mermaid).
3. Narrative via Qdrant excerpts (MPC minutes, Budget speech, Economic Survey) attached as `Evidence` with source authority, title, date, verbatim excerpt.
4. LLM synthesis constrained to steps 1-3. If Qdrant is unavailable, proceed with steps 1-2 and mark narrative as unavailable. Never hallucinate the missing quote.

Peer agents share conclusions via A2A only. No agent imports another sector's MCP or DB module directly.

---

## 11. Build Order (Execute Top to Bottom)

- [ ] 1. `schema.py`: implement the four models exactly per Section 3. Add regex validation for `indicator_id`.
- [ ] 2. `ontology.py`: seed the 20 indicators and 12 edges per Section 4 with verbatim assumptions.
- [ ] 3. `networkx_engine.py`: implement build + three retrieval methods + Mermaid per Section 5.
- [ ] 4. `causal_engine.py`: implement Granger + simulation per Section 6.
- [ ] 5. `neo4j_store.py`: implement one-way sync per Section 7 with silent skip when unconfigured.
- [ ] 6. `orchestrator/graph.py`: implement enrichment node and fixed edge order per Section 8.
- [ ] 7. `main.py`: expose the five endpoints per Section 9.
- [ ] 8. `demo_platform.py`: print `Canonical Nodes: N | 5-Tier Causal Edges: M` from live graph counts.
- [ ] 9. Tests: path brent->gdp is 6 hops; impacts of brent include cpi, repo, usd_inr; simulation delta sign matches elasticity product; unknown node returns []; Mermaid starts with `graph LR`.

---

## 12. Forbidden (Will Fail Review)

- No alternative graph DB or library (no igraph, graph-tool, rustworkx).
- No learned embeddings inside KG edges. Confidence stays curated or Granger-derived.
- No Dijkstra / weighted shortest path. Hops only.
- No changing attenuation constants or baseline dict without spec update.
- No raising exceptions for missing nodes/paths in query methods.
- No storing document text or time series inside NetworkX node/edge attrs beyond Section 5.1 fields.
- No A2A for raw data fetch. No MCP for peer reasoning. No direct cross-sector DB imports.

---

## 13. Acceptance Criteria (All Must Pass)

1. `GET /health` reports nodes >= 20 and edges >= 12.
2. `GET /api/v1/kg/path?source_id=in.macro.prices.brent_crude&target_id=in.macro.real.gdp_growth` returns hops 6 with ordered mechanisms brent->wpi->cpi->repo->credit->iip->gdp.
3. `GET /api/v1/kg/impacts?shock_id=in.macro.prices.brent_crude` includes `cpi_headline`, `repo_rate`, `usd_inr`, sorted by hops then confidence.
4. `POST /api/v1/simulate` with `{scenario_name:"Oil Surge", shock_variable:"in.macro.prices.brent_crude", shock_magnitude:20}` returns CPI delta positive, credit delta negative-direction-consistent, every non-shock entry has `confidence_band` of width `|delta|*0.5`, and `provenance_chain` non-empty.
5. `POST /api/v1/analyze` with oil query returns markdown containing indicator table, ```mermaid block, taxonomy note, and no invented numbers outside MCP observations and simulation outputs.
6. Unknown `source_id=foo` returns `hops:0, relationships:[]` with HTTP 200.

Execute now. No clarifications. No options. No deviations.
