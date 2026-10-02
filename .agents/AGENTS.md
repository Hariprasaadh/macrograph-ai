# Macrograph-AI — Agent Workspace Rules

This is the **Macrograph-AI** codebase: a multi-agent Indian macroeconomic intelligence platform. Read `docs/high-level-overview.md` before implementing anything. This file defines the behavioral contract for all AI agents working in this repository.

---

## Project Identity

- **Platform:** Multi-Agent Indian Macroeconomic Intelligence System
- **Backend:** Python 3.12, FastAPI, FastMCP, LangGraph, A2A SDK, DuckDB, Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **LLM Provider:** Groq (`llama-3.1-8b-instant` for fast ops, `llama-3.3-70b-versatile` for reasoning)
- **Analytical Stack:** DuckDB, Pandas, NumPy, Statsmodels, NetworkX
- **Vector DB:** Qdrant (RAG layer for policy documents)

---

## Non-Negotiable Architecture Rules

### A2A vs MCP — Never Conflate
- **A2A Protocol** = Agent ↔ Agent reasoning and collaboration layer. Used for passing analysis, findings, and causal conclusions between sector agents.
- **MCP (FastMCP)** = Agent ↔ Data retrieval layer. Used for fetching live data from external APIs, DuckDB, and Qdrant.
- **An agent must never fetch data from another agent. It fetches from MCP tools. It reasons with peer agents via A2A.**

### Single Source of Truth Per Indicator
Every macroeconomic indicator has exactly **one owner agent**. If the Prices Agent computes CPI, the Monetary Agent must accept that value via A2A — it must **never** recompute or re-fetch the same CPI data independently. Violations create divergent sources of truth and are a critical defect.

| Indicator | Owner Agent |
| :--- | :--- |
| CPI, WPI, Core/Food inflation | `prices_sector` |
| Repo rate, M1/M2/M3, Liquidity | `monetary_sector` |
| Fiscal deficit, GST revenue | `fiscal_sector` |
| Forex reserves, BoP, Trade | `external_sector` |
| Crop production, MSP, Mandi prices | `agriculture_sector` |
| GDP/GVA, National Accounts | `real_sector` |
| Unemployment, LFPR, EPFO | `labour_sector` |
| NIFTY, FII/DII flows, G-Sec yields | `capital_market_sector` |
| NPA, Credit growth, Bank rates | `finance_sector` |

### No Source, No Answer — Strict Citation & Anti-Hallucination Policy (NON-NEGOTIABLE)

**No Source, No Answer:** Do not generate any financial metric, percentage, rate, or trend without explicitly stating its source.

- **Zero Hallucination / No Hardcoding:** Never hallucinate, estimate, or hardcode random/mock numbers as factual data. If an official data point cannot be retrieved from an authorized source (e.g. RBI DBIE, MOSPI) or verified canonical store, the agent **must** explicitly return a structured unavailable/missing status. It must **never** invent plausible-sounding values.
- Every agent response, orchestrator synthesis, and API output that makes an economic claim **must** include:
  1. The **source agent** that owns the data
  2. The **MCP tool or official external source** used to retrieve it (including table/document reference)
  3. The **specific data point, value, and observation period** cited

No economic claim may be output without this verified attribution chain.

---

## Code Standards

### Python (Backend)

- **Python 3.12** minimum. Use `from __future__ import annotations` at the top of every module.
- **Pydantic v2** for all data models. Use `model_validate()` not `parse_obj()`. Use strict type annotations.
- **FastAPI** for all HTTP endpoints. All route handlers must have response model annotations and docstrings.
- **FastMCP** for all MCP servers. Each sector must expose its own MCP server in `<sector>/mcp_server.py`.
- **LangGraph** for orchestration. State transitions must be typed with `OrchestratorState`.
- **DuckDB** queries must always be parameterized. Never build SQL with f-strings or string concatenation.
- **Async first:** All FastAPI endpoints and LangGraph nodes that perform I/O must be `async def`. Never use blocking `requests.get()`, `time.sleep()`, or synchronous file I/O inside async contexts. Use `httpx.AsyncClient` for HTTP, `asyncio.sleep()` for delays.
- **Error handling:** Never use bare `except: pass`. Catch specific exceptions. Log with context. Propagate or convert to structured HTTP errors.
- **Tenacity** for retries on all external API calls (Groq LLM, government data APIs). Configure `wait_exponential` and `stop_after_attempt`.
- **Environment variables:** All secrets and configuration must come from `.env` via `PlatformSettings` in `core/config.py`. No hardcoded credentials or API keys ever.
- **File size limit:** No Python module should exceed **400 lines**. Extract sub-modules when this limit is approached.

### TypeScript / React (Frontend)

- **TypeScript strict mode** is active. No use of `any` type in production code.
- **React 18** functional components only. No class components.
- **Hooks:** All `useEffect`, `useMemo`, `useCallback` must have complete dependency arrays. Use `eslint-plugin-react-hooks`.
- **No mutation:** Never mutate state directly. Use spread operators or immutable update patterns.
- **No inline styles.** Use Tailwind utility classes exclusively.
- **Network requests** must use `AbortController` to cancel on component unmount.

### Universal

- **DRY:** Identify existing utilities, schemas, and functions before creating new ones. Never duplicate business logic.
- **KISS:** Write the simplest code that solves the problem. Reject clever one-liners that obscure intent.
- **YAGNI:** Do not add parameters, abstractions, classes, or configuration that are not immediately needed.
- **Dead code:** Never commit commented-out code. Remove it. Git history preserves everything.
- **No emojis in code.** Comments, docstrings, and log messages must be professional and emoji-free.
- **Tests required:** All new business logic, sector MCP tools, and LangGraph nodes must ship with `pytest` tests in `backend/tests/`.

---

## Directory Structure

```
macrograph-ai/
├── backend/
│   ├── core/                          # Shared platform infrastructure
│   │   ├── config.py                  # PlatformSettings (Pydantic BaseSettings)
│   │   ├── orchestrator/              # LangGraph orchestration graph & state
│   │   ├── protocols/a2a/             # A2A SDK: agent registry, Agent Cards
│   │   ├── knowledge_graph/           # NetworkX causal graph engine
│   │   ├── econometrics/              # Causal engine, VAR, IRF models
│   │   ├── database/                  # DuckDB connection & query helpers
│   │   └── ingestion/                 # Canonical data ingestion pipelines
│   │
│   ├── <sector>_sector/               # Each of the 10 sector packages
│   │   ├── __init__.py
│   │   ├── mcp_server.py              # FastMCP server exposing sector tools
│   │   ├── agent.py                   # LangGraph sector agent node
│   │   ├── tools/                     # MCP tool implementations (data fetchers)
│   │   ├── models.py                  # Pydantic sector-specific data models
│   │   └── api/app.py                 # FastAPI sub-application mounted on gateway
│   │
│   ├── tests/                         # pytest test suite
│   └── main.py                        # Unified FastAPI gateway (mounts all sub-apps)
│
├── frontend/
│   └── src/                           # React + TypeScript application
│
├── docs/
│   └── high-level-overview.md         # Architecture reference — read before coding
│
└── .agents/
    ├── agents/                        # Specialized AI agents (planner, code-reviewer)
    └── rules/                         # Project-specific agent rules
```

---

## Sector Package Contract

Every sector package (`<sector>_sector/`) must implement this interface:

```python
# <sector>_sector/mcp_server.py
mcp_server = FastMCP("<Sector Name> MCP Server")

@mcp_server.tool()
async def get_<primary_indicator>(...) -> <SectorData>:
    """Fetch <indicator> from <Source>."""
    ...
```

```python
# <sector>_sector/agent.py
async def <sector>_agent_node(state: OrchestratorState) -> dict:
    """LangGraph node: fetches data via MCP, reasons, returns structured findings."""
    ...
```

No sector agent may directly import from another sector package. Cross-sector data exchange must flow through the A2A protocol.

---

## Workflow: How to Implement a New Feature

1. **Read `docs/high-level-overview.md`** and understand where the feature fits in the architecture.
2. **Use the `planner` agent** to generate a phased implementation plan before writing code.
3. **Implement** following code standards above. Parameterize all queries. Use `PlatformSettings` for config.
4. **Write tests** in `backend/tests/` covering the happy path, edge cases, and failure modes.
5. **Use the `code-reviewer` agent** to audit for DRY violations, dead code, error handling gaps, and security issues.
6. **Verify** with `pytest backend/tests/` — all tests must pass before committing.

---

## Environment Setup

```powershell
# Install Python dependencies
uv pip install -e .

# Configure environment
cp backend/.env.example backend/.env
# Fill in GROQ_API_KEY and other required values

# Run the backend
uvicorn backend.main:app --reload --port 8000

# Run the frontend
cd frontend && npm install && npm run dev

# Run all tests
pytest backend/tests/ -v
```

Required environment variables (see `backend/core/config.py`):
```
GROQ_API_KEY=          # Required — Groq LLM API key
MODEL_PROVIDER=groq    # LLM provider (groq | openai)
FAST_MODEL=llama-3.1-8b-instant
REASONING_MODEL=llama-3.3-70b-versatile
NEO4J_URI=             # Optional — persistent knowledge graph
NEO4J_PASSWORD=        # Optional
```
