# Macrograph-AI: Multi-Agent Indian Macroeconomic Intelligence Platform

Macrograph-AI decomposes the Indian economy into **10 sector agents** that reason with each other over an internal **A2A protocol** (agent-to-agent), retrieve data only through per-sector **FastMCP** tool servers (agent-to-data), and are coordinated by a **LangGraph** orchestrator. Cross-sector answers are grounded in a **causal knowledge graph** of 20 canonical indicators and 12 typed transmission edges, simulated with a transparent graph-attenuation model, and rendered with source, observation period and provenance hash for every number.

Status date: 2026-10-12. See [docs/status-and-roadmap.md](docs/status-and-roadmap.md) for what is production-grade, what is a prototype, and the research roadmap.

---

## Core Architecture

### 1. A2A vs FastMCP: never conflate
- **A2A (agent-to-agent reasoning):** peer coordination, delegation, structured conclusions. Implemented in `backend/core/protocols/a2a` (typed `A2ARequest`/`A2AResponse`, `A2AServer` guards, `A2AClient` retries, card-based router, declared sector edges, trace store). It is a project-native implementation shaped after the A2A specification; the `a2a-sdk` package is listed as a dependency but is not imported by the runtime.
- **FastMCP (agent-to-data):** each sector owns an MCP server (`<sector>/mcp_server.py`) that reads official statistical sources, DuckDB tables and curated snapshots.
- **Rule:** an agent never fetches another agent's data. Sector packages never import each other; peer indicators arrive through `core/protocols/a2a/peers.py` and each sector's `a2a_handlers.py`, restricted to the edges declared in `dependencies.py`.

Details: [docs/a2a-architecture.md](docs/a2a-architecture.md).

### 2. One owner per indicator

| Primary indicators | Owner | Declared A2A consumers |
| :--- | :--- | :--- |
| CPI, WPI, food/fuel/core inflation | `prices_sector` | Finance, Fiscal, External |
| Repo, SDF, MSF, M1/M3, liquidity | `monetary_sector` | Finance, Fiscal, External |
| Bank credit growth, NPA, lending rates | `finance_sector` | Fiscal |
| Fiscal deficit, GST, Union capex | `fiscal_sector` | - |
| NIFTY, India VIX, FII/DII, G-Sec | `capital_market_sector` | - |
| Trade balance, reserves, BoP, USD/INR | `external_sector` | - |
| GDP, GVA, IIP, GFCF | `real_sector` | - |
| PLFS unemployment, EPFO | `labour_sector` | - |
| Services GVA, PMI, IT exports | `services_sector` | - |
| Crops, MSP, mandi prices, monsoon | `agriculture_sector` | - |

Only seven sector-to-sector A2A edges are declared today (finance, fiscal and external consuming repo rate, CPI and bank credit growth). The orchestrator may call every agent. Everything else flows through the orchestrator.

### 3. No source, no answer
Hardcoded or estimated figures must never be presented as fact. Each observation carries source agent, MCP tool or official source with table, value, unit, observation period, `data_status` and a SHA-256 `provenance_hash`. Unavailable data returns a structured unavailable status. Curated baseline snapshots seeded into sector DuckDB stores are tagged `cached` with their publication reference. Fixed simulation defaults are labelled `DEFAULT` and are replaced by live observations when available.

---

## Orchestrator flow

```
USER QUERY
   |
   v
decompose           capability routing over registered Agent Cards (keyword/skill match; LLM only if no card matches)
   |
   v
parallel_a2a_execute  A2A delegation to routed sector agents -> observations, reports, sources, errors, trace
   |
   v
kg_causal_enrichment  shortest transmission paths between observed indicators; optional shock simulation
   |                  (live observations override default baselines)
   v
synthesis           cited report: indicator matrix with provenance hashes, Mermaid causal diagram,
                    path table, scenario table, source table, unavailable-agent list, taxonomy note
```

Single-sector questions bypass the orchestrator through each sector's `is_direct_<sector>_query` check and the shared `core/sector_reasoning.py` helper. Without an LLM key every stage degrades to a deterministic offline summary.

### Analysis layers added since v1.0

| Layer | Location | What it does |
| :--- | :--- | :--- |
| Causal knowledge graph | `core/knowledge_graph` | Ontology of 20 indicators and 12 edges classified on a 5-tier taxonomy (THEORY, STATISTICAL_ASSOCIATION, LAGGED_RELATIONSHIP, GRANGER_PREDICTIVE, STRUCTURAL_CAUSAL_MODEL); NetworkX engine; optional Neo4j mirror. |
| Scenario engine | `core/econometrics/causal_engine.py` | Heuristic graph-attenuation shock propagation (per-hop `0.55 x confidence`, global scale 0.15, +/-25% band) plus a bivariate Granger test helper. It is not a VAR/IRF model. |
| Research lab | `core/research` | Trajectory (Shockwave), base-vs-shocked attribution (Twin), rolling z-score anomaly radar classified against the graph, simulated six-seat MPC, Edge Evidence Audit (SEEDED vs EMPIRICAL via Granger on live series), consensus rollup and model card. |
| Daily brief | `core/briefing` | Telemetry + anomaly scan + cached news + one LLM call with deterministic fallback; DuckDB-backed history; optional 08:15 IST cron (`BRIEF_CRON_ENABLED`). |
| Claim verification | `core/verification` | Typed claim proposals verified against content-addressed evidence snapshots with Decimal arithmetic and an append-only SQLite audit. Currently a standalone, tested library; not yet wired into any sector or the orchestrator (see roadmap). |

---

## The 10 sector agents

| # | Sector | Package | Scope | Primary sources |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Real | `backend/real_sector/` | GDP, GVA, GFCF, IIP | MoSPI e-Sankhyiki MCP (NAS, IIP) |
| 2 | Agriculture | `backend/agriculture_sector/` | Production, MSP, mandi prices, monsoon | Agmarknet, DAC&FW, IMD, data.gov.in |
| 3 | Prices | `backend/prices_sector/` | CPI, WPI, subgroups, market proxies | MoSPI e-Sankhyiki MCP, Yahoo Finance, Tavily |
| 4 | Monetary | `backend/monetary_sector/` | Repo corridor, M3, liquidity, stance | RBI DBIE |
| 5 | Finance | `backend/finance_sector/` | Bank credit, GNPA, WALR/MCLR, CD ratio | RBI DBIE tables |
| 6 | Capital Markets | `backend/capital_market_sector/` | NIFTY, VIX, FII/DII, G-Sec, USD/INR | yfinance, SEBI |
| 7 | Fiscal | `backend/fiscal_sector/` | Deficit, GST, capex, debt | CGA, Union Budget, GST Council |
| 8 | External | `backend/external_sector/` | Reserves, USD/INR, trade, BoP | RBI, DGCI&S, IMF |
| 9 | Labour | `backend/labour_sector/` | PLFS, EPFO, wages | MoSPI PLFS, EPFO |
| 10 | Services | `backend/services_sector/` | Services GVA, PMI, IT/ITeS | MoSPI, PMI releases |

Per-sector READMEs live in each package. Sector maturity differs: Prices, Fiscal and Real are the most complete (A2A handlers, research modules, tests); the rest vary.

---

## Tech stack (as implemented)

| Component | Technology |
| :--- | :--- |
| Runtime | Python 3.12, `uv`, `uv.lock` |
| Orchestration | LangGraph `StateGraph` (4 nodes) |
| Agent protocol | Native A2A layer (typed messages, guards, trace) |
| Data tools | FastMCP, one server per sector |
| Gateway | FastAPI + Uvicorn, SSE streaming chat |
| Analytical store | DuckDB (`macro_store.duckdb`, per-sector stores), SQLite (claim audits) |
| Knowledge graph | NetworkX, optional Neo4j (`NEO4J_URI`) |
| Econometrics | statsmodels (Granger), pandas, NumPy |
| LLM | Groq via `langchain-groq` / `groq`; defaults `openai/gpt-oss-20b` (fast) and `openai/gpt-oss-120b` (reasoning); OpenAI optional; offline fallback |
| Frontend | React 18, TypeScript (strict), Vite, Tailwind, GSAP, Mermaid, react-markdown |

PydanticAI and Qdrant appear in earlier design documents but are not implemented. Documentary (RAG) evidence is reported as unavailable in every report.

---

## Project structure

```text
macrograph-ai/
├── README.md, CLAUDE.md, pyproject.toml, uv.lock, mcp.json
├── docs/                      architecture, API guide, A2A, claim verification, status and roadmap
│   └── images/                98 report figures: descriptions, Mermaid sources, rendered PNG and SVG (see docs/images/README.md)
├── tasks/                     todo.md, lessons.md, KG implementation instructions
├── base_papers/               reference literature
├── .agents/                   agent contract (AGENTS.md), rules, skills, MEMORY.md snapshot
├── backend/
│   ├── main.py                unified gateway, sector mounts, /api/v1/analyze|simulate|kg/*
│   ├── api/                   chat (SSE), dashboard, research lab, daily brief routers
│   ├── core/
│   │   ├── config.py          PlatformSettings
│   │   ├── orchestrator/      LangGraph graph, A2A dispatch, registry bootstrap, canonical IDs, LLM client
│   │   ├── protocols/{a2a,mcp}/
│   │   ├── knowledge_graph/   ontology, NetworkX engine, Neo4j store
│   │   ├── econometrics/      causal engine
│   │   ├── research/          trajectory, attribution, anomaly, mpc, edge_audit, consensus, model_card
│   │   ├── briefing/          daily brief job and store
│   │   ├── verification/      claim verification library
│   │   ├── ingestion/         MoSPI client, normalizer, validators, scheduler
│   │   ├── database/          DuckDB macro store
│   │   └── sector_reasoning.py
│   ├── <sector>_sector/       10 sector packages (mcp_server, agent, client, models, api, executor, tests)
│   └── tests/                 cross-cutting pytest suite
└── frontend/src/              App, chat workspace, dashboard tabs, Causal Lab, KG view, A2A registry
```

---

## Quickstart

```powershell
git clone https://github.com/Hariprasaadh/macrograph-ai.git
cd macrograph-ai
uv pip install -e .
cp backend/.env.example backend/.env    # fill in keys (see below)
```

Environment (`backend/.env`): six Groq keys following the pair convention (`AGR_REAL_KEY`, `FIN_FIS_KEY`, `CAP_MON_KEY`, `ORCH_KEY`, `PRIC_LAB_KEY`, `SERV_EXT_KEY`), optional `TVLY_KEY_1..3` (Tavily), `FAST_MODEL`, `REASONING_MODEL`, A2A guards (`A2A_*`), optional `NEO4J_URI`, optional `BRIEF_CRON_ENABLED=true`. With no key the platform runs deterministically offline.

```powershell
pytest                                   # default testpaths only (374 tests); other sector suites: see CLAUDE.md. Full run 2026-10-12: 550 passed, 1 failed
python backend/demo_platform.py          # end-to-end multi-agent demo

cd backend; uvicorn main:app --reload --port 8000     # run from inside backend/ so imports resolve
cd frontend; npm install; npm run dev                 # http://localhost:5173
npm run build                                         # tsc && vite build
```

OpenAPI docs: http://127.0.0.1:8000/docs. Full endpoint reference: [docs/api-specification-and-runtime-guide.md](docs/api-specification-and-runtime-guide.md).

---

## Main API surface

| Endpoint | Purpose |
| :--- | :--- |
| `POST /api/v1/analyze` | Full orchestrator run with optional `scenario_shock` |
| `POST /api/v1/chat/stream`, `POST /api/v1/chat` | SSE and sync chat (direct sector or orchestrator route); `done` event includes `a2a`, `consensus`, `model_card` |
| `POST /api/v1/simulate`, `GET /api/v1/kg/path`, `GET /api/v1/kg/impacts` | Scenario engine and KG queries |
| `GET /api/v1/dashboard/overview` | Cross-sector telemetry with citations |
| `/api/v1/research/*` | `kg/graph`, `edges/audit`, `trajectory`, `compare`, `anomalies`, `mpc/simulate` |
| `/api/v1/brief/*` | `today`, `run`, `history` |
| `GET /a2a/registry` | Agent Cards and declared dependencies |
| `/<sector>-sector/*` | Mounted sector sub-apps |

---

## Engineering rules

1. Every economic claim cites source agent, MCP tool or official source with table, and value plus observation period.
2. DuckDB SQL is parameterized (`?`); dynamic identifiers only from module constants.
3. I/O paths are `async def`; external calls use Tenacity exponential retries.
4. Pydantic v2, `from __future__ import annotations`, modules under 400 lines, no emojis, no commented-out code.
5. Frontend: strict TypeScript, Tailwind classes, complete hook dependency arrays, `AbortController` for fetches.

Known deviations are tracked in [docs/status-and-roadmap.md](docs/status-and-roadmap.md).

---

## License
MIT. Developed for research and institutional macroeconomic intelligence on the Indian economy.
