# Macrograph-AI — Agent Memory & Context Snapshot

This file is a rapid orientation guide. Read it first. Then read `docs/high-level-overview.md` for full architecture detail and `.agents/AGENTS.md` for code standards.

---

## What This Platform Does

Macrograph-AI is a **multi-agent Indian macroeconomic intelligence platform**. It decomposes the Indian economy into **10 specialized sector agents** that collaborate via the **A2A protocol** (agent-to-agent reasoning) and retrieve real macroeconomic data via **FastMCP servers** (agent-to-data). The Orchestrator routes, coordinates, and synthesizes final **strictly cited** research reports.

---

## The Two Inviolable Architecture Laws

1. **A2A = Reasoning between agents.** Never data fetching.
2. **MCP = Data fetching from external sources.** Never reasoning.

Agents exchange analysis, causal conclusions, and validated findings through A2A. They fetch raw data (CPI, repo rate, trade data, etc.) exclusively through MCP tools. These layers must never be conflated.

---

## The 10 Sector Agents (Modules)

| Agent | Module Path | Owns These Indicators |
| :--- | :--- | :--- |
| **Real Sector** | `backend/real_sector/` | GDP, GVA, National Accounts |
| **Agriculture** | `backend/agriculture_sector/` | Crop production, MSP, Mandi prices, Rainfall |
| **Prices** | `backend/prices_sector/` | CPI, WPI, Core/Food/Fuel/Housing inflation |
| **Monetary** | `backend/monetary_sector/` | Repo rate, SDF, M1/M2/M3, RBI policy stance |
| **Finance** | `backend/finance_sector/` | NPA, Credit growth, Deposit rates, NBFC |
| **Capital Markets** | `backend/capital_market_sector/` | NIFTY, SENSEX, FII/DII, G-Sec yields |
| **Fiscal** | `backend/fiscal_sector/` | Fiscal deficit, GST, Capex, Govt debt |
| **External** | `backend/external_sector/` | Trade balance, Forex reserves, BoP |
| **Labour** | `backend/labour_sector/` | Unemployment, LFPR, EPFO, Wages |
| **Services** | *(to be added: `backend/services_sector/`)* | IT/ITeS, PMI Services, Services GVA |

---

## Key Files to Know

| File | Purpose |
| :--- | :--- |
| `backend/main.py` | Unified FastAPI gateway. Mounts all sector sub-apps and MCP servers. |
| `backend/core/config.py` | `PlatformSettings` — all env vars loaded from `.env` via Pydantic BaseSettings. |
| `backend/core/orchestrator/graph.py` | LangGraph `macro_orchestrator_graph` — the full agent execution graph. |
| `backend/core/orchestrator/state.py` | `OrchestratorState` TypedDict — shared state across all LangGraph nodes. |
| `backend/core/protocols/a2a/` | A2A SDK: agent registry, Agent Cards, A2A request/response schemas. |
| `backend/core/knowledge_graph/networkx_engine.py` | `graph_engine` — in-memory causal indicator transmission graph. |
| `backend/core/econometrics/causal_engine.py` | `causal_engine` — impulse response simulation (VAR/IRF). |
| `backend/<sector>/mcp_server.py` | FastMCP server per sector (registered as `<sector>_mcp` in `main.py`). |
| `backend/tests/` | `pytest` test suite — 6 test modules covering A2A, orchestrator, knowledge graph, ingestion, MCP, and data integrity. |
| `docs/high-level-overview.md` | Full architecture doc with diagrams, sector table, causal example. |
| `.agents/AGENTS.md` | Code standards, directory contract, workflow, and setup instructions. |
| `.agents/rules/project-rules.md` | Granular per-category engineering rules (enforcement by code-reviewer agent). |

---

## Tech Stack at a Glance

- **Backend:** Python 3.12, FastAPI, FastMCP, LangGraph, A2A SDK, DuckDB, Pydantic v2
- **LLM:** Groq — `llama-3.1-8b-instant` (fast), `llama-3.3-70b-versatile` (reasoning)
- **Retry/Resilience:** `tenacity` — all external API calls use exponential backoff
- **Knowledge Graph:** NetworkX (in-memory causal graph), Neo4j (optional persistent store)
- **Vector DB (RAG):** Qdrant — stores RBI MPC minutes, Budget speeches, Economic Surveys
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Testing:** pytest, with plans to add `httpx` transport mocking for external API tests

---

## Active Sector Modules (what currently exists in backend/)

```
agriculture_sector/     ← active
capital_market_sector/  ← active
core/                   ← shared infrastructure (always active)
external_sector/        ← active
finance_sector/         ← active
labour_sector/          ← active
monetary_sector/        ← active
prices_sector/          ← active
real_sector/            ← active
tests/                  ← pytest test suite
main.py                 ← FastAPI gateway
```

**Missing / To Be Built:**
- `services_sector/` — Not yet implemented. Should cover IT/ITeS, PMI Services, Services GVA.
- `fiscal_sector/` — Referenced in `core/config.py` URL list but not yet present as a module.
- Qdrant integration — RAG layer is designed but not yet wired.
- Frontend UI — Exists (`frontend/src/`) but likely at early/demo stage.

---

## Known Issues & Gotchas

- `backend/.env` has `GROQ_API_KEY1` (numbered) but `core/config.py` reads `GROQ_API_KEY` (unnumbered). Ensure `.env` key names match `PlatformSettings` field names exactly.
- `CORS allow_origins=["*"]` is in `main.py` — acceptable for dev, must be restricted for production.
- `core/config.py` references `DATA_DIR = BACKEND_ROOT / "real_sector" / "data"` — this is real_sector-specific and likely needs to be generalized as more sectors are added.
- No `fiscal_sector` sub-app is mounted in `main.py` despite the fiscal sector URL being configured in `PlatformSettings`.

---

## Quick Command Reference

```powershell
# Start backend
uvicorn backend.main:app --reload --port 8000

# Run all tests
pytest backend/tests/ -v

# Start frontend dev server
cd frontend && npm run dev

# Check API health
curl http://localhost:8000/health

# View registered A2A agents
curl http://localhost:8000/a2a/registry
```
