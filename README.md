# Macrograph-AI: Multi-Agent Indian Macroeconomic Intelligence Platform

Macrograph-AI is an academically rigorous, multi-agent macroeconomic intelligence platform specialized in the Indian economy. It decomposes India's macroeconomic landscape into **10 specialized sector agents** that reason collaboratively over the **A2A protocol** (agent-to-agent reasoning), retrieve verified empirical observations via **FastMCP servers** (agent-to-data), validate claims against an embedded **DuckDB** analytical store and **Qdrant** policy vector layer, and produce strictly cited, transmission-aware economic intelligence.

---

## Core Architecture

### 1. A2A vs FastMCP — Never Conflate
- **A2A Protocol (Agent-to-Agent Reasoning):** Used strictly for peer coordination, subtask delegation, causal inquiries, and passing structured conclusions between sector agents.
- **FastMCP (Agent-to-Data Retrieval):** Used strictly for fetching empirical data from external statistical APIs, DuckDB tables, and Qdrant policy vectors.
- **Rule:** An agent must never fetch raw data from another agent. It fetches from its own FastMCP tools and communicates analytical findings with peers via A2A.

```
+--------------------+                     +--------------------+
| Prices Sector      | <====== A2A ======> | Monetary Sector    |
| (Reasoning Agent)  |                     | (Reasoning Agent)  |
+--------------------+                     +--------------------+
         |                                           |
    FastMCP Tool                               FastMCP Tool
         |                                           |
         v                                           v
  +--------------+                            +--------------+
  |  MOSPI DB    |                            |  RBI DBIE    |
  +--------------+                            +--------------+
```

### 2. Single Source of Truth Per Indicator
Every macroeconomic indicator is owned exclusively by **one sector agent**. No agent may independently recompute or re-fetch an indicator owned by another sector.

| Primary Indicator | Owner Agent | Subscribing Peer Agents via A2A |
| :--- | :--- | :--- |
| CPI, WPI, Food/Fuel/Core Inflation | `prices_sector` | Monetary, Agriculture, Fiscal |
| Repo Rate, SDF, MSF, M1/M2/M3 Liquidity | `monetary_sector` | Finance, Capital Markets, Fiscal |
| Crop Production, MSP, Mandi Prices | `agriculture_sector` | Prices, External |
| Fiscal Deficit, GST Revenue, Union Capex | `fiscal_sector` | Monetary, External |
| Bank Credit Growth, NPA Ratios, Deposit Rates | `finance_sector` | Monetary, Capital Markets |
| NIFTY 50, FII/DII Flows, G-Sec Yields | `capital_market_sector` | External, Monetary |
| Trade Balance, Forex Reserves, BoP, Remittances | `external_sector` | Monetary, Capital Markets |
| GDP, GVA, National Accounts, IIP | `real_sector` | Monetary, Fiscal, Capital Markets |
| PLFS Unemployment, LFPR, EPFO Additions | `labour_sector` | Real Sector, Fiscal |
| Services GVA, IT/ITeS Exports, PMI Services | `services_sector` | Real Sector, External |

### 3. Mandatory Attribution & Strict Citation Chain
No economic statement may be returned without an explicit attribution chain:
1. **Source Agent:** The domain authority agent owning the data point
2. **MCP Tool / Source Authority:** The specific FastMCP tool, government publication, or survey cited
3. **Specific Data Point:** The exact observation period, numerical value, and unit

---

## Architectural Flow

```
                           +-------------------------------------------------------------+
                           |                         USER QUERY                          |
                           +------------------------------+------------------------------+
                                                          |
                           +------------------------------v------------------------------+
                           |                         ORCHESTRATOR                        |
                           |  - Parses query, inspects sector AgentCards                 |
                           |  - Decomposes into domain tasks, builds A2A execution graph |
                           |  - Aggregates findings and generates strictly cited output  |
                           +------------------------------+------------------------------+
                                                          | A2A Protocol
               +----------------+-------------+-----------+-----------+----------------+
               |                |             |           |           |                |
               v                v             v           v           v                v
         +-----------+    +-----------+ +-----------+ +-----------+ +-----------+ +-----------+
         |  PRICES   |    | MONETARY  | |  FISCAL   | | EXTERNAL  | |  CAPITAL  | |  FINANCE  |
         |   AGENT   |    |   AGENT   | |   AGENT   | |   AGENT   | |  MARKETS  | |   AGENT   |
         +-----+-----+    +-----+-----+ +-----+-----+ +-----+-----+ +-----+-----+ +-----+-----+
               |                |             |           |           |                |
         +-----+-----+          |       +-----+-----+     |     +-----+-----+          |
         |   AGRI    |          |       |  LABOUR   |     |     | SERVICES  |          |
         |   AGENT   |          |       |   AGENT   |     |     |   AGENT   |          |
         +-----+-----+          |       +-----+-----+     |     +-----+-----+          |
               |                |             |           |           |                |
               +----------------+-------------+-----------+-----------+----------------+
                                              |
                                    FastMCP Tool Servers
               +----------------+-------------+-----------+-----------+----------------+
               v                v             v           v           v                v
          +----------+    +----------+  +----------+ +----------+ +----------+  +----------+
          |  MOSPI   |    | RBI DBIE |  | CGA/CBDT | | DGCI&S   | | NSE/SEBI |  |  Qdrant  |
          |  DuckDB  |    | Bulletins|  |  Budget  | |  Customs | | Financial|  | Vector RAG
          +----------+    +----------+  +----------+ +----------+ +----------+  +----------+
```

---

## The 10 Macroeconomic Domain Sectors

| # | Sector Agent | Package Directory | Core Analytical Scope | Primary FastMCP Sources |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **Real Sector** | `backend/real_sector/` | Real GDP Growth, Gross Value Added (GVA), IIP Manufacturing | MoSPI, MoSPI NAS |
| 2 | **Agriculture & Rural** | `backend/agriculture_sector/` | Foodgrain Production, Kharif/Rabi Sowing, MSP, Agmarknet Prices | Agmarknet, DAC&FW, IMD |
| 3 | **Prices & Inflation** | `backend/prices_sector/` | Headline CPI, Food/Fuel CPI, WPI Commodities, Brent Pass-Through | MoSPI, OEA, EIA |
| 4 | **Monetary & Liquidity** | `backend/monetary_sector/` | Policy Repo Rate, SDF/MSF Corridors, M3 Supply, RBI Stance | RBI DBIE, RBI Bulletins |
| 5 | **Finance & Banking** | `backend/finance_sector/` | Non-Food Bank Credit, Gross NPA Ratios, Liquidity Coverage | RBI DBIE, SEBI |
| 6 | **Capital Markets** | `backend/capital_market_sector/` | NIFTY 50, India VIX Regime, FII/DII Net Flows, G-Sec Yields | NSE/BSE APIs, SEBI, AMFI |
| 7 | **Fiscal & Public Finance** | `backend/fiscal_sector/` | Fiscal Deficit, Gross Tax Revenue, Union Capex, Debt-to-GDP | CGA, CBDT, CBIC, Budget |
| 8 | **External Sector** | `backend/external_sector/` | Forex Reserves, USD/INR Exchange Rate, Merchandise Trade Deficit | RBI BoP, DGCI&S |
| 9 | **Labour & Employment** | `backend/labour_sector/` | Monthly Net EPFO Payrolls, PLFS Unemployment, Rural Wages | PLFS, EPFO, ILO |
| 10 | **Services Sector** | `backend/services_sector/` | Services GVA, IT/BPO Exports, HSBC Services PMI Surveys | MoSPI, S&P Global PMI |

---

## 5-Tier Causal Classification Taxonomy

All cross-sector transmission hypotheses in the Knowledge Graph are evaluated through an explicit 5-tier causal ontology:

1. **`THEORY`**: Grounded in peer-reviewed academic literature and central banking doctrine.
2. **`STATISTICAL_ASSOCIATION`**: Contemporaneous empirical correlation (verified p < 0.05).
3. **`LAGGED_RELATIONSHIP`**: Cross-correlation exhibiting verified transmission lag (1 to 12 months).
4. **`GRANGER_PREDICTIVE`**: Directional predictive causality validated by bivariate F-tests on stationary series.
5. **`STRUCTURAL_CAUSAL_MODEL`**: Directed Acyclic Graph (DAG) counterfactual identification meeting do-calculus criteria.

---

## Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.12 | Modern type-hinting, performance, native async |
| **Orchestration Graph** | LangGraph | Stateful multi-agent graph execution with typed state |
| **Agent Reasoning & Typed IO** | PydanticAI | Type-safe tool use, `result_type` validation, `TestModel` CI |
| **Agent Collaboration Layer** | A2A SDK (`a2a-sdk >= 1.1.0`) | AgentCard discovery, JSON-RPC 2.0, SSE streaming |
| **Data Retrieval Tool Layer** | FastMCP (`fastmcp >= 3.4`) | Decorator-based MCP tool servers, typed parameter schemas |
| **Web Gateway** | FastAPI + Uvicorn | High-performance ASGI gateway mounting all sub-apps |
| **Analytical Database** | DuckDB (Embedded) | In-process columnar OLAP, SQL parameterization, zero latency |
| **Policy Document Vector DB** | Qdrant | Vector embeddings of RBI circulars, Union Budget speeches |
| **Knowledge Graph** | NetworkX & Neo4j | In-memory causal topology traversal and persistent graph |
| **LLM Provider** | Groq Cloud | `llama-3.3-70b-versatile` (reasoning), `llama-3.1-8b-instant` (routing) |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Modular financial intelligence dashboard |

---

## Project Structure

```text
macrograph-ai/
├── README.md                          # Project identity and architecture manual
├── docs/
│   └── high-level-overview.md         # Canonical platform architecture specifications
├── pyproject.toml                     # Python 3.12 dependencies and configuration
├── macro_store.duckdb                 # Embedded DuckDB canonical macroeconomic store
│
├── .agents/
│   ├── AGENTS.md                      # Agent workspace rules and behavioral contract
│   ├── agents/                        # Specialized subagents (planner.md, code-reviewer.md)
│   ├── rules/                         # Core engineering and architecture enforcement rules
│   └── skills/                        # Curated domain and tooling skills
│       ├── a2a-protocol/              # A2A SDK guides, AgentCard templates, validator, mock server
│       ├── pydantic-ai/               # PydanticAI references, Groq runners, sector agent templates
│       ├── fastmcp/                   # FastMCP server construction and testing patterns
│       ├── fastapi/                   # FastAPI route and SSE streaming best practices
│       └── ui-ux-pro-max/             # UI/UX design intelligence and design systems
│
├── backend/
│   ├── main.py                        # Unified FastAPI gateway mounting all sector sub-apps
│   ├── demo_platform.py               # End-to-end platform demonstration script
│   ├── core/                          # Shared platform infrastructure
│   │   ├── config.py                  # Pydantic PlatformSettings (loaded via .env)
│   │   ├── database/                  # DuckDB connection management and parameterized queries
│   │   ├── knowledge_graph/           # NetworkX causal graph engine and ontology
│   │   ├── econometrics/              # Causal impulse response simulation and Granger tests
│   │   ├── protocols/a2a/             # A2A AgentCard, Central Registry, and Task lifecycle
│   │   ├── protocols/mcp/             # FastMCP client utilities
│   │   └── orchestrator/              # LangGraph multi-agent orchestration and state
│   │
│   ├── real_sector/                   # GDP, GVA, IIP (FastMCP + A2A + PydanticAI Agent)
│   ├── agriculture_sector/            # Crops, Monsoon, MSP, Mandi Prices
│   ├── prices_sector/                 # CPI, WPI, Core/Food/Fuel Inflation
│   ├── monetary_sector/               # Repo rate, M3, Liquidity, Stance
│   ├── finance_sector/                # Bank Credit, Gross NPA, Financial Stability
│   ├── capital_market_sector/         # NIFTY, VIX, FII/DII, G-Sec
│   ├── fiscal_sector/                 # Deficit, GST, Union Capex, Debt
│   ├── external_sector/               # BoP, Forex Reserves, Trade Deficit
│   ├── labour_sector/                 # EPFO, PLFS Unemployment, Wages
│   ├── services_sector/               # Services GVA, IT Exports, PMI
│   └── tests/                         # Pytest test suite (27/27 unit and integration tests)
│
└── frontend/                          # React + TypeScript + Vite + Tailwind CSS dashboard
```

---

## Quickstart Guide

### 1. Prerequisites
Ensure Python 3.12+ and Node.js 18+ are installed.

```powershell
# Clone the repository
git clone https://github.com/Hariprasaadh/macrograph-ai.git
cd macrograph-ai

# Activate virtual environment
.venv\Scripts\activate
```

### 2. Configure Environment
Create a `.env` file in `backend/` or repository root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
MODEL_PROVIDER=groq
FAST_MODEL=llama-3.1-8b-instant
REASONING_MODEL=llama-3.3-70b-versatile
DATABASE_PATH=macro_store.duckdb
```

*(Note: If no API key is provided, the platform automatically utilizes deterministic offline fallback synthesis without failing).*

### 3. Run Automated Tests
Execute the full test suite:

```powershell
pytest backend/tests/ -v
```

### 4. Run the Platform Demo
Execute the multi-agent orchestration demonstration:

```powershell
python backend/demo_platform.py
```

### 5. Launch the FastAPI Gateway
Start the backend server on `http://127.0.0.1:8000`:

```powershell
uvicorn backend.main:app --reload --port 8000
```
Interactive OpenAPI documentation will be accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 6. Launch Frontend Dashboard
```powershell
cd frontend
npm install
npm run dev
```

---

## Core API Endpoints

### 1. Multi-Agent Research Analysis
`POST /api/v1/analyze`
```json
{
  "query": "Assess the impact of rising global crude prices on Indian CPI inflation, RBI repo rate policy, and corporate earnings.",
  "scenario_shock": {
    "name": "Global Brent Crude Surge (+20 USD/bbl)",
    "variable": "in.macro.prices.brent_crude",
    "magnitude": 20.0
  }
}
```
**Response:** Delivers verified observations, traversed transmission paths, impulse response projections, and the synthesized, cited intelligence report.

### 2. Causal Scenario Impulse Simulation
`POST /api/v1/simulate`
```json
{
  "scenario_name": "Monetary Policy Tightening (+50 bps)",
  "shock_variable": "in.macro.monetary.repo_rate",
  "shock_magnitude": 0.50,
  "horizon_periods": 4
}
```

### 3. Knowledge Graph Transmission Path
`GET /api/v1/kg/path?source_id=in.macro.prices.brent_crude&target_id=in.macro.real.gdp_growth`
- Returns: Shortest transmission path, hop count, cumulative transmission lag (months), and edge causal classifications.

### 4. Downstream Shock Reachability
`GET /api/v1/kg/impacts?shock_id=in.macro.prices.brent_crude`
- Returns: All reachable macroeconomic indicators affected downstream by the specified shock.

### 5. A2A Agent Registry
`GET /a2a/registry`
- Returns: All discoverable `AgentCard` specifications, sector capabilities, and JSON-RPC task endpoints.

---

## Agent Engineering Rules

1. **Strict Citation is Mandatory:** Every economic claim must cite the authoritative source agent, the FastMCP tool/source, and the specific data point.
2. **DuckDB Query Safety:** All SQL queries must be parameterized (`?`). F-strings and string concatenations in SQL are strictly prohibited.
3. **Async First:** All FastAPI endpoints, FastMCP tools, and LangGraph nodes performing I/O must be `async def`.
4. **Resilience Retries:** All external calls (Groq LLM, government APIs) must be wrapped with Tenacity exponential retries.
5. **No Emojis in Code:** Comments, docstrings, and log messages must be professional and emoji-free.

---

## License & Attribution
Distributed under the MIT License. Developed for research and institutional macroeconomic intelligence on the Indian economy.
