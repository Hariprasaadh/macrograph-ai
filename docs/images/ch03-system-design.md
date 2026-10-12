# Chapter 3: System Design and Architecture - Figures

Chapter 3 (proposed system / design) carries the largest number of figures. The first four are the ones examiners expect on every project: context, layered architecture, deployment and data model.

---

## Figure 3.1: System context diagram

<!-- fig: 3.1 system-context -->

- **Caption:** Figure 3.1: System context of Macrograph-AI showing users, external data sources and external services.
- **Use in:** 3.1 Overall system overview.
- **Description:** The platform is one system boundary. Analysts reach it through a browser; it consumes official data sources through MCP servers and web APIs, calls an LLM provider for narrative reasoning, optionally mirrors the knowledge graph to Neo4j, and uses Google Identity Services for sign-in.

```mermaid
flowchart LR
    U1["Macro analyst"]
    U2["Researcher or student"]
    U3["Developer or API client"]
    subgraph SYS["Macrograph-AI platform"]
        direction TB
        WEB["Web application"]
        API["FastAPI gateway"]
        CORE["Agents, orchestrator, knowledge graph"]
        STORE[("DuckDB and SQLite")]
        WEB --> API --> CORE --> STORE
    end
    subgraph EXT["External services"]
        D1["MoSPI e-Sankhyiki MCP"]
        D2["RBI DBIE"]
        D3["Yahoo Finance"]
        D4["IMF WEO, CGA, GST data"]
        D5["Tavily and web search"]
        L1["Groq LLM API"]
        G1["Google Identity Services"]
        N1[("Neo4j, optional")]
    end
    U1 --> WEB
    U2 --> WEB
    U3 --> API
    CORE --> D1
    CORE --> D2
    CORE --> D3
    CORE --> D4
    CORE --> D5
    CORE --> L1
    CORE -.-> N1
    WEB --> G1
```

---

## Figure 3.2: Layered architecture

<!-- fig: 3.2 layered-architecture -->

- **Caption:** Figure 3.2: Layered architecture of Macrograph-AI.
- **Use in:** 3.2 System architecture. This is the main architecture figure; put it on its own page.
- **Description:** Seven layers from presentation to storage. Arrows only point downward, which is the dependency rule: upper layers call lower layers and never the reverse. The sector agents sit side by side inside the agent layer and are connected only through the protocol layer.

```mermaid
flowchart TB
    L1["1 PRESENTATION: React 18, TypeScript, Vite, Tailwind<br/>landing and sign-in, dashboard, chat, Causal Lab, A2A registry"]
    L2["2 GATEWAY: FastAPI<br/>chat, dashboard, research, brief, analyze, A2A API, sector sub-apps"]
    L3["3 ORCHESTRATION: LangGraph<br/>decompose, parallel A2A execute, KG enrichment, synthesis"]
    L4["4 AGENTS: 10 sector agents<br/>real, agriculture, prices, monetary, finance,<br/>capital markets, fiscal, external, labour, services"]
    L5["5 PROTOCOLS<br/>A2A: server, client, router, guards, trace<br/>MCP: FastMCP servers and client"]
    L6["6 KNOWLEDGE AND ANALYSIS<br/>ontology and NetworkX, scenario engine,<br/>research lab, claim verification library"]
    L7["7 DATA<br/>macro_store.duckdb, sector DuckDB stores,<br/>claim_audits.sqlite3, official sources, LLM API"]
    L1 --> L2 --> L3 --> L4 --> L5 --> L7
    L3 --> L6 --> L7
```

---

## Figure 3.3: Runtime deployment view

<!-- fig: 3.3 deployment-view -->

- **Caption:** Figure 3.3: Runtime deployment view of the development configuration.
- **Use in:** 3.7 Deployment / Implementation environment.
- **Description:** All sector agents run inside a single FastAPI process and talk through an in-process A2A transport; replacing the transport with HTTP is possible without changing callers. The Vite dev server proxies API calls to the gateway on port 8000. DuckDB files are local; Neo4j is optional.

```mermaid
flowchart LR
    BR["Browser"] --> VP["Vite dev server :5173<br/>static app and proxy"]
    VP --> APP
    subgraph GWP["Uvicorn process :8000"]
        direction TB
        APP["FastAPI app"]
        SUB["10 sector sub-apps"]
        A2A["In-process A2A transport"]
        LG["LangGraph orchestrator"]
        KG["NetworkX graph in memory"]
        APP --> SUB
        APP --> LG --> A2A --> SUB
        LG --> KG
    end
    GWP --> FS[("Local files<br/>macro_store.duckdb, sector DuckDB,<br/>claim_audits.sqlite3")]
    GWP --> GQ["Groq API"]
    GWP --> SRC["Official data sources"]
    KG -.->|"startup sync if NEO4J_URI set"| N4[("Neo4j, optional")]
```

---

## Figure 3.4: Package dependency rules

<!-- fig: 3.4 package-dependencies -->

- **Caption:** Figure 3.4: Allowed import directions between packages.
- **Use in:** 3.3 Design constraints / modularity.
- **Description:** Sector packages may import `core` but never each other. The only module in `core` that names sector packages is `registry_bootstrap.py`, which registers each sector's agent card and executor. Cross-sector data moves via A2A messages at run time instead of imports.

```mermaid
flowchart TB
    MAIN["main.py gateway"] --> API["api routers"]
    MAIN --> SECT
    API --> CORE
    subgraph CORE["backend/core"]
        ORCH["orchestrator"]
        BOOT["registry_bootstrap.py<br/>the only module naming sectors"]
        A2A["protocols/a2a"]
        OTH["knowledge_graph, econometrics, research,<br/>briefing, verification, database, ingestion"]
    end
    subgraph SECT["backend/*_sector (10 packages)"]
        S1["each sector"]
    end
    ORCH --> A2A
    ORCH --> OTH
    BOOT -->|"imports executors"| S1
    S1 -->|"may import"| A2A
    S1 -->|"may import"| OTH
    S1 -. "never imports another sector: A2A messages only" .-> S1
```

---

## Figure 3.5: Use case diagram

<!-- fig: 3.5 use-cases -->

- **Caption:** Figure 3.5: Use cases for the principal actors.
- **Use in:** 3.4 Functional requirements.
- **Description:** Three actors and the use cases each can trigger. Convert to formal UML ovals in draw.io if your guide requires UML notation.

```mermaid
flowchart LR
    A1(["Analyst"])
    A2(["Researcher"])
    A3(["API client"])
    subgraph UC["Macrograph-AI use cases"]
        U1["Sign in with Google"]
        U2["View cross-sector dashboard"]
        U3["Ask a single-sector question"]
        U4["Ask a cross-sector question"]
        U5["Inspect citations and evidence"]
        U6["View A2A trace and registry"]
        U7["Run scenario shock"]
        U8["Explore causal graph"]
        U9["Run anomaly radar"]
        U10["Simulate MPC meeting"]
        U11["Read daily brief"]
        U12["Call analyze or simulate API"]
    end
    A1 --- U1
    A1 --- U2
    A1 --- U3
    A1 --- U4
    A1 --- U5
    A1 --- U11
    A2 --- U4
    A2 --- U6
    A2 --- U7
    A2 --- U8
    A2 --- U9
    A2 --- U10
    A3 --- U12
```

---

## Figure 3.6: Internal structure of a sector agent package

<!-- fig: 3.6 sector-package-structure -->

- **Caption:** Figure 3.6: Standard internal structure of a sector agent package.
- **Use in:** 3.5 Sector agent design.
- **Description:** Every sector follows the same shape (some are partial, see the maturity table in `docs/status-and-roadmap.md`). The MCP server is the only door to data; the agent node reasons over the data; the executor exposes the agent to A2A; the sub-app exposes HTTP.

```mermaid
flowchart TB
    subgraph PK["<sector>_sector package"]
        MCP["mcp_server.py<br/>FastMCP tools"]
        CLI["client.py and market_client.py<br/>HTTP and MCP clients with retries"]
        PAR["parsers.py<br/>normalise source payloads"]
        DB["database.py<br/>DuckDB schema, seeds, cache"]
        MOD["models.py<br/>Pydantic v2 models"]
        AGT["agent.py<br/>agent node and direct-query check"]
        CARD["agent card and keywords<br/>registered in registry_bootstrap"]
        EXE["agents/executor.py<br/>A2A executor"]
        HND["a2a_handlers.py<br/>peer indicator tasks"]
        APP["api/app.py<br/>HTTP sub-app"]
    end
    SRC["Official sources"] --> CLI
    CLI --> PAR --> DB
    DB --> MCP
    CLI --> MCP
    MCP --> AGT
    MOD -.-> PAR
    MOD -.-> AGT
    AGT --> EXE
    HND --> EXE
    EXE --> CARD
    AGT --> APP
```

---

## Figure 3.7: Indicator ownership and declared A2A dependencies

<!-- fig: 3.7 ownership-dependencies -->

- **Caption:** Figure 3.7: Ten sector agents and the seven declared sector-to-sector A2A dependencies.
- **Use in:** 3.5 or 4.x (single source of truth).
- **Description:** Each box is an owner of its indicators. Arrows go from the consumer to the provider and are labelled by the A2A task. The orchestrator (not drawn) may call every agent; every other pair is refused with `DEPENDENCY_NOT_ALLOWED`.

```mermaid
flowchart LR
    PR["prices_sector<br/>CPI, WPI"]
    MO["monetary_sector<br/>repo, M3, liquidity"]
    FI["finance_sector<br/>credit, NPA, rates"]
    FS["fiscal_sector<br/>deficit, GST, capex"]
    EX["external_sector<br/>reserves, trade, USD/INR"]
    RE["real_sector<br/>GDP, GVA, IIP"]
    CM["capital_market_sector<br/>NIFTY, VIX, flows"]
    AG["agriculture_sector<br/>crops, MSP, monsoon"]
    LA["labour_sector<br/>PLFS, EPFO"]
    SV["services_sector<br/>services GVA, PMI"]
    FI -->|"repo_rate"| MO
    FI -->|"cpi_headline"| PR
    FS -->|"repo_rate"| MO
    FS -->|"cpi_headline"| PR
    FS -->|"bank_credit_growth"| FI
    EX -->|"repo_rate"| MO
    EX -->|"cpi_headline"| PR
    RE ~~~ CM
    AG ~~~ LA
    SV ~~~ RE
```

---

## Figure 3.8: Canonical data model

<!-- fig: 3.8 canonical-data-model -->

- **Caption:** Figure 3.8: Entity-relationship diagram of the canonical economic data layer.
- **Use in:** 3.6 Database design.
- **Description:** `CanonicalIndicator` is the registry of what can be measured, `CanonicalObservation` is one measured value with provenance, `CausalRelationship` links two indicators, and `ScenarioResult` records a simulation with the relationship ids it used. These are the Pydantic models in `core/data/schema.py` and the tables `canonical_indicators` and `canonical_observations` in `macro_store.duckdb`.

```mermaid
erDiagram
    CANONICAL_INDICATOR ||--o{ CANONICAL_OBSERVATION : "is measured by"
    CANONICAL_INDICATOR ||--o{ CAUSAL_RELATIONSHIP : "is source of"
    CANONICAL_INDICATOR ||--o{ CAUSAL_RELATIONSHIP : "is target of"
    CAUSAL_RELATIONSHIP }o--o{ SCENARIO_RESULT : "provenance chain"
    CANONICAL_INDICATOR {
        string indicator_id PK
        string name
        string sector
        string subsector
        string unit
        string frequency
        string source_authority
        string source_url
    }
    CANONICAL_OBSERVATION {
        string observation_id PK
        string indicator_id FK
        string observation_period
        double value
        string unit
        string release_timestamp
        string retrieved_timestamp
        string revision_status
        string data_status
        double confidence
        double z_score
        double percentile_rank
        string provenance_hash
    }
    CAUSAL_RELATIONSHIP {
        string relation_id PK
        string source_indicator_id FK
        string target_indicator_id FK
        string relation_type
        int transmission_lag_months
        string elasticity_sign
        double empirical_p_value
        double confidence_score
        string mechanism_description
    }
    SCENARIO_RESULT {
        string scenario_name
        string shock_variable
        double shock_magnitude
        int horizon_periods
        json forecasted_impacts
        list provenance_chain
    }
```

---

## Figure 3.9: Class diagram of the A2A message model

<!-- fig: 3.9 a2a-class-diagram -->

- **Caption:** Figure 3.9: Class diagram of the A2A request, response and provenance models.
- **Use in:** 3.8 Protocol design (or Chapter 4).
- **Description:** Strict Pydantic v2 models that forbid extra fields. `A2ARequest` carries the loop-protection fields (`depth`, `call_chain`, `parent_request_id`). `A2AResponse` must carry `SourceProvenance` records unless it failed.

```mermaid
classDiagram
    class A2ARequest {
        +str request_id
        +str sender_agent
        +str receiver_agent
        +str task
        +dict parameters
        +str conversation_id
        +str parent_request_id
        +int depth
        +tuple call_chain
        +float timeout_seconds
        +datetime timestamp
    }
    class A2AResponse {
        +str request_id
        +str sender_agent
        +str receiver_agent
        +str status
        +result
        +list sources
        +list errors
        +list follow_ups
        +dict metadata
    }
    class SourceProvenance {
        +str source_name
        +str source_url
        +str dataset
        +str table
        +str reporting_period
        +datetime retrieved_at
        +str record_reference
    }
    class A2AErrorInfo {
        +ErrorCode code
        +str message
        +str agent
    }
    class HandlerOutput {
        +result
        +list sources
        +str status
        +list errors
        +list follow_ups
    }
    class A2ACallContext {
        +str conversation_id
        +str request_id
        +str agent_id
        +int depth
        +tuple call_chain
    }
    class IndicatorSignal {
        +str owner_agent
        +list observations
    }
    class IndicatorObservation {
        +str indicator_id
        +float value
        +str unit
        +str observation_period
        +str data_status
    }
    class AgentCard {
        +str agent_id
        +str name
        +list capabilities
        +list skills
        +list supported_tasks
        +str input_schema
        +str output_schema
        +dict metadata
    }
    A2AResponse "1" o-- "0..*" SourceProvenance
    A2AResponse "1" o-- "0..*" A2AErrorInfo
    HandlerOutput "1" o-- "0..*" SourceProvenance
    IndicatorSignal "1" o-- "1..*" IndicatorObservation
    A2ARequest ..> A2AResponse : answered by
    AgentCard ..> A2ARequest : advertises tasks for
    A2ACallContext ..> A2ARequest : derives child
```

---

## Figure 3.10: Class diagram of knowledge-graph and scenario components

<!-- fig: 3.10 kg-class-diagram -->

- **Caption:** Figure 3.10: Principal classes of the knowledge graph, scenario engine and optional Neo4j store.
- **Use in:** 3.9 Knowledge graph design (or Chapter 6).
- **Description:** The ontology owns indicators and relationships and validates them. The NetworkX engine builds the in-memory graph and answers path and impact queries. The causal engine uses the graph to simulate shocks. The Neo4j store mirrors the ontology and is optional.

```mermaid
classDiagram
    class MacroeconomicOntology {
        +dict indicators
        +list relationships
        +validate()
    }
    class NetworkXGraphEngine {
        +graph
        +ontology
        +has_node(id)
        +get_shortest_transmission_path(src, dst)
        +get_causal_neighborhood(id, depth)
        +get_downstream_impacts(id)
        +generate_mermaid_diagram(focus)
    }
    class CausalEconometricEngine {
        +test_granger_causality(data, cause, effect, max_lag)
        +simulate_scenario(name, shock_variable, magnitude, horizon, baselines)
    }
    class Neo4jKnowledgeGraphStore {
        +enabled
        +sync_ontology()
        +query_transmission_path(src, dst)
        +get_causal_neighborhood(id)
        +close()
    }
    class CanonicalIndicator
    class CausalRelationship
    class ScenarioResult
    MacroeconomicOntology "1" *-- "20" CanonicalIndicator
    MacroeconomicOntology "1" *-- "12" CausalRelationship
    NetworkXGraphEngine --> MacroeconomicOntology : builds from
    CausalEconometricEngine --> NetworkXGraphEngine : traverses
    CausalEconometricEngine ..> ScenarioResult : returns
    Neo4jKnowledgeGraphStore ..> MacroeconomicOntology : mirrors
```

---

## Figure 3.11: Configuration and API-key topology

<!-- fig: 3.11 configuration-topology -->

- **Caption:** Figure 3.11: Configuration sources and the six-key LLM credential convention.
- **Use in:** 3.7 Implementation environment.
- **Description:** `PlatformSettings` reads `backend/.env`. Each of the six Groq keys is shared by a pair of sectors to spread rate limits; the orchestrator has its own key. If no key resolves, every LLM call returns the unavailable notice and the deterministic fallback is used.

```mermaid
flowchart LR
    ENV["backend/.env"] --> PS["PlatformSettings<br/>core/config.py"]
    PS --> K1["AGR_REAL_KEY<br/>agriculture and real"]
    PS --> K2["FIN_FIS_KEY<br/>finance and fiscal"]
    PS --> K3["CAP_MON_KEY<br/>capital markets and monetary"]
    PS --> K4["ORCH_KEY<br/>orchestrator"]
    PS --> K5["PRIC_LAB_KEY<br/>prices and labour"]
    PS --> K6["SERV_EXT_KEY<br/>services and external"]
    PS --> OT["FAST_MODEL, REASONING_MODEL,<br/>TVLY_KEY_1..3, A2A_*, NEO4J_*, CORS_ORIGINS"]
    K1 --> SR["sector_reasoning.py<br/>and sector agents"]
    K2 --> SR
    K3 --> SR
    K5 --> SR
    K6 --> SR
    K4 --> LC["orchestrator llm_client"]
    SR --> Q{"Key resolved?"}
    LC --> Q
    Q -->|"yes"| LLM["Groq LLM call"]
    Q -->|"no"| FB["Deterministic offline fallback"]
```
