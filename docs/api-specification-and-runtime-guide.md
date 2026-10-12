# Macrograph-AI: Technical API Specification & Runtime Guide

This technical manual details the setup instructions, system architecture, runtime procedures, and comprehensive API documentation for the **Macrograph-AI** Indian Macroeconomic Intelligence Platform.

---

## 1. System Architecture Overview

Macrograph-AI decomposes the Indian macroeconomy into **10 specialized sector agents** operating across two decoupled communication protocols:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 18 + Vite)                    │
│   Landing Page  •  Google Auth  •  Visual Dashboard  •  Streaming Chat  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / SSE Stream
┌────────────────────────────────────▼────────────────────────────────────┐
│                    API GATEWAY (FastAPI / Uvicorn :8000)                │
├─────────────────────────────────────────────────────────────────────────┤
│ • LangGraph Multi-Agent Orchestrator (A2A Dispatch & Synthesis)         │
│ • NetworkX Causal Graph + graph-attenuation scenario engine             │
│ • Server-Sent Events (SSE) Streaming Channel (`/api/v1/chat/stream`)    │
│ • Dashboard aggregator, Causal Lab (`/api/v1/research/*`), Daily Brief  │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
     A2A Protocol   │                  FastMCP Layer  │
 (Reasoning Layer)  │               (Data Retrieval)  │
                    ▼                                 ▼
┌─────────────────────────────────────┐   ┌───────────────────────────────┐
│     A2A Multi-Agent Collaboration   │   │     FastMCP Tool Servers      │
│ • Orchestrator Node                 │   │ • MoSPI e-Sankhyiki FastMCP   │
│ • 10 sector agents (cards in /a2a/registry) │   │   (https://mcp.mospi.gov.in/) │
│ • Prices & Inflation Sector Agent   │   │ • RBI DBIE Live Pipelines     │
│ • Real Sector Agent                 │   │ • Yahoo Finance MCP / yfinance│
│ • Capital Markets Sector Agent      │   │ • Dedicated DuckDB Stores     │
│ • Labour & Employment Agent         │   │ • Curated snapshots (cached)  │
└─────────────────────────────────────┘   └───────────────────────────────┘
```

### Architectural Guarantees
1. **A2A Protocol vs FastMCP:** A2A handles agent-to-agent reasoning, subtask delegation, and transmission hypotheses. FastMCP handles agent-to-data retrieval. Agents never fetch raw data from each other.
2. **Single Source of Truth:** Each indicator has exactly one owner agent (e.g., Prices Sector owns CPI and Food Inflation; Finance Sector owns bank credit and Gross NPAs; Capital Markets owns NIFTY/SENSEX; Real Sector owns GDP/GVA).
3. **Multi-Source Verified Provenance:** Data is pulled from authoritative specialized endpoints:
   - **Prices & Inflation:** Official MoSPI FastMCP server (`https://mcp.mospi.gov.in/`) for CPI & WPI.
   - **Banking & Lending Rates:** RBI DBIE Tables (`r539`, `r330`, `r531`, `r689`) for WALR, MCLR, NPAs, and Credit Growth.
   - **Capital Markets:** Yahoo Finance / NSE India for real-time equities, volatility (India VIX), and currency exchange rates (USD/INR).
4. **No Source, No Answer:** Zero hallucination policy. Every output metric carries a strict attribution chain with source agent, official table/endpoint reference, period, and freshness flag (`live` or `cached`).

---

## 2. Prerequisites & Environment Setup

### System Requirements
- **Python:** 3.12+
- **Node.js:** v18.0.0+ (Tested on v22.12.0)
- **Package Managers:** `pip` (or `uv`) and `npm`

### Environment Configuration

#### Backend Configuration (`backend/.env`)
The backend loads configuration from `backend/.env` (template: `backend/.env.example`). With no key the platform uses deterministic offline synthesis:
```bash
# Groq LLM API Configuration
# Six-key Groq convention (each key is shared by a sector pair); ORCH_KEY drives the orchestrator.
AGR_REAL_KEY=gsk_...
FIN_FIS_KEY=gsk_...
CAP_MON_KEY=gsk_...
ORCH_KEY=gsk_...
PRIC_LAB_KEY=gsk_...
SERV_EXT_KEY=gsk_...
# Optional single key fallback: GROQ_API_KEY
# Optional web search: TVLY_KEY_1, TVLY_KEY_2, TVLY_KEY_3

# Model Selection
MODEL_PROVIDER=groq
FAST_MODEL=openai/gpt-oss-20b
REASONING_MODEL=openai/gpt-oss-120b

# Optional: A2A guards (A2A_MAX_DEPTH, A2A_MAX_HOPS, A2A_REQUEST_TIMEOUT, A2A_API_KEY, A2A_ALLOW_ANONYMOUS_REQUESTS)
# Optional: daily brief scheduler at 08:15 Asia/Kolkata
BRIEF_CRON_ENABLED=false

# Optional: Persistent Knowledge Graph mirror (empty NEO4J_URI disables; install with uv pip install -e ".[neo4j]")
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

#### Frontend Configuration (`frontend/.env`)
For real Google Authentication (Google Identity Services via `@react-oauth/google`), set:
```bash
# Google OAuth 2.0 Web Client ID (from Google Cloud Console)
VITE_GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
```
*Note: You can also paste your Google Client ID directly into the sign-in modal in the UI.*

---

## 3. How to Run Locally

### Step 1: Start the FastAPI Backend Gateway

```powershell
# Navigate to the backend directory
cd backend

# Run Uvicorn server on port 8000
python -m uvicorn main:app --port 8000 --host 127.0.0.1 --reload
```

- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Step 2: Start the React Frontend Application

```powershell
# In a new terminal, navigate to the frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start Vite dev server on port 5173
npm run dev
```

- **Frontend Application:** [http://localhost:5173](http://localhost:5173)

The Vite configuration proxies `/api`, the sector mounts and `/a2a` directly to `http://127.0.0.1:8000`.

---

## 4. Complete API Reference

### System & Health Endpoints

#### `GET /health`
Returns the operational status of the platform and Knowledge Graph dimensions.

- **URL:** `http://127.0.0.1:8000/health`
- **Method:** `GET`
- **Example Response:**
```json
{
  "status": "healthy",
  "platform": "Macrograph AI",
  "version": "1.0.0",
  "sectors_active": 10,
  "knowledge_graph_nodes": 20,
  "knowledge_graph_edges": 12,
  "neo4j_enabled": false
}
```

---

### Dashboard & Analytics Endpoints

#### `GET /api/v1/dashboard/overview`
Returns real ingested data from the Finance Sector's DuckDB store (`finance_sector.duckdb`) alongside staged preview indicators for upcoming sectors.

- **URL:** `http://127.0.0.1:8000/api/v1/dashboard/overview`
- **Method:** `GET`
- **Example Response:**
```json
{
  "status": "success",
  "finance_sector": {
    "credit_growth": {
      "period": "2024-09",
      "gross_credit_cr": 21928365.0,
      "non_food_credit_cr": 21796315.0,
      "non_food_credit_yoy_pct": 13.0,
      "sectoral": {
        "agriculture_cr": 2145890.0,
        "industry_msme_cr": 1980320.0,
        "industry_large_cr": 1809130.0,
        "services_cr": 4567890.0,
        "personal_loans_cr": 5678920.0,
        "personal_housing_cr": 2894500.0,
        "personal_vehicle_cr": 654300.0
      },
      "citation": {
        "source_agent": "finance_sector",
        "source_authority": "Reserve Bank of India (RBI)",
        "table_reference": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
        "observation_period": "2024-09",
        "freshness": "cached"
      },
      "is_real_data": true
    },
    "asset_quality": {
      "period": "2024-06",
      "bank_group": "ALL_SCB",
      "gross_npa_pct": 2.8,
      "net_npa_pct": 0.6,
      "gross_npa_cr": 384000.0,
      "net_npa_cr": 82000.0,
      "provision_coverage_ratio_pct": 76.4,
      "crar_pct": 16.8,
      "cet1_pct": 13.9,
      "citation": {
        "table_reference": "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou",
        "observation_period": "2024-06"
      },
      "is_real_data": true
    },
    "lending_rates": {
      "period": "2024-09",
      "walr_fresh_pct": 9.38,
      "walr_outstanding_pct": 9.87,
      "mclr_1yr_median_pct": 8.85,
      "wadtdr_fresh_pct": 6.51,
      "wadtdr_outstanding_pct": 6.92,
      "is_real_data": true
    },
    "deposits_cd_ratio": {
      "period": "2024-09",
      "aggregate_deposits_cr": 21543890.0,
      "deposits_yoy_pct": 11.8,
      "casa_ratio_pct": 38.6,
      "bank_credit_cr": 16890450.0,
      "cd_ratio_pct": 78.4,
      "is_real_data": true
    }
  },
  "other_sectors_preview": [
    {
      "sector": "Real Sector (GDP/GVA)",
      "indicator": "Real GDP Growth",
      "value": "6.7%",
      "source": "MoSPI National Accounts",
      "is_mock": true
    }
  ]
}
```

---

### Interactive Multi-Agent Chat Endpoints

#### `POST /api/v1/chat/stream` (Server-Sent Events)
Streams real-time step execution updates (tools invoked, agent routed) and fluid token generation.

- **URL:** `http://127.0.0.1:8000/api/v1/chat/stream`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
```json
{
  "message": "Analyze current SCB Gross NPA ratios and non-food bank credit growth.",
  "agent": "finance_sector"
}
```
*Note: Set `"agent": "orchestrator"` for multi-agent routing or `"agent": "finance_sector"` for direct banking domain mode.*

- **SSE Stream Events Output Format:**
```
data: {"type": "step", "step": 1, "agent": "finance_sector", "title": "Targeting Finance Sector Agent", "detail": "Direct domain investigation of Indian Scheduled Commercial Banks."}

data: {"type": "step", "step": 2, "agent": "finance_sector", "tool": "get_bank_credit_growth", "title": "Invoking FastMCP Tool: get_bank_credit_growth", "detail": "Querying non-food credit from RBI DBIE (Table r539)..."}

data: {"type": "token", "text": "**Indian Banking Sector Stability** "}
data: {"type": "token", "text": "Gross NPA stands at 2.8%... "}

data: {"type": "done", "agent_routed": "Finance & Banking Sector Agent", "full_report": "...", "citations": [...]}
```

#### `POST /api/v1/chat` (Synchronous Fallback)
Synchronous endpoint returning complete analytical reports without streaming.

- **URL:** `http://127.0.0.1:8000/api/v1/chat`
- **Method:** `POST`
- **Request Body:**
```json
{
  "message": "What is the current policy transmission lag?",
  "agent": "orchestrator"
}
```

---

### Orchestrator & Econometrics Endpoints

#### `POST /api/v1/analyze`
Executes the full LangGraph multi-agent research workflow (Decompose → Parallel A2A Dispatch → Causal KG Traversal → Report Synthesis).

- **URL:** `http://127.0.0.1:8000/api/v1/analyze`
- **Method:** `POST`
- **Request Body:**
```json
{
  "query": "How will a rise in crude oil prices transmit into Indian bank credit and inflation?",
  "scenario_shock": {
    "variable": "in.macro.prices.brent_crude",
    "magnitude": 20.0,
    "name": "Crude Surge +20%"
  }
}
```
- **Example Response:**
```json
{
  "query": "How will a rise in crude oil prices transmit into Indian bank credit and inflation?",
  "status": "completed",
  "target_sectors": ["prices_inflation", "monetary_banking"],
  "collected_observations": [...],
  "causal_paths": [...],
  "scenario_result": {...},
  "mermaid_diagram": "graph TD\n  in.macro.prices.brent_crude --> in.macro.prices.cpi_headline",
  "report_markdown": "# Indian Macroeconomic Intelligence Report\n...",
  "confidence_score": 0.94
}
```

#### `POST /api/v1/simulate`
Runs a scenario shock through the knowledge graph using the heuristic graph-attenuation engine (per-hop `0.55 x confidence`, scale 0.15, +/-25% band; not a VAR/IRF and not a statistical interval). Baselines are fixed defaults unless supplied.

- **URL:** `http://127.0.0.1:8000/api/v1/simulate`
- **Method:** `POST`
- **Request Body:**
```json
{
  "scenario_name": "Repo Rate Hike Simulation",
  "shock_variable": "in.macro.monetary.repo_rate",
  "shock_magnitude": 0.5,
  "horizon_periods": 4
}
```

---

### Causal Knowledge Graph Endpoints

#### `GET /api/v1/kg/path`
Finds the shortest transmission path and cumulative lag between two canonical indicators.

- **URL:** `http://127.0.0.1:8000/api/v1/kg/path?source_id=in.macro.monetary.repo_rate&target_id=in.macro.monetary.bank_credit_growth`
- **Method:** `GET`
- **Example Response:**
```json
{
  "source": "in.macro.monetary.repo_rate",
  "target": "in.macro.monetary.bank_credit_growth",
  "hops": 1,
  "total_lag_months": 3,
  "relationships": [
    {
      "source_id": "in.macro.monetary.repo_rate",
      "target_id": "in.macro.monetary.bank_credit_growth",
      "relationship_type": "GRANGER",
      "transmission_lag_months": 3,
      "elasticity_coefficient": -0.32
    }
  ]
}
```

#### `GET /api/v1/kg/impacts`
Evaluates all downstream reachable indicators affected by a shock to a source variable.

- **URL:** `http://127.0.0.1:8000/api/v1/kg/impacts?shock_id=in.macro.monetary.repo_rate`
- **Method:** `GET`

---

### Causal Lab (Research) Endpoints

All responses carry `labels` (`SIM`, `CACHED`, `heuristic`) so the UI can distinguish simulated, cached and measured values. Implemented in `backend/api/research.py` over `backend/core/research`.

| Endpoint | Body / query | Returns |
| :--- | :--- | :--- |
| `GET /api/v1/research/kg/graph` | none | Nodes and typed edges (relation id, lag, sign, confidence, seeded p-value, mechanism, review note) |
| `GET /api/v1/research/edges/audit` | none | Per-edge evidence class: `SEEDED` (typed into the ontology) or `EMPIRICAL` (Granger test on live series, needs at least 10 overlapping months) with `status` `UNTESTABLE_NO_DATA` / `UNTESTABLE_N` / `EMPIRICAL`; cached 300 s |
| `POST /api/v1/research/trajectory` | `shock_variable`, `shock_magnitude`, `horizon_months` (1-60), `shape` (`step`/`decay`), `half_life_months` | Monthly series per downstream node, edge list with evidence class and notes (Shockwave) |
| `POST /api/v1/research/compare` | `shock_variable`, `shock_magnitude` | Base vs shocked world, per-hop log-attenuation shares, weakest link, sign flips (Twin) |
| `GET /api/v1/research/anomalies?inject=<id>:<z>` | optional SIM injection | Rolling-window (12) z-scores, threshold 2.0, each anomaly classed `PROPAGATING`, `ISOLATED` or `UNLINKED` against graph neighbours (Radar) |
| `POST /api/v1/research/mpc/simulate` | `use_llm` (default true) | Six archetype seats with deterministic rule votes, optional LLM votes citing an evidence indicator, tally, dissent, `rule_baseline` and agreement flag. Always labelled `SIMULATED` |

### Daily Brief Endpoints

| Endpoint | Purpose |
| :--- | :--- |
| `GET /api/v1/brief/today` | Today's brief or the latest stored one, with `is_stale` and `served_from_cache` |
| `POST /api/v1/brief/run` | Body `{"force": bool}`. Runs telemetry, anomaly scan, cached news (Tavily capped at 4 queries) and one LLM call, with a deterministic fallback. `409` if a run is in progress; debounced unless forced |
| `GET /api/v1/brief/history?limit=7` | Stored briefs (DuckDB) |

These endpoints trigger paid LLM or search calls and are unauthenticated; do not expose them publicly without rate limiting (see `docs/status-and-roadmap.md`).

### Chat `done` event additions
The orchestrator route appends to the final SSE `done` payload: `a2a` (conversation id, routed agents, routing method, errors, sources, flat trace), `consensus` (per-agent status, evidence cover, KG cover, heuristic quality score), `model_card` (evidence counts, KG relations with evidence class, scenario formula and constants, heuristic trust score, inflation regime note) and `live_baseline_ids`. `consensus` and `model_card` are built best-effort and omitted on error.

---

### A2A Protocol Registry Endpoint

#### `GET /a2a/registry`
Returns discoverable Agent Cards, input/output schemas, and skills for all registered domain agents.

- **URL:** `http://127.0.0.1:8000/a2a/registry`
- **Method:** `GET`

---

### Finance Sector Sub-Application Endpoints (`/finance-sector`)

Mounted directly at `/finance-sector` by the central gateway:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/finance-sector/health` | `GET` | Health check for finance sector sub-app |
| `/finance-sector/metadata` | `GET` | Sector ownership, MCP tool registry & A2A interfaces |
| `/finance-sector/credit-growth` | `GET` | Gross non-food credit and sectoral breakdown (lookback_months: 1-60) |
| `/finance-sector/asset-quality` | `GET` | Gross NPA, Net NPA, and CRAR by bank group (ALL_SCB, PSB, PVT) |
| `/finance-sector/lending-rates` | `GET` | WALR (fresh/outstanding), 1-yr MCLR, WADTDR, lending spread |
| `/finance-sector/deposits-cd-ratio` | `GET` | Aggregate deposits YoY, CASA ratio, Credit-to-Deposit ratio |

Example Query:
```bash
curl -X GET "http://127.0.0.1:8000/finance-sector/credit-growth?lookback_months=12"
```

---

## 5. Testing & Verification

Run from the repository root (`pyproject.toml` sets `pythonpath = ["backend", "backend/tests"]` and `asyncio_mode = "auto"`):

```powershell
pytest                                   # default testpaths: backend/tests, finance_sector/tests, agriculture test file
pytest backend/fiscal_sector/tests backend/monetary_sector/tests backend/external_sector/tests `
       backend/services_sector/tests backend/labour_sector/tests backend/capital_market_sector/tests `
       backend/real_sector/tests         # sector suites not in the default testpaths

cd frontend; npm run build               # tsc && vite build (the only frontend check)
```

Importing statsmodels is slow on a cold start (about 30 s); tests are slow, not hung.
