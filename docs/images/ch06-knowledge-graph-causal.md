# Chapter 6: Causal Knowledge Graph and Scenario Engine - Figures

Numbers in this chapter come from the ontology in `backend/core/knowledge_graph/ontology.py` and from a real run of `simulate_scenario` on 2026-10-12 (Brent +20 USD per barrel, default baselines). Re-run the engine before final submission if the ontology changes.

---

## Figure 6.1: The causal knowledge graph (20 indicators, 12 edges)

<!-- fig: 6.1 knowledge-graph -->

- **Caption:** Figure 6.1: Causal transmission graph of 20 canonical indicators connected by 12 typed edges. Edge labels show lag in months and elasticity sign.
- **Use in:** 6.1 Ontology design. The most important figure of this chapter; use a full page in landscape.
- **Description:** Nodes are grouped by sector. Five indicators are currently isolated (NIFTY 50, India VIX, forex reserves, debt-to-GDP and EPFO additions); they are valid nodes without edges and appear at the bottom. Note: the `trade_balance -> usd_inr` sign is flagged in the code for review, and the edge statistics are curated priors (see Chapter 9 limitations).

```mermaid
flowchart TB
    subgraph AGR["Agriculture"]
        MON["Monsoon departure"]
        FGP["Foodgrain production"]
    end
    subgraph PRC["Prices"]
        BRT["Brent crude"]
        WPI["WPI all"]
        CPI["CPI headline"]
        CPF["CPI food"]
    end
    subgraph MNT["Monetary"]
        REP["Repo rate"]
        BCG["Bank credit growth"]
    end
    subgraph EXT["External"]
        TRB["Trade balance"]
        USD["USD/INR"]
    end
    subgraph CAP["Capital markets"]
        BNF["Bank NIFTY"]
    end
    subgraph FIS["Fiscal"]
        CPX["Central capex"]
    end
    subgraph REA["Real"]
        GFC["GFCF investment"]
        IIP["IIP growth"]
        GDP["GDP growth"]
    end
    BRT -->|"1M +"| WPI
    WPI -->|"2M +"| CPI
    CPI -->|"1M +"| REP
    REP -->|"3M -"| BCG
    BCG -->|"2M +"| IIP
    IIP -->|"1M +"| GDP
    BRT -->|"1M -"| TRB
    TRB -->|"1M +"| USD
    REP -->|"1M -"| BNF
    CPX -->|"2M +"| GFC
    MON -->|"3M +"| FGP
    FGP -->|"2M -"| CPF
    subgraph ISO["Nodes without edges"]
        N1["NIFTY 50"]
        N2["India VIX"]
        N3["Forex reserves"]
        N4["Debt to GDP"]
        N5["EPFO additions"]
    end
```

---

## Figure 6.2: Five-tier causal evidence taxonomy

<!-- fig: 6.2 causal-taxonomy -->

- **Caption:** Figure 6.2: Five-tier classification of causal relationship strength used for knowledge-graph edges.
- **Use in:** 6.2 Edge classification.
- **Description:** Tiers rise from qualitative theory to an identified structural model. Edge counts in the current ontology are in brackets: THEORY 3, STATISTICAL_ASSOCIATION 3, LAGGED_RELATIONSHIP 2, GRANGER_PREDICTIVE 2, STRUCTURAL_CAUSAL_MODEL 2. The tier is currently assigned by hand; the edge audit tests it empirically.

```mermaid
flowchart BT
    T1["Tier 1 THEORY (3)<br/>qualitative economic consensus"]
    T2["Tier 2 STATISTICAL_ASSOCIATION (3)<br/>contemporaneous correlation with p-value"]
    T3["Tier 3 LAGGED_RELATIONSHIP (2)<br/>cross-correlation at lag k"]
    T4["Tier 4 GRANGER_PREDICTIVE (2)<br/>Granger F-test predictive causality"]
    T5["Tier 5 STRUCTURAL_CAUSAL_MODEL (2)<br/>explicit SCM or DAG with identification conditions"]
    T1 --> T2 --> T3 --> T4 --> T5
```

---

## Figure 6.3: Anatomy of a causal edge and validation rules

<!-- fig: 6.3 edge-anatomy -->

- **Caption:** Figure 6.3: Fields of a causal relationship and the validation rules enforced when the ontology loads.
- **Use in:** 6.2 Edge classification / 6.3 Validation.
- **Description:** Relation ids are deterministic (uuid5 of source, target and type) so provenance and Neo4j merge keys survive restarts. Invalid edges stop the application from building the graph.

```mermaid
flowchart TB
    EDGE["CausalRelationship<br/>relation_id: rel-8hex, deterministic uuid5<br/>source_indicator_id, target_indicator_id<br/>relation_type: 5-tier enum<br/>transmission_lag_months: integer, at least 0<br/>elasticity_sign: plus or minus<br/>empirical_p_value: optional, None only for THEORY<br/>confidence_score: 0 to 1<br/>mechanism_description: at least 10 characters<br/>documented_assumptions: list"]
    EDGE --> V{"ontology.validate()"}
    V --> R1["reject self-loop"]
    V --> R2["reject unknown endpoint"]
    V --> R3["reject duplicate relation id"]
    V --> R4["reject bad id pattern or sign"]
    V -->|"all pass"| OK["edge added to NetworkX graph"]
```

---

## Figure 6.4: Path and downstream-impact queries

<!-- fig: 6.4 graph-queries -->

- **Caption:** Figure 6.4: Algorithms for shortest transmission path and downstream impact enumeration.
- **Use in:** 6.4 Graph queries.
- **Description:** Shortest path is by hop count. If two parallel edges exist between a pair, the highest-confidence edge is used. Impacts are all descendants of the shocked node, each with hop count, summed lag and the product of edge confidences; results are sorted by hops, then by confidence.

```mermaid
flowchart TB
    A["get_downstream_impacts(shock_id)"] --> B{"Node in graph?"}
    B -->|"no"| Z["return empty list"]
    B -->|"yes"| C["descendants(shock_id)"]
    C --> D["for each target"]
    D --> E["shortest_path by hops"]
    E --> F["pick highest-confidence edge per hop"]
    F --> G["total lag = sum of edge lags"]
    F --> H["cumulative confidence = product of edge confidences"]
    G --> I["impact record: target, hops, lag, confidence, mechanism chain"]
    H --> I
    I --> J["sort by hops then by confidence descending"]
```

---

## Figure 6.5: Scenario propagation algorithm

<!-- fig: 6.5 scenario-algorithm -->

- **Caption:** Figure 6.5: Graph-attenuation scenario algorithm.
- **Use in:** 6.5 Scenario simulation.
- **Description:** For each downstream target, the multiplier is the product over hops of sign x 0.55 x confidence; the delta is shock x multiplier x 0.15. The band is plus or minus 25% of the delta. This is a transparent heuristic, not an econometric impulse response; label it as such in the report.

```mermaid
flowchart TB
    IN["Inputs: shock variable, magnitude, baselines"] --> BASE["Shocked variable: baseline plus magnitude"]
    IN --> DS["downstream impacts from graph"]
    DS --> L["for each target"]
    L --> P["path = shortest transmission path"]
    P --> M["multiplier = product over hops of<br/>sign times 0.55 times confidence"]
    M --> D["delta = magnitude times multiplier times 0.15"]
    D --> SP["shocked peak = target baseline plus delta"]
    SP --> CB["band = shocked peak plus or minus 25 percent of delta"]
    CB --> OUT["forecasted_impacts[target]<br/>baseline, shocked_peak, delta, band, lag, confidence"]
    P --> PRV["provenance_chain: relation ids used, first-seen order"]
```

---

## Figure 6.6: Worked example: Brent +20 USD per barrel

<!-- fig: 6.6 worked-example -->

- **Caption:** Figure 6.6: Simulated transmission of a USD 20 per barrel Brent crude increase (default baselines).
- **Use in:** 6.6 Case study.
- **Description:** Values are the engine's actual output. Example check, first hop: 20 x (0.55 x 0.95) x 0.15 = 1.57 added to the WPI baseline 2.45 gives 4.02. Report honestly that USD/INR falls in this run: that is a consequence of the `+` sign on `trade_balance -> usd_inr`, which the code flags as under review. Fix the sign and re-run before submission, or discuss it as a known limitation.

```mermaid
flowchart TB
    B["Brent crude<br/>78.50 to 98.50"]
    W["WPI all<br/>2.45 to 4.02<br/>delta +1.57, lag 1M"]
    C["CPI headline<br/>4.26 to 5.04<br/>delta +0.78, lag 3M"]
    R["Repo rate<br/>6.25 to 6.66<br/>delta +0.41, lag 4M"]
    K["Bank credit growth<br/>13.80 to 13.60<br/>delta -0.20, lag 7M"]
    I["IIP growth<br/>4.20 to 4.11<br/>delta -0.09, lag 9M"]
    G["GDP growth<br/>5.40 to 5.35<br/>delta -0.05, lag 10M"]
    T["Trade balance<br/>-22.50 to -24.02<br/>delta -1.52, lag 1M"]
    U["USD/INR<br/>86.40 to 85.68<br/>delta -0.72, lag 2M"]
    N["Bank NIFTY<br/>51500 to 51499.81<br/>delta -0.19, lag 5M"]
    B --> W --> C --> R --> K --> I --> G
    B --> T --> U
    R --> N
```

---

## Figure 6.7: Impact of the shock by transmission lag (chart)

<!-- fig: 6.7 impact-chart -->

- **Caption:** Figure 6.7: Simulated deltas of selected indicators by cumulative transmission lag (Brent +20).
- **Use in:** 6.6 Case study (results).
- **Description:** A bar chart of the deltas from Figure 6.6, ordered by lag. The units differ by indicator (percentage points or index points), so the chart conveys pattern, not comparable magnitude. State that under the figure. The engine is unit-blind; the Chapter 9 limitations discuss this.

```mermaid
xychart-beta
    title "Simulated delta by cumulative lag in months (Brent +20)"
    x-axis ["WPI 1M", "Trade 1M", "USD/INR 2M", "CPI 3M", "Repo 4M", "Credit 7M", "IIP 9M", "GDP 10M"]
    y-axis "Delta in indicator units" -2 --> 2
    bar [1.57, -1.52, -0.72, 0.78, 0.41, -0.2, -0.09, -0.05]
```

---

## Figure 6.8: Scenario fan: confidence of the path decays with hops

<!-- fig: 6.8 confidence-decay -->

- **Caption:** Figure 6.8: Cumulative confidence of transmission paths from Brent crude by number of hops.
- **Use in:** 6.6 Case study.
- **Description:** Cumulative confidence is the product of edge confidences. Values are from the engine run: WPI 0.95 (1 hop), CPI 0.85 (2 hops), repo 0.81, credit 0.71, IIP 0.59, GDP 0.57. It shows why distant effects should be read with more caution, a point worth making in the discussion.

```mermaid
xychart-beta
    title "Cumulative path confidence from Brent crude"
    x-axis ["WPI (1 hop)", "CPI (2)", "Repo (3)", "Credit (4)", "IIP (5)", "GDP (6)"]
    y-axis "Cumulative confidence" 0 --> 1
    line [0.95, 0.85, 0.81, 0.71, 0.59, 0.57]
```

---

## Figure 6.9: Neo4j mirroring

<!-- fig: 6.9 neo4j-sync -->

- **Caption:** Figure 6.9: Optional synchronisation of the ontology to a Neo4j database at gateway start.
- **Use in:** 6.7 Persistence.
- **Description:** Neo4j is disabled unless `NEO4J_URI` is set. The sync is the only write path and is idempotent (MERGE on stable ids), with three retry attempts. NetworkX remains the query engine for the orchestrator.

```mermaid
sequenceDiagram
    participant GW as Gateway lifespan
    participant ST as Neo4jKnowledgeGraphStore
    participant ON as MacroeconomicOntology
    participant DB as Neo4j server
    GW->>ST: enabled?
    alt NEO4J_URI empty
        ST-->>GW: disabled, skip
    else enabled
        GW->>ST: sync_ontology (thread pool)
        ST->>ON: read indicators and relationships
        ST->>DB: create uniqueness constraint
        loop each indicator
            ST->>DB: MERGE node
        end
        loop each relationship
            ST->>DB: MERGE AFFECTS edge with relation_id, type, lag, sign, confidence
        end
        Note over ST,DB: up to 3 attempts with exponential backoff
        ST-->>GW: True or False
    end
```

---

## Figure 6.10: Canonical indicator id mapping

<!-- fig: 6.10 canonical-id-mapping -->

- **Caption:** Figure 6.10: Mapping of sector-native indicator names to canonical ontology identifiers.
- **Use in:** 6.8 Integration with sector agents.
- **Description:** Sector agents report observations under their own names. `CANONICAL_ID_MAP` aliases them onto canonical ids so that the orchestrator can join sector evidence to graph nodes. Only canonical nodes can have transmission paths.

```mermaid
flowchart TB
    A1["real: gdp_growth, national_income"] --> M["CANONICAL_ID_MAP"]
    A2["prices: cpi_general, cpi_headline_combined_yoy"] --> M
    A3["monetary: repo_rate, policy_repo_rate"] --> M
    A4["other sector-native names"] --> M
    M --> C1["in.macro.real.gdp_growth"]
    M --> C2["in.macro.prices.cpi_headline"]
    M --> C3["in.macro.monetary.repo_rate"]
    C1 --> G{"Node in knowledge graph?"}
    C2 --> G
    C3 --> G
    G -->|"yes"| P["eligible for paths and live baselines"]
    G -->|"no"| X["kept as observation, no path"]
```

---

## Figure 6.11: Knowledge-graph enrichment node

<!-- fig: 6.11 enrichment-node -->

- **Caption:** Figure 6.11: Operation of the knowledge-graph causal enrichment node.
- **Use in:** 6.8 Integration.
- **Description:** Indicators from collected observations (and the shocked variable) are filtered to KG nodes; all ordered pairs are queried for a path; an optional scenario is simulated; and a Mermaid diagram for the first five nodes is produced for the report.

```mermaid
flowchart TB
    OBS["collected_observations"] --> IDS["unique indicator ids, first-seen order"]
    SH["scenario_shock"] --> ADD["add shocked variable"]
    IDS --> KGF["keep ids that are KG nodes"]
    ADD --> KGF
    KGF --> PAIR["all ordered pairs u to v"]
    PAIR --> PATH["shortest transmission path"]
    PATH --> CP["causal_paths: hops, total lag, relations"]
    KGF --> SIMQ{"scenario_shock present?"}
    SIMQ -->|"yes"| LB["live baselines"] --> SIM["simulate_scenario"]
    SIMQ -->|"no"| SKIP["no scenario"]
    KGF --> MER["generate_mermaid_diagram(first 5 ids)"]
    CP --> OUT["state update"]
    SIM --> OUT
    MER --> OUT
```
