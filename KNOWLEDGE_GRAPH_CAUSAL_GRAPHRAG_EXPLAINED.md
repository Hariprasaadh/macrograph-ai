# Knowledge Graph, Causality & GraphRAG — Complete Explainer for Macrograph-AI

> **Scope:** This is a standalone conceptual + project-grounded document.
> It explains **(1) Knowledge Graphs, (2) Causal reasoning, (3) GraphRAG** from absolute basics to exactly how they are used in **Macrograph-AI** (Indian macroeconomic intelligence platform).
> No code was changed to produce this file.

**How to read this document:**

- If you are new: read Parts 1 → 2 → 3 in order. Each part starts with “What is it in plain English?” and “Why not just use a normal database / normal AI search?”.
- If you already know graphs: jump to “How it is useful HERE” in each part and Section 4 (end-to-end example).
- Files mentioned like `backend/core/knowledge_graph/ontology.py` are the actual implementation in this repo.

---

## Table of Contents

1. [Part 1 — Knowledge Graph (KG)](#part-1--knowledge-graph-kg)
2. [Part 2 — Causal Reasoning / Causal Inference](#part-2--causal-reasoning--causal-inference)
3. [Part 3 — GraphRAG (Graph + Retrieval-Augmented Generation)](#part-3--graphrag-graph--retrieval-augmented-generation)
4. [Part 4 — How All Three Work Together in Macrograph-AI](#part-4--how-all-three-work-together-in-macrograph-ai)
5. [Quick FAQ / Viva Questions](#quick-faq--viva-questions)

---

# Part 1 — Knowledge Graph (KG)

## 1.1 What is a Knowledge Graph in plain English?

A **knowledge graph** is a way of storing knowledge as:

- **Nodes (entities):** things like `CPI Inflation`, `Repo Rate`, `GDP Growth`, `Brent Crude Price`.
- **Edges (relationships):** directed connections like `Brent Crude → WPI Inflation` meaning “crude affects wholesale prices”.
- **Properties on both:** each node and edge carries details.

Example sentence:

> “Higher Brent crude raises WPI with a 1-month lag”

becomes:

```text
Node: brent_crude { name: "Brent Crude Oil", unit: "USD/barrel", source: "EIA/Markets" }
Node: wpi_all     { name: "WPI All Commodities", unit: "% YoY", source: "Office of Economic Adviser" }
Edge: brent_crude --[ lag=1 month, sign=+, confidence=0.95, mechanism="fuel & input costs" ]--> wpi_all
```

That is the whole idea. A graph of **what affects what, how fast, in which direction, and why**.

## 1.2 Why not just use a table / SQL database?

A normal table is good for:

```text
date       | indicator   | value
2024-10-01 | CPI         | 4.26
2024-11-01 | CPI         | 4.50
```

But it cannot directly answer:

- “If crude spikes, what breaks **next**, and then what breaks **after that**?”
- “What is the shortest transmission chain from monsoon → food inflation?”
- “What are all downstream victims of a repo-rate hike?”

You would need many painful SQL joins. A knowledge graph stores those joins **as first-class edges**, so traversal is natural:

```text
brent_crude → trade_balance → usd_inr
brent_crude → wpi_all → cpi_headline → repo_rate → bank_credit → iip_growth → gdp_growth
```

That chain is exactly what macroeconomics is: **transmission channels**.

## 1.3 Basic vocabulary (answer to “what do people mean by…”)

| Term | Meaning | Example here |
| :--- | :--- | :--- |
| **Node / Vertex** | An entity | `in.macro.prices.cpi_headline` |
| **Edge / Link** | Directed relation | `cpi_headline → repo_rate` |
| **Directed** | Arrow has direction (cause → effect) | Crude affects WPI, not reverse |
| **MultiDiGraph** | Multiple directed edges allowed between same nodes | Two different studies could give two edges WPI→CPI |
| **Ontology** | The allowed vocabulary/schema: what node types and edge types exist | `ontology.py` defines 20 indicators + 12 edges |
| **Property graph** | Nodes/edges carry key-value data | `lag_months`, `elasticity`, `confidence`, `mechanism` |
| **Traversal** | Walking along edges | “Find all descendants of crude” |
| **Shortest path** | Fewest-hop cause→effect route | `get_shortest_transmission_path()` |
| **Neighborhood** | Direct causes + direct effects | `get_causal_neighborhood()` |
| **Descendants** | Everything reachable downstream | `get_downstream_impacts()` |

## 1.4 What does the graph look like in Macrograph-AI?

### Nodes: canonical indicators

Defined in `backend/core/knowledge_graph/ontology.py` → class `MacroeconomicOntology`.

Each indicator is a `CanonicalIndicator` (see `backend/core/data/schema.py`):

```python
CanonicalIndicator(
  indicator_id="in.macro.prices.cpi_headline",
  name="All India CPI Combined Headline Inflation",
  sector=SectorEnum.PRICES_INFLATION,
  unit="% YoY",
  frequency="monthly",
  source_authority="MoSPI"
)
```

Naming convention:

```text
in.macro.<domain>.<short_name>
in.macro.prices.brent_crude
in.macro.monetary.repo_rate
in.macro.external.usd_inr
in.macro.agri.monsoon_departure
```

Current ontology has ~20 nodes across 8 domains:

- Real: `gdp_growth`, `iip_growth`, `gfcf_investment`
- Prices: `cpi_headline`, `cpi_food`, `wpi_all`, `brent_crude`
- Monetary/Banking: `repo_rate`, `bank_credit_growth`
- Fiscal: `debt_to_gdp`, `central_capex`
- External: `forex_reserves`, `usd_inr`, `trade_balance`
- Capital markets: `nifty_50`, `bank_nifty`, `india_vix`
- Agriculture: `monsoon_departure`, `foodgrain_production`
- Labour: `epfo_additions`

Each node stores: `name, sector, subsector, unit, frequency, source_authority`. This enforces **single source of truth** — e.g. CPI is owned by Prices, RBI repo by Monetary.

### Edges: causal transmission links

Each edge is a `CausalRelationship`:

```python
CausalRelationship(
  source_indicator_id="in.macro.prices.brent_crude",
  target_indicator_id="in.macro.prices.wpi_all",
  relation_type=CausalRelationType.LAGGED_RELATIONSHIP,
  transmission_lag_months=1,
  elasticity_sign="+",
  empirical_p_value=0.001,
  confidence_score=0.95,
  mechanism_description="Crude surge passes into fuel & manufacturing input costs.",
  documented_assumptions=["Excise taxes constant"]
)
```

So every arrow answers 5 questions:

1. **What → what?** (`source → target`)
2. **How strong / how sure?** (`confidence_score`, `p_value`)
3. **Which direction?** (`elasticity_sign`: `+` moves together, `-` moves opposite)
4. **How fast?** (`transmission_lag_months`)
5. **Why? Under what assumption?** (`mechanism_description`, `documented_assumptions`)

### The 3 stages encoded in this project

From `ontology.py`:

**Stage 1 — Core inflation chain:**

```text
brent_crude --(+ ,1M)--> wpi_all --(+ ,2M)--> cpi_headline --(+ ,1M)-->
repo_rate --(- ,3M)--> bank_credit_growth --(+ ,2M)--> iip_growth --(+ ,1M)--> gdp_growth
```

Read it as: oil shock → wholesale costs → retail inflation → RBI hikes → credit slows → industry slows → GDP slows.

**Stage 2 — External / fiscal / markets:**

```text
brent_crude --(- ,1M)--> trade_balance --(+ ,1M)--> usd_inr
repo_rate --(- ,1M)--> bank_nifty
central_capex --(+ ,2M)--> gfcf_investment
```

**Stage 3 — Agriculture & food:**

```text
monsoon_departure --(+ ,3M)--> foodgrain_production --(- ,2M)--> cpi_food
```

Good monsoon → more grain → lower food inflation (hence negative sign).

## 1.5 How is it built in code? Two engines, one ontology

There is **one ontology**, **two graph stores**:

```text
ontology.py  (the truth: nodes + edges list)
    ├── networkx_engine.py  (fast in-memory graph for queries)
    └── neo4j_store.py      (persistent graph DB, optional)
```

### A. `NetworkXGraphEngine` — the workhorse

File: `backend/core/knowledge_graph/networkx_engine.py`

- Uses `networkx.MultiDiGraph()` — in-process, zero-latency, perfect for API + LangGraph.
- `_build_graph()`: adds every indicator as node, every `CausalRelationship` as edge with `relation_type, lag_months, elasticity, confidence, mechanism`.
- Key methods:

| Method | What it does | Used where |
| :--- | :--- | :--- |
| `get_shortest_transmission_path(src, dst)` | BFS shortest path + picks highest-confidence edge per hop | `GET /api/v1/kg/path`, orchestrator enrichment |
| `get_causal_neighborhood(id, depth=2)` | Direct causes (predecessors) + effects (successors) | Sector-agent context |
| `get_downstream_impacts(shock_id)` | All `descendants()`, total lag = sum(lags), cumulative confidence = product(confidences) | Scenario simulation, `GET /api/v1/kg/impacts` |
| `generate_mermaid_diagram(focus_ids)` | Emits `graph LR` Mermaid for frontend report | Synthesis node report Section 3 |

Cumulative confidence example: path with 0.95 → 0.90 → 0.95 gives `0.95*0.90*0.95 ≈ 0.81`. Longer chains are less certain — mathematically explicit.

### B. `Neo4jKnowledgeGraphStore` — persistence

File: `backend/core/knowledge_graph/neo4j_store.py`

- For durable storage with Cypher constraints when `NEO4J_URI` is configured (`backend/core/config.py`).
- `sync_ontology()` seeds Neo4j from the same ontology, so NetworkX and Neo4j never diverge.
- If Neo4j is absent, the platform still works fully on NetworkX.

This dual design answers “why two graphs?”: **speed (NetworkX) + durability/sharing (Neo4j)**.

## 1.6 How it is useful HERE (concrete)

1. **Cross-sector reasoning without hallucinating links.** The orchestrator (`backend/core/orchestrator/graph.py` → `kg_causal_enrichment_node`) takes observations collected via A2A (e.g. `brent_crude` + `cpi_headline`), looks up every pair `(u,v)` in the graph, and attaches the verified chain, lag, and mechanism. The LLM never invents “crude affects GDP” — it cites the traversed `relation_id`s.

2. **APIs for UI + agents:**
   - `GET /api/v1/kg/path?source_id=...&target_id=...` → hops, total lag, relations.
   - `GET /api/v1/kg/impacts?shock_id=...` → every reachable target + hops + lag + confidence + mechanism chain.
   - `GET /health` exposes `knowledge_graph_nodes/edges` counts.
   - Demo: `backend/demo_platform.py` prints topology on startup.

3. **Visual explanation.** `generate_mermaid_diagram()` renders edges as `A -->|"+ (1M) [LAGGED]"| B`, embedded in the final report. Frontend/economist sees the channel, not just numbers.

4. **Anti-hallucination.** Because edges carry `documented_assumptions` + `confidence + p_value`, the synthesis node can write: “Transmission edges classified per 5-tier taxonomy…” instead of vague “crude may affect inflation”.

---

# Part 2 — Causal Reasoning / Causal Inference

## 2.1 Correlation vs Causation (the most-asked question)

- **Correlation:** “Two things move together.” Example: NIFTY and GDP often rise together. Useful but says nothing about what to *do*.
- **Causation:** “If I intervene and change X, Y will change.” Example: “If RBI hikes repo by 25 bps, bank credit growth falls after ~3 months.” That is actionable for policy.

Classic trap: ice-cream sales and drowning correlate (both rise in summer) but ice cream does not cause drowning. Heat is the confounder.

Economics is full of confounders, lags, and feedback loops, so Macrograph-AI **never claims causality lightly**. It uses a 5-level ladder (next section).

## 2.2 The 5-tier causal taxonomy (core to this project)

Defined in `backend/core/data/schema.py` → `CausalRelationType`:

| Tier | Name | What it means | Example in ontology |
| :--- | :--- | :--- | :--- |
| 1 | `THEORY` | Textbook/consensus mechanism, no fresh statistical test here | `brent_crude → trade_balance` (“India imports ~85% crude”) |
| 2 | `STATISTICAL_ASSOCIATION` | Correlation with p-value, contemporaneous | `bank_credit → iip_growth` (p=0.025) |
| 3 | `LAGGED_RELATIONSHIP` | Cross-correlation at lag k: X today predicts Y in k months | `brent → wpi` (lag 1M, p=0.001) |
| 4 | `GRANGER_PREDICTIVE` | Granger test: past X improves forecast of Y beyond past Y alone | `wpi → cpi` (lag 2M, p=0.008); `repo → credit` (p=0.015) |
| 5 | `STRUCTURAL_CAUSAL_MODEL` (SCM/DAG) | Explicit structural model with identification assumptions (e.g. RBI mandate, national-accounts identity) | `cpi → repo` (RBI 4%±2% mandate); `iip → gdp` (accounting identity) |

Higher tier = stronger claim = needs stronger assumptions/data. The report always prints which tier each edge is, so a reader knows “is this proven or textbook logic?”.

## 2.3 What is Granger causality? (simple + technical)

**Simple:** “Does the history of X help me predict Y better than history of Y alone?” If yes, X *Granger-causes* Y.

**Technical (`backend/core/econometrics/causal_engine.py` → `test_granger_causality`):**

1. Take a DataFrame with columns `[effect, cause]`, drop NaNs, require N ≥ 10.
2. Call `statsmodels.tsa.stattools.grangercausalitytests(subset, maxlag=2)`.
3. For each lag, read `ssr_ftest` p-value.
4. Pick lag with smallest p-value. If `p < 0.05`, `is_significant=True`.

```python
results = grangercausalitytests(subset, maxlag=2, verbose=False)
# per lag: p_val = lag_res[0]["ssr_ftest"][1]
```

Important nuance the code respects: Granger is **predictive causality**, not proof of structural causation. That is why it is tier 4, not tier 5. True SCM needs a DAG + identification (no hidden confounder, correct functional form).

Other methods mentioned/imported: `VAR` (Vector Autoregression) for multi-variable dynamics. The engine is structured to add VAR/IRF estimation later.

## 2.4 What is a DAG / SCM?

- **DAG = Directed Acyclic Graph:** arrows show causal direction, no cycles (you cannot cause yourself indirectly). The ontology is designed as a DAG: crude → WPI → CPI → repo → credit → IIP → GDP.
- **SCM = Structural Causal Model:** a DAG + equations + assumptions (e.g. “RBI follows flexible inflation targeting”). In code, SCM edges are those with `relation_type=STRUCTURAL_CAUSAL_MODEL` + explicit `documented_assumptions`.

## 2.5 How causal simulation works here (impulse propagation)

File: `backend/core/econometrics/causal_engine.py` → `simulate_scenario()`.

This answers: “If crude jumps +$20, what happens to CPI, repo, credit, GDP, INR… and when?”

**Inputs:**

```python
simulate_scenario(
  scenario_name="Oil Surge",
  shock_variable="in.macro.prices.brent_crude",
  shock_magnitude=20.0,
  horizon_periods=4,
  baseline_values={ "in.macro.prices.brent_crude": 78.5, "in.macro.prices.cpi_headline": 4.26, ... }
)
```

**Steps:**

1. `downstream_impacts = graph.get_downstream_impacts(shock_variable)` — find all victims.
2. Shock the source: `shocked = baseline + magnitude`.
3. For each target, get shortest path, then compute attenuated impact:

```python
cum_multiplier = 1.0
for r in path:
    sign = +1 if r.elasticity_sign == "+" else -1
    decay = 0.55 * r.confidence_score   # each hop loses strength
    cum_multiplier *= (sign * decay)

delta = shock_magnitude * cum_multiplier * 0.15
shocked_target = baseline + delta
CI = [shocked - |delta|*0.25, shocked + |delta|*0.25]
```

Why this formula? Each hop multiplies by confidence-discounted decay, so distant effects are smaller and cumulative confidence shrinks. The `0.15` is a scaling damper to avoid explosive macro claims; `±25%` gives a confidence band.

4. Return `ScenarioResult` with `forecasted_impacts` + `provenance_chain` (relation IDs traversed). The API `POST /api/v1/simulate` and orchestrator `scenario_shock` both use this.

**Worked mini-example:** Shock crude +20 with path `brent(0.95) → wpi(0.90) → cpi`:

- Hop1: `+1 * 0.55*0.95 = +0.5225`
- Hop2: `+1 * 0.55*0.90 = +0.495` → cumulative `0.5225*0.495 ≈ 0.2587`
- `delta = 20 * 0.2587 * 0.15 ≈ +0.78` → CPI `4.26 → ~5.04`, lag `1+2=3M`. That matches intuition: oil shock lifts CPI materially but not 1:1.

## 2.6 How causality is useful HERE

- **Policy counterfactuals:** `repo → credit (−, 3M)` lets the Monetary/Finance agents debate “what if RBI hikes?”.
- **Honest uncertainty:** every edge shows `p_value + confidence + lag + assumptions`, and every simulation shows `confidence_band + lag + mechanism_summary`. No black-box “AI predicts GDP = X”.
- **Orchestrator grounding:** `kg_causal_enrichment_node` runs *before* LLM synthesis, so the LLM’s narrative must be consistent with graph paths + simulation table. Final report Section 4 is a shock table: `Target | Baseline | Shocked Peak | Delta | Lag | CI`.
- **Anti-confusion guard:** code comments and Agriculture agent explicitly state “Co-movement is descriptive and does not by itself establish causality.” Tiers prevent overstating.

## 2.7 Limits (what causality here does NOT do)

- Granger ≠ true causation if there is an omitted variable or structural break.
- Simulation is **graph-propagated impulse**, not a full DSGE/VAR estimated on live data each time. It is explainable by design, not a substitute for RBI-grade econometrics.
- Lags/confidences are curated priors in the ontology; they should be re-estimated as fresh DuckDB time series arrive.

---

# Part 3 — GraphRAG (Graph + Retrieval-Augmented Generation)

## 3.1 What is RAG? (prerequisite)

**LLM problem:** an LLM alone hallucinates numbers and does not know today’s CPI or what the RBI Governor just said.

**RAG = Retrieval-Augmented Generation:**

```text
User query → Retriever searches trusted docs/DB → Top passages fed to LLM → LLM answers WITH citations
```

Instead of answering from memory, the model answers from **retrieved evidence**.

## 3.2 What is a vector DB / embedding? (prerequisite)

- **Embedding:** turn text into a number vector (list of floats) capturing meaning. Similar meanings → nearby vectors.
- **Vector DB (here: Qdrant):** stores millions of such vectors + original text, answers “find passages *semantically* similar to this query” in milliseconds.

In Macrograph-AI, Qdrant is the **policy-language memory**:

- RBI MPC minutes, Governor press conferences
- Union Budget speeches, fiscal statements
- Economic Survey, RBI Annual Reports, PLFS/NSSO reports

So a query like “RBI stance on food inflation?” retrieves the Governor’s verbatim line “food volatility is transitory”, not a hallucinated paraphrase.

## 3.3 What is GraphRAG then? (RAG + Knowledge Graph)

Naive RAG retrieves **disconnected chunks**: “CPI was 4.8%” here, “monsoon deficit 18%” there. It misses *how they connect*.

**GraphRAG = retrieve over a graph + retrieve over text, then generate.**

```text
Naive RAG:   query → vector search → chunks → LLM
GraphRAG:    query → vector search (narrative) + graph traversal (structure/causality) → LLM
```

Concretely:

- **Graph gives structure:** `monsoon → foodgrain → cpi_food → cpi_headline → repo_rate` + lags + mechanisms.
- **Vectors give narrative:** RBI circular wording, Budget speech context, MPC vote rationale.
- **LLM fuses both:** numbers + chains + quotes, each cited.

Microsoft popularized the term “GraphRAG”, but the pattern is general. This project implements that pattern with its own stack: **NetworkX/Neo4j (graph) + Qdrant (vectors) + DuckDB/FastMCP (numbers) + PydanticAI/Groq LLM (synthesis)**.

## 3.4 How RAG / GraphRAG is wired (or designed) HERE

Architecture intent (see `README.md`, `docs/high-level-overview.md`, `.agents/AGENTS.md`):

```text
Sector Agent
   ├── FastMCP → DuckDB / MOSPI / RBI DBIE / Agmarknet / IMD   (numbers)
   ├── Qdrant via MCP → policy passages                        (words)
   └── Knowledge Graph → transmission paths                    (structure)
                    ↓
         Orchestrator synthesis (cited report)
```

- **FastMCP = agent↔data; A2A = agent↔agent.** Agents never fetch numbers from each other; they fetch from MCP (DuckDB/Qdrant/APIs) and share conclusions via A2A. This is a strict rule.
- **Qdrant role:** when Monetary needs “why did RBI hold repo at 6.5% despite 4.8% food CPI?”, it pulls the MPC statement from Qdrant. Canonical example in docs:

```text
Prices → MOSPI MCP: Food CPI +4.8% YoY
Agriculture → IMD MCP: monsoon −18%, Kharif sowing −8%; Agmarknet: tomato +120%, onion +60%
Monetary → RBI DBIE MCP: repo 6.5%, stance "withdrawal of accommodation"
Monetary → Qdrant RAG: Governor: "Food volatility is transitory"
→ Final cited paragraph fuses all four.
```

- **Current maturity note (honest):** graph + DuckDB + MCP + orchestrator paths are fully implemented (`networkx_engine.py`, `causal_engine.py`, `orchestrator/graph.py`, `main.py`). Qdrant corpus + query path is **architecturally specified** (tech stack, AgentCard templates referencing “Reads MPC statements from Qdrant”, finance `README.md` “Qdrant Policy Corpus”) but noted in `.agents/MEMORY.md` as “designed but not yet wired” in some branches. Treat Qdrant here as the **designated narrative-evidence layer** for GraphRAG; the graph + structured-RAG half is live.

## 3.5 Why GraphRAG matters for macro questions

| Question type | Naive LLM | Naive RAG only | GraphRAG (this project) |
| :--- | :--- | :--- | :--- |
| “What is current CPI?” | May hallucinate | Retrieves CPI chunk | Retrieves CPI via MCP/DuckDB + cites agent/tool/period |
| “Why is food inflation rising?” | Generic guess | Two unlinked chunks | Graph chain `monsoon→grain→food CPI` + IMD/Agmarknet numbers |
| “How will RBI respond?” | Generic Taylor-rule talk | Governor quote alone | Quote **plus** `cpi→repo` SCM edge (4%±2% mandate) + lag |
| “Impact of +$20 oil?” | Single number | No propagation | Full downstream table with lags/CIs/mechanisms + Mermaid |

In short: **numbers without narrative are dry; narrative without structure is untrustworthy. GraphRAG gives both.**

## 3.6 Minimal mental model

```text
1. Decompose query → sectors (orchestrator decompose_node)
2. Parallel A2A → sector agents fetch via FastMCP (DuckDB/APIs) + Qdrant (docs)
3. KG enrichment → shortest paths + downstream impacts + Mermaid (kg_causal_enrichment_node)
4. Causal simulation (optional) → shock propagation table (causal_engine)
5. Synthesis → cited markdown report with matrix + graph + scenario + taxonomy notes
```

Endpoints mapping to this: `POST /api/v1/analyze` (full pipeline), `POST /api/v1/simulate` (step 4 alone), `GET /api/v1/kg/path|impacts` (step 3 alone), `GET /a2a/registry` (discovery for step 2).

---

# Part 4 — How All Three Work Together in Macrograph-AI

## 4.1 End-to-end example: “Crude +$20 — impact on CPI, repo, credit, GDP, INR?”

1. **Decompose:** query hits keywords `crude/oil` → Prices, `repo/RBI` → Monetary, `credit` → Finance/Banking, `GDP/IIP` → Real, `USD/INR/trade` → External.
2. **A2A + MCP:** Prices pulls CPI/WPI, Monetary pulls repo/M3, External pulls trade/USDs, etc. Each returns `Artifact { metrics, provenance_hash }`.
3. **KG traversal:** for every pair of collected IDs, `get_shortest_transmission_path()` finds e.g. `brent→wpi→cpi→repo→credit→iip→gdp` (6 hops, total lag ~10M) and `brent→trade→usd_inr`. `get_downstream_impacts(brent)` ranks all victims by hops/confidence.
4. **Causal simulation:** `simulate_scenario(shock_variable=brent_crude, magnitude=20)` produces baselines → shocked peaks + deltas + CIs + lags (see Section 2.5 math).
5. **RAG grounding (design):** Monetary attaches Qdrant MPC excerpt on oil pass-through; Fiscal attaches Budget speech on fuel subsidies.
6. **Synthesis:** LLM writes executive narrative **constrained** by steps 2–5, then report appends: indicator matrix with hashes, Mermaid channels, shock table, taxonomy note. Every number traceable to agent + tool + period.

## 4.2 File map (where to look)

| Concept | File | Key symbol |
| :--- | :--- | :--- |
| Indicator/edge schemas, 5-tier enum | `backend/core/data/schema.py` | `CanonicalIndicator`, `CausalRelationship`, `CausalRelationType`, `ScenarioResult` |
| Node/edge vocabulary | `backend/core/knowledge_graph/ontology.py` | `MacroeconomicOntology`, `ontology` |
| In-memory traversal | `backend/core/knowledge_graph/networkx_engine.py` | `NetworkXGraphEngine`, `graph_engine` |
| Persistent graph | `backend/core/knowledge_graph/neo4j_store.py` | `Neo4jKnowledgeGraphStore` |
| Granger + simulation | `backend/core/econometrics/causal_engine.py` | `CausalEconometricEngine`, `causal_engine` |
| Orchestrator wiring | `backend/core/orchestrator/graph.py` | `kg_causal_enrichment_node`, `macro_orchestrator_graph` |
| HTTP surface | `backend/main.py` | `/api/v1/analyze`, `/api/v1/simulate`, `/api/v1/kg/path`, `/api/v1/kg/impacts` |
| RAG design | `docs/high-level-overview.md`, `README.md`, sector READMEs | “Knowledge Layer — RAG (Qdrant)” |

## 4.3 Design choices worth defending in a viva

- **Why MultiDiGraph not simple Graph?** Multiple evidence tiers can link same pair (e.g. theory + Granger). Highest-confidence edge wins per hop.
- **Why confidence product + lag sum?** Transparent uncertainty decay over longer chains; total delay matters for policy (“repo affects credit in ~3M, GDP much later”).
- **Why separate A2A vs MCP?** Prevents agents inventing each other’s data; KG then reasons over *verified* inputs only.
- **Why 5 tiers not binary causal/not?** Economics rarely has RCTs; grading evidence avoids both naivety (“correlation = cause”) and nihilism (“nothing is causal”).

---

# Quick FAQ / Viva Questions

**Q: Is a knowledge graph a database?**
A: It is a data *model* + store. Here it is implemented once as NetworkX objects (in-memory) and optionally as Neo4j (persistent DB with Cypher). DuckDB remains the numeric fact store; the graph stores *relations between* those facts.

**Q: What is an ontology vs a knowledge graph?**
A: Ontology = schema/vocabulary (what *can* exist). Knowledge graph = populated instance (what *does* exist + live values). Here `ontology.py` is both seed vocabulary and initial instance.

**Q: Directed or undirected? Why?**
A: Directed (`MultiDiGraph`), because causation has direction. `predecessors()` = causes, `successors()` = effects.

**Q: Correlation vs Granger vs SCM?**
A: Correlation = co-move. Granger = past-X improves forecast of Y (tier 4, tested via `grangercausalitytests`). SCM = structural equation + identification assumptions (tier 5, e.g. RBI mandate, accounting identity).

**Q: What does elasticity sign `+`/`-` mean?**
A: Direction only, not size. `+`: both move same way (crude↑ → WPI↑). `-`: opposite (repo↑ → credit↓; grain↑ → food CPI↓).

**Q: What is transmission lag?**
A: Months for cause to show in effect. Summed along a path to get total delay. Critical for “when will GDP feel today’s oil shock?”.

**Q: What is GraphRAG in one line?**
A: RAG over text **plus** traversal over a knowledge/causal graph, fused by the LLM with citations for both.

**Q: Why Qdrant + graph instead of just stuffing PDFs into the LLM?**
A: Scale (millions of passages searchable by meaning), freshness (update docs without retraining), verifiability (verbatim excerpts + hashes), and structure (graph explains *why* chunks relate).

**Q: What happens if data is missing?**
A: “No Source, No Answer”: agent returns `UNAVAILABLE`, no number is invented. Graph paths still show *expected* channels, clearly labeled as theoretical/predictive, not observed.

**Q: How do I demo each piece?**
A: `python backend/demo_platform.py` (graph topology) → `GET /api/v1/kg/path` → `GET /api/v1/kg/impacts` → `POST /api/v1/simulate` → `POST /api/v1/analyze` (full GraphRAG report with Mermaid).

---

*End of document. For implementation details, read the files in Section 4.2 in order: `schema.py` → `ontology.py` → `networkx_engine.py` → `causal_engine.py` → `orchestrator/graph.py`.*
