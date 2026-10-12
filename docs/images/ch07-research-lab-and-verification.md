# Chapter 7: Research Lab, Daily Brief and Claim Verification - Figures

This chapter holds the most original parts of the project. Label every simulated output as simulated in the text; the code does the same (`SIM`, `SIMULATED`, `heuristic`).

---

## Figure 7.1: Research lab architecture

<!-- fig: 7.1 research-lab-overview -->

- **Caption:** Figure 7.1: Research lab modules, API endpoints and user-interface tabs.
- **Use in:** 7.1 Overview.
- **Description:** The research modules are pure functions over the frozen graph, the engine and series already held by the dashboard helpers. They never mutate engine state. Chat adds two of them (consensus and model card) to the final streamed event.

```mermaid
flowchart LR
    subgraph IN["Inputs"]
        KG["Knowledge graph"]
        EN["Scenario engine"]
        SE["Series provider<br/>dashboard helpers and macro_store"]
        ST["Finished orchestrator state"]
    end
    subgraph MOD["core/research"]
        TR["trajectory.py<br/>Shockwave"]
        AT["attribution.py<br/>Twin"]
        AN["anomaly.py<br/>Radar"]
        MP["mpc.py<br/>MPC"]
        ED["edge_audit.py<br/>Edge audit"]
        CO["consensus.py"]
        MC["model_card.py"]
    end
    subgraph API["Endpoints"]
        E1["POST /research/trajectory"]
        E2["POST /research/compare"]
        E3["GET /research/anomalies"]
        E4["POST /research/mpc/simulate"]
        E5["GET /research/edges/audit"]
        E6["chat done event: consensus, model_card"]
    end
    subgraph UI["UI"]
        U1["Shockwave tab"]
        U2["Twin tab"]
        U3["Radar tab"]
        U4["MPC tab"]
        U5["Graph view with audit"]
        U6["Debate DAG and model card strip"]
    end
    KG --> TR
    EN --> TR
    EN --> AT
    SE --> AN
    SE --> ED
    KG --> AN
    ST --> CO
    ST --> MC
    TR --> E1 --> U1
    AT --> E2 --> U2
    AN --> E3 --> U3
    MP --> E4 --> U4
    ED --> E5 --> U5
    CO --> E6
    MC --> E6 --> U6
```

---

## Figure 7.2: Shockwave trajectory construction

<!-- fig: 7.2 shockwave-trajectory -->

- **Caption:** Figure 7.2: Construction of monthly impact trajectories from a single scenario result.
- **Use in:** 7.2 Shockwave.
- **Description:** The engine gives one peak delta and one lag per node. The trajectory keeps the baseline until the lag month, then applies either a step to the peak or an exponential decay with a chosen half-life. The 12-month horizon is adjustable from 1 to 60 months.

```mermaid
flowchart TB
    IN["shock variable, magnitude, horizon, shape, half-life"] --> E{"Shock node in graph?"}
    E -->|"no"| EMP["empty result with explanation note"]
    E -->|"yes"| SIM["simulate_scenario"]
    SIM --> NODES["for each downstream node:<br/>baseline, peak delta, lag, hops, cumulative confidence"]
    NODES --> SH{"shape"}
    SH -->|"step"| ST["value = baseline until lag, then baseline plus delta"]
    SH -->|"decay"| DC["value = baseline plus delta times 0.5 power ((t minus lag) / half-life)"]
    ST --> SER["monthly series t = 0 to horizon"]
    DC --> SER
    NODES --> ED["edges on path with evidence class and notes"]
    SER --> OUT["trajectory payload labelled SIM and heuristic"]
    ED --> OUT
```

---

## Figure 7.3: Twin: base world versus shocked world with attribution

<!-- fig: 7.3 twin-attribution -->

- **Caption:** Figure 7.3: Comparison of the baseline and shocked worlds and per-hop attribution.
- **Use in:** 7.3 Twin.
- **Description:** Two simulations (shock 0 and shock s) give per-node deltas. For each target the path is split into hops and each hop receives a share proportional to the log of its attenuation factor, which identifies the weakest link. Sign flips (inverse edges) are counted.

```mermaid
flowchart TB
    S["shock variable and magnitude"] --> B["simulate with shock 0 (base world)"]
    S --> H["simulate with shock s (shocked world)"]
    B --> CMP["compare per node"]
    H --> CMP
    CMP --> D["delta, percent of baseline, gain per unit"]
    CMP --> L["lag months from impact list"]
    CMP --> P["for each target: shortest path"]
    P --> LG["hop weight = log of abs(0.55 times confidence)"]
    LG --> SH["share per hop = hop weight / sum of weights"]
    SH --> WK["weakest link = hop with largest share"]
    P --> SF["sign flips = count of inverse edges"]
    D --> OUT["payload: base, shocked, delta, attribution"]
    WK --> OUT
    SF --> OUT
```

---

## Figure 7.4: Anomaly radar classification

<!-- fig: 7.4 anomaly-radar -->

- **Caption:** Figure 7.4: Rolling z-score anomaly detection classified against the causal graph.
- **Use in:** 7.4 Anomaly Radar.
- **Description:** The latest point is compared with the trailing 12 observations (the latest point is excluded from its own baseline). Anomalies above |z| of 2.0 are classified by what their graph neighbours did: PROPAGATING if a linked indicator is also anomalous, ISOLATED if none is, UNLINKED if no neighbour has data. Isolated and unlinked ones are marked for source verification because they may be data errors.

```mermaid
flowchart TB
    A["all series with at least 8 points"] --> Z["z-score of latest vs trailing window of 12"]
    Z --> T{"abs(z) greater than 2.0?"}
    T -->|"no"| N["normal"]
    T -->|"yes"| NB["neighbours in knowledge graph<br/>upstream and downstream"]
    NB --> HD{"any neighbour with data?"}
    HD -->|"no"| UL["UNLINKED<br/>trust: LOW, verify source"]
    HD -->|"yes"| AN{"any neighbour anomalous?"}
    AN -->|"yes"| PR["PROPAGATING<br/>score = anomalous / with-data neighbours<br/>culprit path of relation ids"]
    AN -->|"no"| IS["ISOLATED<br/>trust: LOW, verify source"]
    PR --> EX["expected downstream propagation list"]
    IS --> EX
    UL --> EX
    INJ["optional SIM injection id:z"] -.-> Z
```

---

## Figure 7.5: Edge evidence audit

<!-- fig: 7.5 edge-audit -->

- **Caption:** Figure 7.5: Edge evidence audit: seeded priors tested against live series.
- **Use in:** 7.5 Edge Evidence Audit. A key novelty figure.
- **Description:** For each graph edge the audit aligns both series by month. With fewer than ten overlapping months the edge stays untestable. Otherwise a bivariate Granger test is run. The result labels each edge SEEDED (typed prior only) or EMPIRICAL (tested). Results are cached for five minutes.

```mermaid
flowchart TB
    E["each edge in ontology"] --> G1["get source series and target series"]
    G1 --> HAS{"both series available?"}
    HAS -->|"no"| U1["UNTESTABLE_NO_DATA<br/>class SEEDED"]
    HAS -->|"yes"| AL["align by YYYY-MM, overlap months n"]
    AL --> NQ{"n at least 10?"}
    NQ -->|"no"| U2["UNTESTABLE_N<br/>class SEEDED"]
    NQ -->|"yes"| GR["Granger test, max lag 2<br/>(ssr F-test, minimum p over lags)"]
    GR --> PV{"p-value computed?"}
    PV -->|"no"| U2
    PV -->|"yes"| EM["EMPIRICAL<br/>p, optimal lag, significant flag"]
    EM --> CACHE["cache 300 seconds"]
    U1 --> CACHE
    U2 --> CACHE
```

---

## Figure 7.6: Edge evidence states

<!-- fig: 7.6 edge-evidence-states -->

- **Caption:** Figure 7.6: Evidence states of a causal edge and the target path for the project.
- **Use in:** 7.5 Edge Evidence Audit / Chapter 10 future work.
- **Description:** Today an edge is either SEEDED or EMPIRICAL (single Granger test). The dashed future states describe the roadmap: stationarity-checked, multiple-testing-corrected and stability-tested estimates.

```mermaid
stateDiagram-v2
    [*] --> Seeded : typed into ontology
    Seeded --> UntestableData : series missing
    Seeded --> UntestableN : fewer than 10 overlap months
    Seeded --> Empirical : Granger test runs
    Empirical --> Seeded : data removed or cache expired
    Empirical --> Corrected : roadmap, BH-corrected p-values
    Corrected --> Stable : roadmap, sub-sample stability
    Stable --> [*]
```

---

## Figure 7.7: Simulated MPC meeting

<!-- fig: 7.7 mpc-simulation -->

- **Caption:** Figure 7.7: Simulation of a six-seat Monetary Policy Committee with a deterministic rule baseline.
- **Use in:** 7.6 MPC simulation. A key novelty figure.
- **Description:** An evidence pack (latest CPI, repo rate, GDP growth, USD/INR, credit growth) feeds three persona types (hawk, dove, centrist). Each persona has a rule-based vote and, when an LLM key exists, an LLM vote that must quote a number and cite an indicator from the pack. Six seats map to the three personas. The Governor casts the vote on a tie. The rule-only decision is always reported next to the final one, which makes an ablation possible. The meeting is always labelled SIMULATED.

```mermaid
flowchart TB
    EV["Evidence pack: CPI, repo, GDP growth, USD/INR, credit growth"] --> RULE["Rule vote per persona: hawk, dove, centrist"]
    EV --> LLMQ{"LLM key and use_llm?"}
    LLMQ -->|"yes"| LLMV["LLM vote per persona (JSON: vote, reason, cited indicator)<br/>accepted only if vote valid and cited id is in the pack"]
    LLMQ -->|"no"| SEATS
    RULE --> SEATS["6 seats: Governor centrist, RBI deputy hawk, RBI officer centrist,<br/>external 1 hawk, external 2 dove, external 3 dove"]
    LLMV --> SEATS
    SEATS --> TALLY["tally HIKE, HOLD, CUT"]
    TALLY --> TIE{"tie?"}
    TIE -->|"yes"| GOV["Governor casting vote"]
    TIE -->|"no"| MAJ["majority decision"]
    GOV --> OUT["decision, dissent, rule_baseline, agreement flag<br/>label SIMULATED"]
    MAJ --> OUT
```

---

## Figure 7.8: MPC rule logic per persona

<!-- fig: 7.8 mpc-rules -->

- **Caption:** Figure 7.8: Deterministic voting rules of the hawk, dove and centrist archetypes.
- **Use in:** 7.6 MPC simulation.
- **Description:** The thresholds 2%, 4% and 6% are the inflation-targeting band of the RBI framework (target 4% with a 2 to 6% tolerance band). `growth_weakening` is true when the latest GDP growth is below the prior value.

```mermaid
flowchart TB
    C{"CPI available?"} -->|"no"| H0["HOLD: no basis to move"]
    C -->|"yes"| PER{"persona"}
    PER -->|"hawk"| HW{"CPI above 6?"}
    HW -->|"yes"| HK1["HIKE"]
    HW -->|"no"| HH["HOLD"]
    PER -->|"dove"| DV{"CPI below 2?"}
    DV -->|"yes"| CT1["CUT"]
    DV -->|"no"| DG{"growth weakening and CPI at most 6?"}
    DG -->|"yes"| CT2["CUT"]
    DG -->|"no"| DH["HOLD"]
    PER -->|"centrist"| CE1{"CPI above 6?"}
    CE1 -->|"yes"| HK2["HIKE"]
    CE1 -->|"no"| CE2{"CPI below 2?"}
    CE2 -->|"yes"| CT3["CUT"]
    CE2 -->|"no"| CE3{"growth weakening and CPI below 4?"}
    CE3 -->|"yes"| CT4["CUT"]
    CE3 -->|"no"| CH["HOLD"]
```

---

## Figure 7.9: Consensus and model-card computation

<!-- fig: 7.9 consensus-model-card -->

- **Caption:** Figure 7.9: Derivation of the heuristic consensus quality and the model card from a finished orchestrator state.
- **Use in:** 7.7 Provenance cards.
- **Description:** Both are labelled heuristic in the payload. The consensus quality multiplies agent success, evidence cover and a knowledge-graph coverage factor. The trust score is the weighted sum 0.4 x evidence cover + 0.3 x mean edge confidence + 0.3 x agent success. The weights are design choices, not calibrated values; say so.

```mermaid
flowchart LR
    ST["Orchestrator state:<br/>trace, observations, sources, errors,<br/>causal_paths, scenario_result"] --> AS["agent_success<br/>success 1, partial 0.5, else 0"]
    ST --> EC["evidence_cover<br/>usable observations / all"]
    ST --> KC["kg_cover<br/>connected pairs / all pairs"]
    ST --> MC["mean edge confidence"]
    AS --> CQ["consensus_quality =<br/>agent_success x evidence_cover x (0.5 + 0.5 x kg_cover)"]
    EC --> CQ
    KC --> CQ
    AS --> TS["trust score =<br/>0.4 evidence_cover + 0.3 mean edge confidence + 0.3 agent_success"]
    EC --> TS
    MC --> TS
    CQ --> CO["consensus payload per agent"]
    TS --> CARD["model card:<br/>evidence counts, KG relations with evidence class,<br/>model formula and constants, regime note"]
```

---

## Figure 7.10: Daily early-warning brief pipeline

<!-- fig: 7.10 daily-brief -->

- **Caption:** Figure 7.10: Daily early-warning brief generation with deterministic fallback.
- **Use in:** 7.8 Daily brief.
- **Description:** A single scheduled or on-demand job reads dashboard telemetry (monetary, fiscal, external, markets), runs the anomaly scan, fetches capped and cached news, then makes at most one LLM call. If the LLM is unavailable or returns invalid JSON, a deterministic template is used. The brief is stored by Asia/Kolkata date.

```mermaid
flowchart TB
    TRG["Trigger: cron 08:15 IST (optional)<br/>or POST /brief/run"] --> EX{"Brief for today exists<br/>and not forced?"}
    EX -->|"yes"| RET["return stored brief"]
    EX -->|"no"| TEL["telemetry: monetary, fiscal, external, markets"]
    TEL --> SC["anomaly scan"]
    SC --> PIL["build four pillars and warnings"]
    PIL --> NEWS["cached news, at most 4 Tavily queries, 6 h TTL"]
    NEWS --> LLM{"LLM key and valid JSON?"}
    LLM -->|"yes"| SYN["LLM headline, summary, watch list"]
    LLM -->|"no"| DET["deterministic template"]
    SYN --> SAVE[("daily_briefs in macro_store.duckdb")]
    DET --> SAVE
    SAVE --> API["GET /brief/today, /history"]
```

---

## Figure 7.11: Claim verification pipeline

<!-- fig: 7.11 claim-verification-pipeline -->

- **Caption:** Figure 7.11: Claim verification pipeline: from retrieved evidence and proposed claims to rendered text and audit record.
- **Use in:** 7.9 Claim verification. The strongest novelty figure.
- **Description:** Observations and source passages are frozen into content-addressed evidence. Claims proposed by rules or a model must match a strict schema. Numeric claims are recomputed with Decimal arithmetic; qualitative claims are verified as exact source sentences or reviewed templates. Only controlled text is rendered; everything is written to an append-only audit. Be explicit that the pipeline is currently a tested library not yet connected to the answer path.

```mermaid
flowchart TB
    OBS["Retrieved observations"] --> EVD["build_evidence<br/>content-addressed ids"]
    SRC["Retrieved source passages"] --> EVD
    PROP["Claim proposals<br/>rules or model"] --> SCH{"strict schema valid?<br/>extra fields forbidden"}
    SCH -->|"no"| REJ0["rejected: invalid_claim_schema"]
    SCH -->|"yes"| TYP{"claim type"}
    TYP -->|"observation, rate_change,<br/>price_direction_yoy"| NUM["numeric verification<br/>Decimal, units, period, base, scope"]
    TYP -->|"reported_explanation"| QUO["exact complete-sentence match<br/>in retrieved passage"]
    TYP -->|"general_mechanism"| TPL["reviewed template"]
    TYP -->|"statistical_finding"| NOR["no registered analysis: insufficient_evidence"]
    EVD --> NUM
    EVD --> QUO
    NUM --> RES["VerificationResult"]
    QUO --> RES
    TPL --> RES
    NOR --> RES
    REJ0 --> RES
    RES --> REND["render_report<br/>only controlled text, withheld count"]
    RES --> AUD[("append-only SQLite audit")]
```

---

## Figure 7.12: Verification status outcomes

<!-- fig: 7.12 verification-statuses -->

- **Caption:** Figure 7.12: Possible outcomes of verifying a claim and what each guarantees.
- **Use in:** 7.9 Claim verification.
- **Description:** `verified` is a statement about consistency with the retrieved snapshot, not about the correctness of the provider. `source_attributed` shows an exact quotation without certifying causation.

```mermaid
flowchart LR
    C["Claim"] --> R{"Result"}
    R --> V["verified<br/>recomputed value matches at displayed precision"]
    R --> SA["source_attributed<br/>exact sentence in retrieved passage"]
    R --> GM["general_mechanism<br/>reviewed educational template"]
    R --> RJ["rejected<br/>wrong value, direction, scope, unit or altered quote"]
    R --> IE["insufficient_evidence<br/>unknown id, conflicting values, unknown base,<br/>no registered analysis"]
    V --> SHOW["rendered"]
    SA --> SHOW
    GM --> SHOW
    RJ --> HIDE["withheld, kept in audit"]
    IE --> HIDE
```

---

## Figure 7.13: Claim type model

<!-- fig: 7.13 claim-class-diagram -->

- **Caption:** Figure 7.13: Discriminated union of claim types accepted by the verifier.
- **Use in:** 7.9 Claim verification.
- **Description:** All claim classes forbid extra fields. A model cannot introduce a new claim type, formula or free text; this is the design decision that prevents prose from becoming fact.

```mermaid
classDiagram
    class ClaimBase {
        +str claim_id
        extra fields forbidden
    }
    class ObservationClaim {
        +str observation_id
        +float proposed_value
        +str output_unit
    }
    class RateChangeClaim {
        +str earlier_observation_id
        +str later_observation_id
        +float proposed_value
        +str operation
    }
    class PriceDirectionClaim {
        +str observation_id
        +str direction
        +str comparison
    }
    class ReportedExplanationClaim {
        +str passage_id
        +str supporting_quote
    }
    class GeneralMechanismClaim {
        +str mechanism_id
    }
    class StatisticalFindingClaim {
        +str analysis_id
    }
    class VerificationResult {
        +str claim_id
        +str status
        +str verification_method
        +list evidence_ids
        +list failed_checks
        +float computed_value
        +str rendered_text
    }
    ClaimBase <|-- ObservationClaim
    ClaimBase <|-- RateChangeClaim
    ClaimBase <|-- PriceDirectionClaim
    ClaimBase <|-- ReportedExplanationClaim
    ClaimBase <|-- GeneralMechanismClaim
    ClaimBase <|-- StatisticalFindingClaim
    ClaimBase ..> VerificationResult : verified into
```

---

## Figure 7.14: Content-addressed evidence identity

<!-- fig: 7.14 evidence-identity -->

- **Caption:** Figure 7.14: Identity rules for evidence records: revisions change the id, retrieval time does not.
- **Use in:** 7.9 Claim verification.
- **Description:** The id is a SHA-256 of the canonical JSON of the record without volatile fields. Two retrievals of the same published value share an id; a revised value or changed definition gets a new id, so an audit can show which version supported an answer.

```mermaid
flowchart TB
    REC["Observation record"] --> STRIP["remove observation_id, retrieved_at, request_id<br/>and volatile metadata: freshness, coverage, geography labels"]
    STRIP --> CAN["canonical JSON, sorted keys"]
    CAN --> HASH["SHA-256"]
    HASH --> ID["obs_ + hex digest"]
    REV["Revision or definition change"] --> NEWID["different id"]
    RE["Repeated retrieval, same value"] --> SAME["same id"]
```

---

## Figure 7.15: Proposed verification gate in the orchestrator (future work)

<!-- fig: 7.15 proposed-verification-gate -->

- **Caption:** Figure 7.15: Proposed integration of the claim verifier into orchestrator synthesis (not yet implemented).
- **Use in:** Chapter 10 Future work (and 7.9 as the design target).
- **Description:** In the current system the LLM narrative is rendered as written. In the proposed design the LLM returns structured claims and a template id; the verifier checks them against the A2A evidence; only verified statements are rendered, and causal claims are hedged by the evidence class of the edge they rely on. This is the main planned research contribution.

```mermaid
flowchart TB
    EV["A2A observations and sources"] --> EVD["content-addressed evidence"]
    KG["Causal paths with edge evidence class"] --> EVD
    EVD --> LLM["LLM proposes structured claims"]
    LLM --> VER["verify_claims"]
    VER --> CL{"claim kind"}
    CL -->|"numeric"| VN["recompute and compare"]
    CL -->|"causal"| VC["bind to KG edge,<br/>hedge by evidence class"]
    CL -->|"qualitative"| VQ["exact quote or template"]
    VN --> GATE["render verified text only"]
    VC --> GATE
    VQ --> GATE
    GATE --> REP["final report plus audit id"]
    VER --> WH["withheld claims reported with reason"]
    classDef future stroke-dasharray: 5 5
    class LLM,VER,GATE future
```
