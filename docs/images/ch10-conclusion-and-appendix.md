# Chapter 10 and Appendices: Conclusion, Future Work and Supporting Figures

---

## Figure 10.1: Objectives achieved

<!-- fig: 10.1 objectives-achieved -->

- **Caption:** Figure 10.1: Status of the project objectives defined in Chapter 1.
- **Use in:** 10.1 Summary of work.
- **Description:** Traces the five objectives from Figure 1.2 to their delivered status. Fully, Partially and Not yet are honest assessments from the code review.

```mermaid
flowchart LR
    O1["O1 Sector-wise data access"] --> S1["Delivered: 10 MCP servers and stores"]
    O2["O2 Coordinated multi-agent reasoning"] --> S2["Delivered: A2A layer and orchestrator"]
    O3["O3 Source-grounded answers"] --> S3["Partial: provenance enforced,<br/>verification library not yet wired"]
    O4["O4 Explicit causal model"] --> S4["Partial: graph delivered,<br/>edge statistics are priors,<br/>scenario engine heuristic"]
    O5["O5 Traceable provenance"] --> S5["Delivered: SourceProvenance, hashes, A2A trace"]
```

---

## Figure 10.2: Contributions of the work

<!-- fig: 10.2 contributions -->

- **Caption:** Figure 10.2: Summary of contributions.
- **Use in:** 10.1 Summary / 10.2 Contributions.
- **Description:** Engineering contributions are complete; research contributions are prototypes whose evaluation is future work.

```mermaid
mindmap
  root((Contributions))
    Engineering
      Ten India-specific sector agents over official sources
      Native typed A2A layer with guards and trace
      Per-sector FastMCP servers with fallbacks
      Cited report generation with offline fallback
      Interactive dashboard, chat and registry UI
    Research prototypes
      Edge evidence audit seeded versus empirical
      Graph-conditioned anomaly classification
      Simulated MPC with rule baseline
      Claim verification with content-addressed evidence
    Documentation
      Architecture, API and A2A guides
      Code review and publication plan
```

---

## Figure 10.3: Maturity of components

<!-- fig: 10.3 maturity -->

- **Caption:** Figure 10.3: Maturity assessment of the major components (author's assessment from the code review).
- **Use in:** 10.2 Limitations.
- **Description:** Position reflects implementation completeness (x) and evidence of correctness through tests or evaluation (y). Qualitative; explain in the text.

```mermaid
quadrantChart
    title Component maturity (author's assessment)
    x-axis "Prototype" --> "Complete"
    y-axis "Little evidence" --> "Well tested"
    quadrant-1 "Mature"
    quadrant-2 "Tested but incomplete"
    quadrant-3 "Early"
    quadrant-4 "Complete but unproven"
    "A2A layer": [0.85, 0.85]
    "Sector agents": [0.70, 0.70]
    "Orchestrator": [0.72, 0.65]
    "Knowledge graph": [0.60, 0.70]
    "Claim verification": [0.35, 0.80]
    "Scenario engine": [0.45, 0.35]
    "Research lab": [0.55, 0.30]
    "Frontend": [0.80, 0.25]
```

---

## Figure 10.4: Future-work roadmap

<!-- fig: 10.4 roadmap -->

- **Caption:** Figure 10.4: Proposed roadmap for future work (about twelve weeks).
- **Use in:** 10.3 Future work.
- **Description:** Mirrors `docs/publication-plan.md`. Adjust dates to your own plan.

```mermaid
gantt
    title Roadmap after submission of this report
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section Credibility
    Wire claim verification into synthesis      :r1, 2026-10-13, 14d
    Fix edge sign, silent failures, test paths  :r2, 2026-10-13, 14d
    section Causal modelling
    Estimated edges from long series            :r3, 2026-10-27, 28d
    Local projection or BVAR scenario engine    :r4, 2026-11-10, 28d
    section Evaluation
    Question set and gold answers               :r5, 2026-11-10, 21d
    Baselines and ablations                     :r6, 2026-12-01, 21d
    MPC benchmark with vintage data             :r7, 2026-12-01, 21d
    section Writing
    Paper draft and internal review             :r8, 2026-12-22, 21d
```

---

## Figure 10.5: Target architecture with the verification gate

<!-- fig: 10.5 target-architecture -->

- **Caption:** Figure 10.5: Target architecture after planned improvements (additions in the dashed group).
- **Use in:** 10.3 Future work.
- **Description:** Compared with Figure 3.2, three additions: a verification gate between synthesis and the report, an evidence-graded graph fed by long series, and a document evidence store for passage-level attribution.

```mermaid
flowchart TB
    UQ["User query"] --> OR["Orchestrator"]
    OR --> AG["Sector agents over A2A and MCP"]
    AG --> EV["Evidence store<br/>content-addressed observations"]
    KG["Causal graph"] --> OR
    subgraph NEW["Planned additions"]
        LS["Long-series estimation of edge grades"]
        DOC["Document evidence store<br/>RBI minutes, Economic Survey"]
        VG["Verification gate<br/>typed claims, hedged causal claims"]
        EVAL["Evaluation harness and benchmark"]
    end
    LS --> KG
    DOC --> EV
    EV --> VG
    OR --> VG
    VG --> REP["Verified report plus audit id"]
    REP --> EVAL
```

---

## Figure A.1: Repository structure

<!-- fig: A.1 repository-structure -->

- **Caption:** Figure A.1: Repository layout.
- **Use in:** Appendix A.
- **Description:** Top-level folders and their purpose.

```mermaid
flowchart LR
    ROOT["macrograph-ai/"]
    ROOT --> B["backend/"]
    ROOT --> F["frontend/"]
    ROOT --> D["docs/"]
    ROOT --> T["tasks/"]
    ROOT --> AG[".agents/"]
    ROOT --> BP["base_papers/"]
    ROOT --> CF["pyproject.toml, uv.lock, mcp.json"]
    B --> B1["main.py, demo_platform.py"]
    B --> B2["api/"]
    B --> B3["core/"]
    B --> B4["10 x sector packages"]
    B --> B5["tests/, scripts/, data/"]
    B3 --> C1["orchestrator, protocols, knowledge_graph,<br/>econometrics, research, briefing,<br/>verification, ingestion, database"]
    F --> F1["src/components, data, hooks, types"]
    D --> D1["architecture, API, A2A, status, publication plan, images"]
```

---

## Figure A.2: Worked end-to-end example (conceptual)

<!-- fig: A.2 example-query -->

- **Caption:** Figure A.2: Handling of the query "How does a rise in crude oil prices affect inflation and RBI policy?"
- **Use in:** Appendix A or Chapter 5 as a case walkthrough.
- **Description:** Replace the conceptual node text with the actual output (indicator matrix, causal paths and trace) from a real run before printing. The routing shown is what the keyword cards would select for oil, inflation and policy terms.

```mermaid
flowchart TB
    Q["Query: crude oil, inflation, RBI policy"] --> DEC["decompose: prices_sector and monetary_sector"]
    DEC --> P["prices_sector<br/>CPI and WPI via MoSPI MCP"]
    DEC --> M["monetary_sector<br/>repo rate via RBI DBIE"]
    P --> AGG["aggregate observations and sources"]
    M --> AGG
    AGG --> KG["KG paths: brent to WPI to CPI to repo"]
    KG --> SIM["optional scenario: Brent +20"]
    SIM --> SYN["synthesis: report with matrix, diagram, paths, scenario, sources"]
    SYN --> OUT["Response with citations and A2A trace"]
```

---

## Figure A.3: Error-code taxonomy

<!-- fig: A.3 error-taxonomy -->

- **Caption:** Figure A.3: Taxonomy of A2A error codes.
- **Use in:** Appendix B.
- **Description:** Grouped by cause. Retryable codes are shown in the last group.

```mermaid
mindmap
  root((A2A error codes))
    Addressing
      AGENT_NOT_FOUND
      AGENT_UNAVAILABLE
      UNSUPPORTED_CAPABILITY
    Policy
      DEPENDENCY_NOT_ALLOWED
    Loop protection
      MAX_DEPTH_EXCEEDED
      MAX_HOPS_EXCEEDED
      CIRCULAR_DELEGATION
      DUPLICATE_REQUEST
    Content
      INVALID_REQUEST
      INVALID_RESPONSE
    Execution
      DATA_SOURCE_ERROR
      LLM_ERROR
      AGENT_ERROR
    Retryable
      AGENT_TIMEOUT
      TRANSPORT_ERROR
```
