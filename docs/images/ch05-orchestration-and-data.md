# Chapter 5: Implementation of Orchestration, Sector Agents and Data Layer - Figures

---

## Figure 5.1: LangGraph orchestrator state graph

<!-- fig: 5.1 orchestrator-graph -->

- **Caption:** Figure 5.1: The four-node LangGraph orchestrator and the state keys written by each node.
- **Use in:** 5.1 Orchestrator implementation.
- **Description:** A linear graph. Each node reads and writes keys of `OrchestratorState`. The A2A node returns partial data on agent failure and the run continues.

```mermaid
flowchart TB
    START(["START"]) --> N1["decompose<br/>writes routed_agents, routing_method,<br/>target_sectors, decomposed_tasks"]
    N1 --> N2["parallel_a2a_execute<br/>writes collected_observations, agent_analyses,<br/>citations, a2a_sources, a2a_errors, a2a_trace"]
    N2 --> N3["kg_causal_enrichment<br/>writes causal_paths, scenario_result,<br/>mermaid_diagram, live_baseline_ids"]
    N3 --> N4["synthesis<br/>writes final_report, confidence_score, status"]
    N4 --> END(["END"])
```

---

## Figure 5.2: End-to-end sequence for a cross-sector query

<!-- fig: 5.2 end-to-end-sequence -->

- **Caption:** Figure 5.2: End-to-end sequence of a cross-sector chat request through the platform.
- **Use in:** 5.1 Orchestrator implementation, or Appendix A as a worked example.
- **Description:** The browser opens a Server-Sent Events stream. The orchestrator graph runs; progress is streamed as `step` events read live from the trace store; the report is streamed as `token` events and the final `done` event carries citations, A2A summary, consensus and model card.

```mermaid
sequenceDiagram
    actor U as Analyst
    participant UI as Chat workspace
    participant API as Chat router
    participant G as Orchestrator
    participant A as A2A and agents
    participant K as KG and engine
    participant L as LLM client
    U->>UI: ask question
    UI->>API: POST /chat/stream
    API->>G: invoke graph
    G->>G: decompose over Agent Cards
    G->>A: delegate in parallel
    A-->>API: trace updates
    API-->>UI: SSE step events
    A-->>G: observations and sources
    G->>K: paths and scenario
    K-->>G: paths, table, Mermaid
    G->>L: grounded prompt
    L-->>G: narrative or notice
    G->>G: offline fallback if needed
    G-->>API: final state
    API-->>UI: SSE token events
    API-->>UI: SSE done event
    UI-->>U: report, tables, trace
```

---

## Figure 5.3: Chat routing decision (direct versus orchestrated)

<!-- fig: 5.3 chat-routing -->

- **Caption:** Figure 5.3: Decision logic that sends a message to a single sector agent or to the full orchestrator.
- **Use in:** 5.2 Chat and routing implementation.
- **Description:** The UI sends the selected agent id. Direct sector chats bypass the orchestrator and call the sector's agent node. When the orchestrator is selected and the query is clearly a single-sector prices query, it is rerouted to the prices agent. Everything else uses the graph.

```mermaid
flowchart TB
    M["Message and selected agent"] --> S{"Selected agent"}
    S -->|"orchestrator"| P{"is_direct_prices_query?"}
    P -->|"yes"| PR["prices_agent_node"]
    P -->|"no"| G["Full orchestrator graph"]
    S -->|"finance_sector"| F["finance_agent_node"]
    S -->|"fiscal_sector"| FI["fiscal_agent_node"]
    S -->|"prices_sector"| PR
    S -->|"other sector id"| O["sector agent node via chat_config"]
    F --> OUT["Stream steps, tokens and done event"]
    FI --> OUT
    PR --> OUT
    O --> OUT
    G --> OUT
```

---

## Figure 5.4: Delegation, follow-up round and aggregation

<!-- fig: 5.4 delegate-aggregate -->

- **Caption:** Figure 5.4: Parallel delegation, bounded follow-up round and aggregation of A2A responses.
- **Use in:** 5.1 Orchestrator implementation.
- **Description:** Requests go out concurrently. A response may include up to three follow-ups, which are sent once as a bounded second round. Aggregation validates each response, extracts observations from JSON or markdown artifacts, and converts failures into `a2a_errors`; the run status becomes `a2a_partial` rather than failing.

```mermaid
flowchart TB
    A["routed agent ids"] --> B["send_many: one sector_analysis per agent, concurrent"]
    B --> D{"follow_ups present?"}
    D -->|"yes, max 3 each"| E["one bounded follow-up round<br/>linked by parent_request_id"]
    D -->|"no"| G
    E --> G["aggregate(): validate each response"]
    G --> I{"artifact type"}
    I -->|"JSON"| J["extract observations and citations"]
    I -->|"markdown"| K["report text plus artifact-level provenance"]
    G --> M["failed responses appended to a2a_errors"]
    J --> N["state update"]
    K --> N
    M --> N
    N --> O{"any error?"}
    O -->|"yes"| P["status a2a_partial"]
    O -->|"no"| Q["status ok"]
```

---

## Figure 5.5: Structure of the generated report

<!-- fig: 5.5 report-structure -->

- **Caption:** Figure 5.5: Sections of the cited intelligence report produced by the synthesis node.
- **Use in:** 5.3 Synthesis.
- **Description:** The narrative is only section 1. Sections 2 to 6 are assembled deterministically from structured state, so the evidence and provenance never depend on LLM prose.

```mermaid
flowchart LR
    R["Indian Macroeconomic Intelligence Report"]
    R --> S1["1 Executive synthesis<br/>LLM narrative or deterministic summary"]
    R --> S2["2 Indicator matrix and provenance<br/>value, unit, period, status, hash"]
    R --> S3["3 Causal transmission channels<br/>Mermaid diagram and path table"]
    R --> S4["4 Scenario simulation table<br/>baseline, shocked peak, delta, lag, band"]
    R --> S5["5 A2A source provenance<br/>agent, source, dataset or table, period, retrieved"]
    R --> S6["6 Methodological notes<br/>5-tier taxonomy, documentary evidence unavailable"]
    R --> S7["Unavailable agent data<br/>when any agent failed"]
```

---

## Figure 5.6: LLM availability and deterministic fallback ladder

<!-- fig: 5.6 offline-fallback -->

- **Caption:** Figure 5.6: Graceful degradation when the LLM is not available.
- **Use in:** 5.4 Robustness.
- **Description:** Every LLM-using stage has a deterministic path built from the same structured evidence, so the platform works without credentials (useful for demonstrations and tests). The notice string is compared by the callers to decide when to fall back.

```mermaid
flowchart TB
    S["Stage needs LLM text<br/>routing, synthesis, sector reasoning, brief, MPC"] --> K{"API key resolved?"}
    K -->|"no"| U["return unavailable notice"]
    K -->|"yes"| CALL["call model with retry"]
    CALL --> OKQ{"success?"}
    OKQ -->|"yes"| TXT["use model text"]
    OKQ -->|"no"| U
    U --> DET["deterministic output"]
    DET --> D1["routing: card scoring only"]
    DET --> D2["synthesis: counts, paths, scenario list"]
    DET --> D3["brief: pillar takeaways template"]
    DET --> D4["MPC: rule-based votes"]
```

---

## Figure 5.7: Live baseline override for scenarios

<!-- fig: 5.7 live-baselines -->

- **Caption:** Figure 5.7: Selection of simulation baselines: live observations override fixed defaults.
- **Use in:** 5.5 Scenario integration.
- **Description:** For each indicator in the knowledge graph the first usable sector observation replaces the default baseline. The report states which indicators used live baselines and which used defaults, so a report cannot silently contradict the retrieved data.

```mermaid
flowchart TB
    OBS["collected_observations"] --> F{"Indicator in KG,<br/>numeric, data_status usable?"}
    F -->|"yes"| LIVE["live baseline"]
    F -->|"no"| DEF["DEFAULT_BASELINES"]
    LIVE --> M["merge: live overrides default"]
    DEF --> M
    M --> SIM["simulate_scenario(baseline_values)"]
    LIVE --> IDS["live_baseline_ids"]
    IDS --> NOTE["baseline note in report and prompt"]
    SIM --> RES["scenario_result"]
```

---

## Figure 5.8: Generic sector data pipeline

<!-- fig: 5.8 sector-data-pipeline -->

- **Caption:** Figure 5.8: Data acquisition pipeline shared by the sector agents.
- **Use in:** 5.6 Data acquisition.
- **Description:** Source payloads are fetched with retries, parsed into Pydantic models, validated, stored with parameterised SQL and returned with a citation and a freshness flag. The `fetch_log` table records every attempt.

```mermaid
flowchart TB
    SRC["Official source<br/>MCP, REST, Excel, HTML"] --> FETCH["client.py<br/>httpx async plus Tenacity retry"]
    FETCH --> PARSE["parsers.py<br/>normalise fields and units"]
    PARSE --> VAL["Pydantic v2 models<br/>period and numeric validation"]
    VAL --> STORE[("Sector DuckDB<br/>parameterised SQL")]
    FETCH --> LOG[("fetch_log")]
    STORE --> TOOL["FastMCP tool"]
    TOOL --> CIT["Citation: source, table, period,<br/>freshness, retrieved_at"]
    CIT --> AGENT["Agent node and A2A executor"]
```

---

## Figure 5.9: Canonical ingestion pipeline

<!-- fig: 5.9 ingestion-pipeline -->

- **Caption:** Figure 5.9: Canonical ingestion pipeline of the shared core data layer.
- **Use in:** 5.6 Data acquisition.
- **Description:** Source adapters are registered by canonical indicator id. The scheduler runs adapters on demand. The validator checks numeric ranges and period formats, the normaliser maps to a `CanonicalObservation`, and the provenance step attaches the SHA-256 hash before storage in `macro_store.duckdb`.

```mermaid
flowchart TB
    REG["SourceRegistry<br/>adapter per indicator id"] --> SCH["IngestionScheduler<br/>run_ingestion_pipeline"]
    SCH --> AD["Source adapter<br/>e.g. MoSPI client"]
    AD --> VA["ObservationValidator<br/>numeric range, period format"]
    VA --> NO["Normalizer<br/>to CanonicalObservation"]
    NO --> PV["Provenance hash<br/>SHA-256 of payload"]
    PV --> MS[("macro_store.duckdb<br/>canonical_observations")]
    VA -->|"invalid"| ERR["ValidationError, not stored"]
    MS --> RD["get_canonical_series(indicator_id)"]
```

---

## Figure 5.10: Data sources by sector

<!-- fig: 5.10 data-sources-by-sector -->

- **Caption:** Figure 5.10: Primary data sources feeding each sector agent.
- **Use in:** 5.6 Data acquisition.
- **Description:** One cluster per sector. Verify the source names against the per-sector README before printing: some sectors use more than one fallback source.

```mermaid
flowchart TB
    S1["real_sector: MoSPI e-Sankhyiki MCP (NAS, IIP)"]
    S2["agriculture_sector: MoSPI MCP, data.gov.in, weather MCP, Agmarknet"]
    S3["prices_sector: MoSPI MCP (CPI, WPI), Yahoo Finance proxies, Tavily and web search"]
    S4["monetary_sector: RBI DBIE, eco-policy-mcp, Tavily news"]
    S5["finance_sector: RBI DBIE tables r539, r330, r531, r689, Financial Stability Report"]
    S6["capital_market_sector: yfinance (NIFTY, VIX, USD/INR), SEBI and flow data"]
    S7["fiscal_sector: Union Budget and CGA seeds, IMF WEO debt series, GST collections"]
    S8["external_sector: RBI, IMF, market and Tavily clients"]
    S9["labour_sector: MoSPI PLFS, EPFO"]
    S10["services_sector: MoSPI, PMI releases"]
    S1 ~~~ S2 ~~~ S3 ~~~ S4 ~~~ S5 ~~~ S6 ~~~ S7 ~~~ S8 ~~~ S9 ~~~ S10
```

---

## Figure 5.11: Sector DuckDB tables

<!-- fig: 5.11 sector-tables -->

- **Caption:** Figure 5.11: Tables created by each sector's DuckDB schema.
- **Use in:** 5.7 Database design (tables chapter).
- **Description:** Table names are taken from the `CREATE TABLE` statements in each `database.py`. Every sector also has a `fetch_log` table. Prices and agriculture do not keep a persistent sector database in the current code.

```mermaid
flowchart TB
    M0["macro_store.duckdb: canonical_indicators, canonical_observations,<br/>macro_series, daily_briefs, brief_news_cache"]
    MON["monetary: policy_rates, money_supply, system_liquidity, monetary_stance"]
    FIN["finance: bank_credit_growth, asset_quality, lending_rates, deposits_cd_ratio"]
    FIS["fiscal: union_fiscal_deficit, general_govt_debt, gst_collections, mospi_tax_aggregates"]
    EXT["external: forex_reserves, trade_balance, bop, exchange_rates,<br/>external_flows, remittances_invisibles, external_debt"]
    LAB["labour: unemployment, lfpr, wpr, labour_conditions"]
    REA["real: iip_sectoral, iip_use_based, core_industries,<br/>manufacturing_gva, market_context"]
    SER["services: isp_growth, services_gva, services_pmi, transport_freight"]
    CAP["capital markets: nifty_snapshot, market_history, india_vix, market_breadth,<br/>gsec_yields, mutual_fund_flows, fpi_flows, corporate_earnings,<br/>sectoral_performance, primary_market_ipos,<br/>investor_participation, market_economy_linkages"]
    M0 ~~~ MON ~~~ FIN ~~~ FIS ~~~ EXT ~~~ LAB ~~~ REA ~~~ SER ~~~ CAP
```

---

## Figure 5.12: Direct sector agent reasoning pipeline

<!-- fig: 5.12 direct-agent-pipeline -->

- **Caption:** Figure 5.12: Evidence-grounded reasoning pipeline of a direct sector agent (Prices and Finance pattern).
- **Use in:** 5.8 Sector agent reasoning.
- **Description:** Official observations come first through the sector's own MCP tools. Market proxies and news are fetched concurrently as context, not as authoritative data. The LLM receives the consolidated dataset and must cite periods and sources; the response keeps the citations separate from prose.

```mermaid
flowchart TB
    Q["User query"] --> D{"Query in sector domain?"}
    D -->|"no"| DECL["Politely decline and suggest correct agent"]
    D -->|"yes"| SEL["Select services and MCP tools"]
    SEL --> PAR{"concurrent"}
    PAR --> OFF["Official observations via own MCP tools"]
    PAR --> MKT["Market proxies, e.g. crude, gold, USD/INR, NIFTY"]
    PAR --> NEWS["Tavily news and web research"]
    PAR --> PEER["Peer indicators via A2A (finance, fiscal)"]
    OFF --> CONS["Consolidated dataset"]
    MKT --> CONS
    NEWS --> CONS
    PEER --> CONS
    CONS --> RSN["reason_over_sector_data<br/>core/sector_reasoning.py"]
    RSN --> RES["Report plus data_context plus citations plus freshness"]
```

---

## Figure 5.13: Resilience pattern for external calls

<!-- fig: 5.13 resilience -->

- **Caption:** Figure 5.13: Retry, timeout and degradation pattern applied to external calls.
- **Use in:** 5.9 Reliability engineering.
- **Description:** Exponential backoff via Tenacity on external calls, per-request timeouts in the A2A layer, partial results instead of failures at the orchestrator, and an explicit unavailable list in the report. Nothing is silently dropped.

```mermaid
flowchart TB
    CALL["External call"] --> TRY{"Success?"}
    TRY -->|"yes"| OK["Return data"]
    TRY -->|"no"| RT{"Attempts left?"}
    RT -->|"yes"| WAIT["Exponential backoff"] --> CALL
    RT -->|"no"| CACHE{"Cached snapshot?"}
    CACHE -->|"yes"| CV["Return cached, freshness cached"]
    CACHE -->|"no"| UN["Structured unavailable result"]
    UN --> AGG["A2A error recorded"]
    AGG --> REP["Report lists unavailable agent data"]
```
