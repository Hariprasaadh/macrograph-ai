# Macrograph AI — Production Implementation Plan & Engineering Roadmap Tracker

## Executive Summary & Mission
**Macrograph AI** is an academically rigorous, multi-agent macroeconomic intelligence platform specialized in the Indian economy. This document serves as the master production engineering roadmap, establishing:
1. **Exhaustive Codebase Audit**: Exact inventory of completed infrastructure across analytical data stores, multi-agent protocols, knowledge graphs, and orchestration pipelines.
2. **Code Modifications & Architectural Refactoring**: Remediation of current architectural bottlenecks (e.g., consolidating the 3-executor MVP into 8 independent domain executors).
3. **Live Official API Ingestion Contracts**: Standardized API endpoint matrix, strict fail-fast error schemas, and circuit breakers eliminating all mock or hardcoded data.
4. **Data Integrity & Deduplication Invariants**: DuckDB schema evolution, composite unique constraints, and upsert mechanics.
5. **Phase-by-Phase Roadmap with Definition of Done (DoD)**: Measurable, testable criteria for upcoming milestones spanning dedicated domain agents, vector RAG, interactive frontend dashboard, and containerization.
6. **Resilience & Risk Mitigation**: Operational strategies for government portal downtime, rate limits, and CI/CD test reproducibility.

---

## 1. What We Have Completed So Far

### 1.1 Canonical Data Layer & Analytical Storage Core
- [x] **Canonical Data Schemas** ([backend/core/data/schema.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/data/schema.py)):
  - Built strict Pydantic v2 schemas: `CanonicalIndicator`, `CanonicalObservation`, `CausalRelationship`, `ScenarioResult`, `Evidence`, and `AgentAnalysis`.
  - Defined standard enums: `SectorEnum` (8 canonical macro domains), `DataStatusEnum` (`live`, `verified_historical`, `unavailable`), `RevisionStatusEnum` (`flash`, `provisional`, `revised`, `final`), and `CausalRelationType` (5-tier causal taxonomy).
  - Built automatic `SHA-256` observation provenance digest generator hashing `indicator_id:observation_period:value:unit:data_status`.
- [x] **Embedded Columnar DuckDB Store** ([backend/core/database/macro_store.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/database/macro_store.py)):
  - Initialized `macro_store.duckdb` with persistent tables: `canonical_indicators`, `canonical_observations`, `causal_relationships`, `provenance_records`, and legacy `macro_series`.
  - Built deterministic in-process statistical aggregations: rolling historical Z-scores and percentile ranking ($0-100\%$).
  - Seeded official historical baseline indicators across all 8 sectors from MoSPI, RBI DBIE, Office of Economic Adviser, and EIA/Markets.

### 1.2 Knowledge Graph & Econometric Inference Core
- [x] **8-Domain Macroeconomic Ontology** ([backend/core/knowledge_graph/ontology.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/knowledge_graph/ontology.py)):
  - Registered 20+ canonical indicators across Real Economy, Prices, Monetary, Fiscal, External, Capital Markets, Agriculture, and Labour.
  - Constructed the 5-tier causal transmission network linking international commodity shocks (Brent Crude) through domestic price indices (WPI, CPI) and monetary levers (Repo Rate, Bank Credit) to real output (GDP) and market valuations (NIFTY 50).
- [x] **NetworkX Directed Graph Engine** ([backend/core/knowledge_graph/networkx_engine.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/knowledge_graph/networkx_engine.py)):
  - Sub-millisecond shortest transmission path discovery between any two canonical indicator nodes.
  - Multi-hop cumulative lag calculation (months) and directional elasticity compounding.
  - Downstream reachability impact analysis for systemic shock cascade evaluation.
  - Dynamic Mermaid diagram generation for visual report rendering.
- [x] **Neo4j Enterprise Graph Store Adapter** ([backend/core/knowledge_graph/neo4j_store.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/knowledge_graph/neo4j_store.py)):
  - Cypher query generator for persistent enterprise deployments with automatic fallback to NetworkX if Neo4j is offline.
- [x] **Causal Econometric Scenario Engine** ([backend/core/econometrics/causal_engine.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/econometrics/causal_engine.py)):
  - Multi-period impulse response simulation engine propagating magnitude shocks along causal paths.
  - Empirical Granger causality statistical $F$-test engine with stationarity transformations and p-value validation.

### 1.3 Inter-Agent Communication & Tool Protocols
- [x] **Agent-to-Agent (A2A) Protocol** ([backend/core/protocols/a2a/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/protocols/a2a/)):
  - Pydantic models: `AgentCard`, `SkillDefinition`, `TaskRequest`, `TaskResponse`, `A2AArtifact`, `StreamingChunk`.
  - Central `AgentRegistry` supporting dynamic skill discovery, capability matching, and runtime task routing.
  - Server-Sent Events (SSE) compliant async chunk streaming (`streaming.py`).
  - Formal task lifecycle state machine (`SUBMITTED` $\rightarrow$ `WORKING` $\rightarrow$ `COMPLETED` / `FAILED`).
- [x] **Model Context Protocol (FastMCP)**:
  - 6 active FastMCP servers (`real_sector_mcp`, `finance_sector_mcp`, `capital_markets_mcp`, `prices_sector_mcp`, `monetary_sector_mcp`, `labour_sector_mcp`).
  - Standard FastMCP client abstraction ([backend/core/protocols/mcp/client.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/protocols/mcp/client.py)).

### 1.4 Multi-Agent Orchestration & Unified API Gateway
- [x] **LangGraph Orchestrator Graph** ([backend/core/orchestrator/graph.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/orchestrator/graph.py)):
  - 4-stage StateGraph: `decompose_node` $\rightarrow$ `parallel_a2a_execute_node` $\rightarrow$ `kg_causal_enrichment_node` $\rightarrow$ `synthesis_node`.
  - Resilient LLM client (`llm_client.py`) utilizing Groq Cloud (`llama-3.3-70b-versatile` with exponential retry, fallback to `llama-3.1-8b-instant` on rate limits, and deterministic offline synthesis).
- [x] **Unified FastAPI Gateway** ([backend/main.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/main.py)):
  - Endpoints: `/health`, `/api/v1/analyze`, `/api/v1/simulate`, `/api/v1/kg/path`, `/api/v1/kg/impacts`, `/a2a/registry`.
  - Mounted sector sub-applications: `/real-sector`, `/finance-sector`, `/capital-markets`.
- [x] **Automated Test Suite** ([backend/tests/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/tests/)):
  - 27/27 unit and integration tests passing across A2A streaming, canonical ingestion, data integrity, FastMCP servers, Knowledge Graph causal paths, and LangGraph orchestration.
- [x] **Reusable Skill Ecosystem**:
  - 13 comprehensive skills installed in [`.agents/skills/`](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/.agents/skills) with YAML frontmatter and strict Live API mandates.

---

## 2. Changes & Modifications Required in Existing Code

The following technical modifications are required to scale from the current MVP to an enterprise multi-agent architecture:

| Priority | Component | File | Current Limitation | Required Modification |
| :---: | :--- | :--- | :--- | :--- |
| **P0 (Critical)** | A2A Registry Bootstrap | [backend/core/orchestrator/registry_bootstrap.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/orchestrator/registry_bootstrap.py) | Only 3 executors registered (`Real`, `Finance`, `CapitalMarkets`). | Implement and register dedicated A2A executors: `PricesInflationAgentExecutor`, `MonetaryBankingAgentExecutor`, `LabourEmploymentAgentExecutor`, `AgricultureRuralAgentExecutor`, `FiscalSectorAgentExecutor`, and `ExternalSectorAgentExecutor`. |
| **P0 (Critical)** | Orchestrator Routing | [backend/core/orchestrator/graph.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/orchestrator/graph.py#L93-L102) | `sector_agent_map` maps Prices, Monetary, Fiscal, and External all to Finance Sector, and Agri/Labour to Real Sector. | Decouple routing so all 8 sectors route directly to their respective dedicated domain agents for granular task isolation. |
| **P1 (High)** | Live API Ingestion Adapters | [backend/core/ingestion/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/ingestion/) | Ingestion relies on static seed data or mock endpoints. | Build live HTTP/REST client adapters for MoSPI, RBI DBIE, Yahoo Finance, and EPFO with fail-fast error handling. |
| **P1 (High)** | DuckDB Deduplication & Key Constraints | [backend/core/database/macro_store.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/database/macro_store.py#L45-L63) | Table `canonical_observations` allows duplicate rows on repeated polling. | Add composite unique constraint on `(indicator_id, observation_period)` with `ON CONFLICT DO UPDATE` upsert semantics. |
| **P2 (Medium)** | FastAPI Sub-App Mounts | [backend/main.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/main.py#L48-L50) | Only `/real-sector`, `/finance-sector`, and `/capital-markets` sub-apps mounted. | Create and mount sub-apps for `/prices-sector`, `/monetary-sector`, `/labour-sector`, and `/agriculture-sector`. |
| **P2 (Medium)** | Dynamic Graph Recalibration | [backend/core/knowledge_graph/networkx_engine.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/knowledge_graph/networkx_engine.py) | Transmission lags and elasticities are statically configured in `ontology.py`. | Implement periodic background job running rolling Pearson cross-correlations and Granger causality tests on DuckDB time series to recalibrate edge weights and transmission lags. |

---

## 3. Live Official API Ingestion Contracts & Error Handling

To satisfy the **Zero Hardcoded Data Mandate**, all indicator feeds must be dynamically ingested from official APIs. If a feed is unavailable, tools and agents must fail fast with a standardized error response.

### 3.1 Official Live API Endpoint Matrix

| Domain Sector | Primary Indicator | Official Live Data Source | Integration Technology | Fallback Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Real Economy** | `in.macro.real.gdp_growth`, `iip_growth` | MoSPI e-Sankhyiki / National Accounts Portal API | `requests` / `httpx` (JSON REST API) | Structured Error (HTTP 502) |
| **Prices & Inflation**| `in.macro.prices.cpi_headline`, `wpi_all` | MoSPI CPI Data Portal + DPIIT WPI Feed | `requests` / `beautifulsoup4` table extractor | Structured Error (HTTP 502) |
| **Prices & Inflation**| `in.macro.prices.brent_crude` | EIA / Yahoo Finance Benchmark Spot (`BZ=F`) | `yfinance` (`Ticker("BZ=F").history`) | Structured Error (HTTP 503) |
| **Monetary & Banking**| `in.macro.monetary.repo_rate`, `bank_credit` | RBI Data Warehouse (DBIE SDMX / REST endpoints) | `requests` with XML/JSON parsing | Structured Error (HTTP 502) |
| **Fiscal Sector** | `in.macro.fiscal.debt_to_gdp`, `capex_growth`| Controller General of Accounts (CGA) / MoF Portal | Open Government Data (data.gov.in) API | Structured Error (HTTP 502) |
| **External Sector** | `in.macro.external.forex_reserves`, `trade_deficit` | RBI Weekly Statistical Supplement + MoC Trade API | `requests` / XML parser | Structured Error (HTTP 502) |
| **External Sector** | `in.macro.external.usd_inr_exchange_rate` | RBI Reference Rate / Yahoo Finance (`INR=X`) | `yfinance` (`Ticker("INR=X").history`) | Structured Error (HTTP 503) |
| **Capital Markets** | `in.macro.capmarkets.nifty_50`, `india_vix` | National Stock Exchange (NSE) / Yahoo Finance (`^NSEI`, `^INDIAVIX`) | `yfinance` / NSE official quote API | Structured Error (HTTP 503) |
| **Capital Markets** | `in.macro.capmarkets.dii_mutual_fund_flows` | AMFI India Industry Data Portal / SEBI | AMFI Daily/Monthly Data Feeds | Structured Error (HTTP 502) |
| **Agriculture & Rural**| `in.macro.agri.foodgrain_production`, `msp` | Ministry of Agriculture (Agmarknet API / CCEA releases) | Data.gov.in Agmarknet REST API | Structured Error (HTTP 502) |
| **Labour & Employment**| `in.macro.labour.epfo_additions` | EPFO Monthly Payroll Portal Data Services | `requests` against EPFO payroll bulletin API | Structured Error (HTTP 502) |

### 3.2 Standardized Live API Error Schema (`APIErrorResponse`)

When an external live API endpoint fails, domain agents and FastMCP servers must return this Pydantic-validated error structure:

```python
class LiveAPIErrorResponse(BaseModel):
    status: str = Field(default="error")
    error_code: str = Field(..., description="E.g. LIVE_API_TIMEOUT, UPSTREAM_AUTH_ERROR, DATA_FORMAT_INVALID")
    domain_sector: SectorEnum
    target_indicator: str = Field(..., description="Canonical indicator ID attempted")
    source_authority: str = Field(..., description="MoSPI, RBI, NSE, AMFI, etc.")
    endpoint_attempted: str
    http_status_code: int = Field(..., description="Upstream or gateway HTTP status")
    failure_reason: str = Field(..., description="Explanatory failure message")
    retry_attempted: int = Field(default=3)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

### 3.3 Circuit Breaker & Retry Policy
- **Tenacity Retry Configuration**: Maximum 3 retries with exponential backoff ($1.0\text{s}$, $2.0\text{s}$, $4.0\text{s}$) on network timeouts.
- **Fail-Fast Circuit Breaker**: If 3 consecutive requests to an external government portal fail, trip the circuit for 60 seconds to protect system responsiveness. Return immediate `LIVE_API_UNAVAILABLE` error to the Orchestrator without hanging.

---

## 4. DuckDB Schema Evolution & Deduplication Invariants

To support recurring live data streaming without data corruption or duplicate rows:

### 4.1 Schema DDL Migration Script
```sql
-- 1. Create unique composite index for observation deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_canonical_obs_unique 
ON canonical_observations (indicator_id, observation_period);

-- 2. Create index for high-speed chronological time-series retrieval
CREATE INDEX IF NOT EXISTS idx_canonical_obs_lookup 
ON canonical_observations (indicator_id, observation_period DESC);
```

### 4.2 Ingestion Upsert Contract
```python
def upsert_canonical_observation(self, obs: CanonicalObservation) -> None:
    """Inserts or updates an empirical observation without creating duplicate records."""
    query = """
        INSERT INTO canonical_observations (
            observation_id, indicator_id, observation_period, value, unit,
            release_timestamp, retrieved_timestamp, revision_status, data_status,
            confidence, z_score, percentile_rank, provenance_hash, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (indicator_id, observation_period) DO UPDATE SET
            value = EXCLUDED.value,
            revision_status = EXCLUDED.revision_status,
            retrieved_timestamp = EXCLUDED.retrieved_timestamp,
            data_status = EXCLUDED.data_status,
            provenance_hash = EXCLUDED.provenance_hash,
            metadata_json = EXCLUDED.metadata_json;
    """
    with self.get_connection() as con:
        con.execute(query, [
            obs.observation_id, obs.indicator_id, obs.observation_period, obs.value, obs.unit,
            obs.release_timestamp, obs.retrieved_timestamp, obs.revision_status.value, obs.data_status.value,
            obs.confidence, obs.z_score, obs.percentile_rank, obs.provenance_hash, json.dumps(obs.metadata)
        ])
```

---

## 5. Prioritized Phased Implementation Roadmap with Definitions of Done (DoD)

```
[Phase 1: Core Foundation]  ─────>  [Phase 2: Docs & Memory]  ─────>  [Phase 3: 8 Dedicated Domain Agents]
       (COMPLETED)                         (COMPLETED)                           (TARGET: WEEK 1)
                                                                                         │
[Phase 6: Containerization] <───── [Phase 5: React Dashboard] <───── [Phase 4: Policy Vector RAG]
     (TARGET: WEEK 4)                    (TARGET: WEEK 3)                    (TARGET: WEEK 2)
```

---

### Phase 2: System Documentation, Institutional Memory & Skill System (Status: COMPLETED)
- [x] Author comprehensive [AGENTS.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/AGENTS.md) with 8 domain agent specs, A2A schemas, FastMCP catalogs, and operational rules.
- [x] Author [MEMORY.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/MEMORY.md) capturing architectural decisions, canonical data taxonomies, and invariant rules.
- [x] Author publication-grade root [README.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/README.md) with architecture flowcharts, quickstart, and API references.
- [x] Install 13 modular skills natively in [`.agents/skills/`](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/.agents/skills) and delete redundant root `skills/` folder.
- [x] Author version-controlled [IMPLEMENTATION_PLAN.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/IMPLEMENTATION_PLAN.md).

---

### Phase 3: Complete 8-Domain A2A Agent Decoupling & Live Feeds (Target: Week 1)
- [ ] **Task 3.1**: Implement `PricesInflationAgentExecutor` in `backend/prices_sector/agents/executor.py` with live CPI/WPI/Crude oil client.
- [ ] **Task 3.2**: Implement `MonetaryBankingAgentExecutor` in `backend/monetary_sector/agents/executor.py` with live RBI DBIE rate client.
- [ ] **Task 3.3**: Implement `LabourEmploymentAgentExecutor` in `backend/labour_sector/agents/executor.py` with live EPFO payroll client.
- [ ] **Task 3.4**: Implement `AgricultureRuralAgentExecutor` in `backend/agriculture_sector/` with Agmarknet API client.
- [ ] **Task 3.5**: Implement `FiscalSectorAgentExecutor` and `ExternalSectorAgentExecutor`.
- [ ] **Task 3.6**: Update `registry_bootstrap.py` to register all 8 domain executors with central `agent_registry`.
- [ ] **Task 3.7**: Update `graph.py` to route queries across all 8 sectors independently.
- [ ] **Task 3.8**: Mount all 8 sub-apps in `backend/main.py`.

#### Definition of Done (DoD) for Phase 3:
1. `GET /a2a/registry` returns exactly 8 registered `AgentCard` objects.
2. Every domain executor implements live API data ingestion with fail-fast `LiveAPIErrorResponse`.
3. Test suite expands to at least 40 tests covering all 8 domain executors and mocks of live endpoints.
4. All existing 27 tests remain green.

---

### Phase 4: Policy Document Vector RAG via Qdrant (Target: Week 2)
- [ ] **Task 4.1**: Initialize Qdrant client (`qdrant-client`) with local persistent storage.
- [ ] **Task 4.2**: Implement PDF document ingestion pipeline (`backend/core/rag/ingest_docs.py`):
  - Extract and chunk text (500–800 tokens, 10% overlap).
  - Generate embeddings using `text-embedding-3-small` or local HuggingFace `BAAI/bge-small-en-v1.5`.
  - Store metadata (source authority, document title, publication date, URL, excerpt).
- [ ] **Task 4.3**: Ingest official base papers and documents:
  - RBI Monetary Policy Committee (MPC) resolution statements (2024–2026).
  - Union Budget 2024–2026 speeches and fiscal deficit tables.
  - Ministry of Finance Economic Survey 2024–2026 chapters.
- [ ] **Task 4.4**: Create FastMCP tool `search_policy_circulars(query: str, domain: Optional[str])`.
- [ ] **Task 4.5**: Integrate RAG retrieval node into LangGraph orchestrator (`rag_policy_enrichment_node`).

#### Definition of Done (DoD) for Phase 4:
1. Qdrant collection `policy_circulars` populated with at least 500 semantic chunks from official documents.
2. Orchestrator research reports include verbatim official policy quotes alongside empirical data tables.
3. Unit tests verify semantic retrieval accuracy and citation metadata integrity.

---

### Phase 5: Interactive Web Dashboard in `frontend/` (Target: Week 3)
- [ ] **Task 5.1**: Scaffold React + Vite + TypeScript web application in `frontend/`.
- [ ] **Task 5.2**: Implement Macroeconomic Overview Panel:
  - KPI metric cards for GDP, CPI, Repo Rate, Forex Reserves, and NIFTY 50 with real-time Z-score badges.
  - Interactive historical time-series charts using Plotly / Chart.js.
- [ ] **Task 5.3**: Implement Interactive Knowledge Graph Canvas:
  - Cytoscape.js or React Flow canvas rendering nodes and 5-tier causal transmission edges.
  - Click-to-inspect shortest path between any two clicked nodes with cumulative latency badges.
- [ ] **Task 5.4**: Implement Scenario Simulation Studio:
  - Sliders for shock variables (e.g. Brent Crude $+20\%$, Repo Rate $-50\text{ bps}$).
  - Multi-horizon comparison plot showing baseline vs. forecasted impulse trajectory.
- [ ] **Task 5.5**: Implement Conversational Research Interface:
  - Streaming SSE chat UI rendering markdown reports, Mermaid diagrams, and collapsible provenance hashes.

#### Definition of Done (DoD) for Phase 5:
1. Frontend runs locally via `npm run dev` and communicates with backend at `http://127.0.0.1:8000`.
2. Graph canvas renders all 20+ canonical nodes and 15+ causal transmission edges with color-coded causal tiers.
3. Scenario simulation sliders trigger `/api/v1/simulate` and update forecast charts in under 300ms.

---

### Phase 6: Production Packaging & Containerization (Target: Week 4)
- [ ] **Task 6.1**: Author multi-stage `backend/Dockerfile` (Python 3.12 slim, non-root user).
- [ ] **Task 6.2**: Author multi-stage `frontend/Dockerfile` (Node.js build + Nginx alpine runtime).
- [ ] **Task 6.3**: Author root `docker-compose.yml` orchestrating:
  - `gateway`: FastAPI backend server.
  - `frontend`: React web dashboard.
  - `neo4j`: Enterprise graph database with persistent volume.
  - `qdrant`: Vector database with persistent volume.
  - Persistent volume mount for `macro_store.duckdb`.
- [ ] **Task 6.4**: Set up GitHub Actions CI/CD workflow running pytest, linting (`ruff`/`pyright`), and Docker image builds.

#### Definition of Done (DoD) for Phase 6:
1. `docker compose up -d` boots the entire platform cleanly with healthy container status.
2. End-to-end integration tests execute successfully inside the container environment.
3. Zero credentials or secret keys committed to version control.

---

## 6. Resilience, External Downtime & Risk Mitigation Strategy

| Risk Factor | Probability | Impact | Mitigation Architecture |
| :--- | :---: | :---: | :--- |
| **Government Portal Downtime** (MoSPI, RBI DBIE maintenance) | Medium | High | **Circuit Breaker & Degraded Synthesis**: If live API fails after 3 retries, return structured `LiveAPIErrorResponse`. The Orchestrator surfaces an explicit "External Feed Degraded" notice in the executive summary and uses verified cached historical data with clear timestamp disclaimers. |
| **Groq Cloud API Rate Limits** (HTTP 429) | High | Medium | **Dual-Tier Backoff**: Built-in exponential backoff in `llm_client.py`, instant fallback from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant`, and ultimate fallback to deterministic local analytical synthesis without failing user requests. |
| **CI/CD Flakiness on Live Endpoints** | High | High | **VCR / Mock Recording**: All automated unit and regression tests run against recorded VCR cassettes or local DuckDB snapshots. Tests never make unmocked outbound HTTP calls to third-party government servers during CI/CD execution. |
| **Neo4j Offline / Connection Loss** | Medium | Low | **In-Memory NetworkX Fallback**: NetworkX engine runs entirely in-process in Python RAM. If Neo4j connection fails, the platform continues graph path discovery and Mermaid generation with zero interruption. |

---

## 7. Verification & Quality Assurance Matrix

| Layer | Verification Method | Automated Command | Target Threshold |
| :--- | :--- | :--- | :--- |
| **Unit & Integration Tests** | `pytest` with coverage report | `.venv\Scripts\pytest backend/tests -v` | 100% passing tests (27/27 current, $\ge 40$ in Phase 3) |
| **Type Safety & Schema** | `pyright` / `pydantic` validation | `.venv\Scripts\pyright backend` | 0 type errors across core schemas |
| **Platform Demo Execution** | End-to-end pipeline script | `.venv\Scripts\python backend/demo_platform.py` | Exit code 0, complete report synthesis |
| **FastAPI Gateway Health** | REST Healthcheck query | `curl http://127.0.0.1:8000/health` | HTTP 200, `status: "healthy"` |
| **Skill Structure** | Antigravity YAML validation | Custom script inspecting `.agents/skills/*/SKILL.md` | 13/13 valid frontmatter & Live API mandates |
