# Chapter 9: Testing, Results and Evaluation - Figures

Measured values below were collected on 2026-10-12 from the repository (test function counts by `grep`, line counts by `wc`, full test run). Update them if the code changes before submission. The evaluation-design figures (9.6 to 9.9) describe planned work; do not present them as results.

---

## Figure 9.1: Test suite composition by area

<!-- fig: 9.1 test-composition -->

- **Caption:** Figure 9.1: Number of test functions per test area (455 functions counted; 551 test cases executed after parametrisation).
- **Use in:** 9.1 Testing strategy.
- **Description:** The core and cross-cutting suite in `backend/tests` is the largest block (A2A protocol and hardening, orchestrator integration, knowledge graph, causal engine, claim verification, dashboard, prices and real sector). Sector suites follow.

```mermaid
pie showData
    title Test functions by area
    "backend/tests (core, A2A, KG, API)" : 198
    "agriculture" : 48
    "external" : 45
    "monetary" : 43
    "services" : 33
    "finance" : 32
    "capital markets" : 27
    "fiscal" : 15
    "labour" : 7
    "real" : 7
```

---

## Figure 9.2: Result of the full test run

<!-- fig: 9.2 test-results -->

- **Caption:** Figure 9.2: Outcome of the complete backend test run on 12 October 2026.
- **Use in:** 9.2 Test results.
- **Description:** 550 passed and 1 failed in 715 seconds. The failure is a monetary-sector test whose stub no longer reaches the fallback path (expected repo rate 5.0, got 5.25). Fix it or report it as a known issue; do not hide it.

```mermaid
pie showData
    title Full run: 551 test cases
    "Passed" : 550
    "Failed" : 1
```

---

## Figure 9.3: Test pyramid of the project

<!-- fig: 9.3 test-pyramid -->

- **Caption:** Figure 9.3: Layers of testing applied to the platform.
- **Use in:** 9.1 Testing strategy.
- **Description:** Unit tests dominate. Protocol and orchestrator integration tests use stub handlers and a mocked LLM. The Chapter 9 limitation applies: there are no browser end-to-end tests and no frontend unit tests; `npm run build` is the only frontend check.

```mermaid
flowchart TB
    L4["Layer 4: Manual system demo<br/>demo_platform.py, validate_sector_agents.py"]
    L3["Layer 3: Integration tests<br/>A2A integration and streaming, orchestrator and KG, dashboard API"]
    L2["Layer 2: Component tests<br/>A2A protocol and hardening, KG schema, networkx, Neo4j mock, causal engine"]
    L1["Layer 1: Unit tests<br/>parsers, validators, claim verification, sector clients and databases"]
    L4 --> L3 --> L2 --> L1
```

---

## Figure 9.4: Source code size by component

<!-- fig: 9.4 code-size -->

- **Caption:** Figure 9.4: Non-test source lines by component.
- **Use in:** 9.3 Implementation statistics.
- **Description:** Lines of Python (backend) and TypeScript (frontend), tests excluded. The core package and the frontend are the largest items; each sector is between about 1.9k and 3.3k lines.

```mermaid
xychart-beta
    title "Source lines by component (tests excluded)"
    x-axis ["frontend", "core", "api", "services", "real", "external", "finance", "capital", "fiscal", "monetary", "labour", "agri", "prices"]
    y-axis "Lines of code" 0 --> 12000
    bar [11287, 6778, 2877, 3274, 3200, 3053, 3081, 2918, 2653, 2560, 2545, 2101, 1872]
```

---

## Figure 9.5: Quality gates and verification workflow

<!-- fig: 9.5 quality-gates -->

- **Caption:** Figure 9.5: Verification workflow followed before a change is accepted.
- **Use in:** 9.1 Testing strategy.
- **Description:** The gates mirror the project's agent contract (`.agents/AGENTS.md`). Add continuous integration (not present today) to run the full-suite gate automatically.

```mermaid
flowchart TB
    C["Code change"] --> T["pytest: unit and integration"]
    T --> R["Rule scan:<br/>400-line limit, parameterised SQL,<br/>future annotations, no bare except"]
    R --> FB["npm run build<br/>tsc and vite build"]
    FB --> DM["Demo run:<br/>demo_platform.py"]
    DM --> D["Update docs and tasks/todo.md"]
    D --> OK["Accept"]
    T -->|"fail"| FIX["Fix root cause"]
    R -->|"fail"| FIX
    FB -->|"fail"| FIX
    FIX --> C
```

---

## Figure 9.6: Proposed evaluation harness (planned)

<!-- fig: 9.6 evaluation-harness -->

- **Caption:** Figure 9.6: Proposed evaluation harness for measuring unsupported-claim rate and abstention correctness.
- **Use in:** 9.5 Evaluation methodology (planned) or Chapter 10 future work.
- **Description:** Questions have gold answers computed directly from official series, never from model output. Each system answers the same questions; a grader extracts claims and scores them. Results are reported with bootstrap intervals over repeated runs.

```mermaid
flowchart TB
    QS["Question set, about 250<br/>lookup, change, cross-sector, causal, unanswerable"] --> RUN["Runner"]
    GOLD["Gold answers computed from frozen official data"] --> GR
    subgraph SYS["Systems under test"]
        S1["1 Single LLM"]
        S2["2 LLM with web search"]
        S3["3 RAG"]
        S4["4 Multi-agent without verification"]
        S5["5 Multi-agent with verification"]
    end
    RUN --> SYS --> ANS["Answers and cited claims"]
    ANS --> GR["Grader: claim extraction and matching"]
    GR --> MET["Metrics:<br/>unsupported numeric claim rate,<br/>citation validity, abstention correctness,<br/>coverage, latency, cost"]
    MET --> STAT["Mean and 95 percent bootstrap interval,<br/>at least 3 runs and 2 LLM backends"]
```

---

## Figure 9.7: Ablation design (planned)

<!-- fig: 9.7 ablation-design -->

- **Caption:** Figure 9.7: Planned ablations isolating the contribution of each mechanism.
- **Use in:** 9.5 Evaluation methodology (planned).
- **Description:** Each ablation removes exactly one mechanism from the full system and measures the change in unsupported-claim rate and coverage.

```mermaid
flowchart LR
    FULL["Full system"] --> A1["Remove ownership constraint<br/>agents may fetch any indicator"]
    FULL --> A2["Remove claim verification<br/>render LLM prose"]
    FULL --> A3["Remove edge evidence grading<br/>treat all edges as equal"]
    FULL --> A4["Remove knowledge graph<br/>no causal enrichment"]
    FULL --> A5["Single agent with all tools"]
    A1 --> M["Compare: unsupported claims,<br/>contradictions, coverage, latency"]
    A2 --> M
    A3 --> M
    A4 --> M
    A5 --> M
```

---

## Figure 9.8: Planned MPC benchmark

<!-- fig: 9.8 mpc-benchmark -->

- **Caption:** Figure 9.8: Planned benchmark of the simulated MPC against actual RBI decisions with point-in-time data.
- **Use in:** Chapter 10 future work or 9.5.
- **Description:** The current evidence pack uses the latest values, so it cannot be tested historically without look-ahead leakage. The benchmark needs vintage data available before each meeting date.

```mermaid
flowchart TB
    MT["RBI meeting dates since 2016"] --> VD["Point-in-time data before each meeting"]
    VD --> ARMS
    subgraph ARMS["Arms"]
        R1["Always HOLD"]
        R2["Taylor rule"]
        R3["Rule baseline of the simulator"]
        R4["Single LLM"]
        R5["Three-persona LLM"]
    end
    ARMS --> PRED["Predicted decisions and dissent"]
    ACT["Actual decisions and vote splits from published minutes"] --> CMP["Compare: accuracy, turning points, dissent correlation"]
    PRED --> CMP
```

---

## Figure 9.9: Edge-audit evaluation plan

<!-- fig: 9.9 edge-audit-plan -->

- **Caption:** Figure 9.9: Planned procedure for estimating causal-edge statistics from data.
- **Use in:** Chapter 10 future work.
- **Description:** Replaces hand-typed p-values and confidences with estimates that carry sample size and stability. Reports what share of seeded edges survives testing.

```mermaid
flowchart TB
    S["Long monthly series from owner sectors"] --> ST["Stationarity: ADF or KPSS, difference as needed"]
    ST --> GR["Pairwise Granger tests, lags 1 to 6"]
    GR --> BH["Benjamini-Hochberg correction"]
    BH --> LP["Sign and magnitude by local projection"]
    LP --> STAB["Sub-sample stability test"]
    STAB --> GRADE["Edge evidence grade and stored estimate with n, window, vintage"]
    GRADE --> REP["Report: share of seeded edges supported"]
```

---

## Figure 9.10: Limitations and risk map

<!-- fig: 9.10 limitations -->

- **Caption:** Figure 9.10: Known limitations of the current implementation and their mitigation.
- **Use in:** 9.6 Limitations / 10.2 Limitations.
- **Description:** State these openly. They come from the code review in `docs/status-and-roadmap.md`.

```mermaid
flowchart LR
    subgraph L["Limitation"]
        L1["Edge p-values and confidences are curated priors"]
        L2["Scenario engine is heuristic and unit-blind"]
        L3["Claim verification not wired into answers"]
        L4["Short time series for audits"]
        L5["No document RAG"]
        L6["Unauthenticated cost-bearing endpoints"]
        L7["No formal evaluation yet"]
    end
    subgraph M["Mitigation or next step"]
        M1["Estimate edges from long series"]
        M2["Local projections or BVAR with back-tests"]
        M3["Add verification gate to synthesis"]
        M4["Ingest long histories from DBIE and MoSPI"]
        M5["Index RBI minutes and Economic Survey with passage attribution"]
        M6["Add API keys and rate limiting"]
        M7["Build benchmark and ablations"]
    end
    L1 --> M1
    L2 --> M2
    L3 --> M3
    L4 --> M4
    L5 --> M5
    L6 --> M6
    L7 --> M7
```
