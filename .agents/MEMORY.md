# Macrograph-AI: Agent Memory & Context Snapshot

Rapid orientation guide, refreshed 2026-10-12. Read it first, then `docs/high-level-overview.md`, `docs/status-and-roadmap.md` and `.agents/AGENTS.md`.

---

## What This Platform Does

Multi-agent Indian macroeconomic intelligence platform. **10 sector agents** reason with each other over a native **A2A** layer (agent-to-agent) and fetch data only through per-sector **FastMCP** servers (agent-to-data). A four-node LangGraph orchestrator (`decompose` -> `parallel_a2a_execute` -> `kg_causal_enrichment` -> `synthesis`) produces cited reports grounded in a 20-indicator, 12-edge causal knowledge graph.

## Two Inviolable Laws
1. **A2A = reasoning between agents.** Never data fetching. Sector packages never import each other.
2. **MCP = data fetching.** Never reasoning. One owner agent per indicator; peers get it via A2A along declared edges only (`core/protocols/a2a/dependencies.py`, 7 edges).

## Sector Agents (all 10 exist)

| Agent | Path | Maturity note |
| :--- | :--- | :--- |
| Real | `backend/real_sector/` | GDP/GFCF/IIP, national accounts parser; fairly complete |
| Agriculture | `backend/agriculture_sector/` | Needs `.mcp-sources` (weather MCP) and `agriculture` extra; agent.py over 400 lines |
| Prices | `backend/prices_sector/` | Most complete: A2A handlers, research, market proxies; claim verification was removed from it |
| Monetary | `backend/monetary_sector/` | A2A handlers, DBIE client |
| Finance | `backend/finance_sector/` | A2A handlers, peers gathered |
| Capital Markets | `backend/capital_market_sector/` | yfinance based |
| Fiscal | `backend/fiscal_sector/` | Seeded CGA/Budget baselines tagged `cached`; peers gathered |
| External | `backend/external_sector/` | RBI/IMF/Tavily |
| Labour | `backend/labour_sector/` | `parsers.py` 866 lines, `client.py` 796 lines (over limit) |
| Services | `backend/services_sector/` | MoSPI/PMI |

## Key Files

| File | Purpose |
| :--- | :--- |
| `backend/main.py` | Gateway. Imports sectors, mounts sub-apps, DuckDB init at import time (sub-app lifespans do not run), includes `api.research` and `api.brief` in try/except |
| `backend/core/config.py` | `PlatformSettings` (six-key Groq convention, A2A guards, NEO4J, CORS) |
| `backend/core/orchestrator/graph.py` | `macro_orchestrator_graph`; `a2a_dispatch.py`, `registry_bootstrap.py`, `canonical_ids.py`, `llm_client.py` (offline fallback sentinel `_unavailable_notice()`) |
| `backend/core/protocols/a2a/` | Native A2A: messages, server guards, client, router, dependencies, peers, provenance, trace |
| `backend/core/knowledge_graph/` | `ontology.py` (indicators, edges), `networkx_engine.py`, `neo4j_store.py` (optional) |
| `backend/core/econometrics/causal_engine.py` | Heuristic scenario engine (0.55 x confidence per hop, scale 0.15). Not a VAR |
| `backend/core/research/` | Trajectory, attribution (Twin), anomaly radar, MPC, edge audit, consensus, model card |
| `backend/core/briefing/` | Daily brief job and DuckDB store |
| `backend/core/verification/` | Typed claim verification library; **not wired anywhere** |
| `backend/api/` | `chat.py` (SSE), `dashboard*.py`, `research.py`, `brief.py` |
| `docs/status-and-roadmap.md` | Component maturity and review findings |
| `docs/publication-plan.md` | Novelty assessment and research plan |

## Tech Stack
Python 3.12 (`uv`), FastAPI, FastMCP, LangGraph, DuckDB, SQLite (claim audits), NetworkX (+ optional Neo4j), statsmodels, Pydantic v2, Tenacity. LLM: Groq via `langchain-groq`/`groq`, defaults `openai/gpt-oss-20b` and `openai/gpt-oss-120b`, offline fallback. Frontend: React 18, TypeScript, Vite, Tailwind, GSAP, Mermaid.

**Not implemented despite older docs:** PydanticAI, Qdrant/RAG, SDK-based A2A (`a2a-sdk` is declared but unused).

## Known Issues and Gotchas
- `pytest` default testpaths cover only `backend/tests`, `finance_sector/tests`, and the agriculture test file; run the other sector `tests/` dirs explicitly.
- Run uvicorn from inside `backend/` (`uvicorn main:app`); `backend.main:app` breaks imports.
- statsmodels import takes about 30 s cold.
- `core/research/__init__.py` mirrors `ATTENUATION`, `SCALE`, `BAND` from the causal engine; keep in sync.
- Edge p-values/confidences in the ontology are seeded priors; `EDGE_NOTES` flags the `trade_balance -> usd_inr` sign as wrong.
- Gateway silently skips optional sector mounts on `ImportError`/`AttributeError` and logs only a warning for failed DB init.
- Tracked binaries that should not be: `backend/data/claim_audits.sqlite3`, `frontend/vite.config.ts.timestamp-*.mjs`.
- Research and brief endpoints are unauthenticated and can trigger paid LLM/Tavily calls.
- Over the 400-line limit (non-test): `labour_sector/parsers.py`, `labour_sector/client.py`, `real_sector/client.py`, `agriculture_sector/agent.py`, `agriculture_sector/client.py`, `services_sector/agent.py`, `monetary_sector/client.py`, `capital_market_sector/client.py`, `api/dbie_sector_catalog.py`.
- Frontend still has `any` usages and inline `style={{}}` (violations of the stated rules).

## Quick Commands
```powershell
cd backend; uvicorn main:app --reload --port 8000
pytest                                  # plus the sector test dirs listed in CLAUDE.md
cd frontend; npm run dev; npm run build
curl http://localhost:8000/health
curl http://localhost:8000/a2a/registry
```
