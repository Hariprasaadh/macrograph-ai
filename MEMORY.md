# Macrograph AI — System Architecture & Institutional Memory (MEMORY.md)

## 1. Project DNA & Core Philosophy
**Macrograph AI** is an academically rigorous, multi-agent macroeconomic intelligence platform built specifically for the Indian economy. Its primary purpose is to model macroeconomic transmission channels, evaluate policy interventions (monetary, fiscal, supply-side), and forecast impulse response scenarios across physical output, monetary conditions, prices, and financial markets.

### Key Architectural Invariants
1. **Mathematical Determinism**: Large Language Models (LLMs) are strictly prohibited from performing mathematical calculations, calculating statistical Z-scores, compounding growth rates, or simulating impulse responses. All math is executed deterministically in Python (`numpy`, `scipy`, `statsmodels`) or DuckDB.
2. **Zero Hardcoded Data & Live API Mandate**: Never hardcode indicator values, dates, or simulated numbers. All statistical metrics and indicators must be fetched dynamically from live official APIs. If a live API endpoint is down, unreachable, or returns invalid data, the system must return an explicit, structured error rather than falling back to fake or hardcoded numbers.
3. **Decoupled Agent-to-Agent (A2A) Architecture**: Agents communicate through standardized JSON-based A2A message passing (`TaskRequest`, `TaskResponse`, `A2AArtifact`). Domain agents operate as modular autonomous executors that can be run as local classes or independent network microservices.
4. **Standard Model Context Protocol (FastMCP)**: All analytical data queries are encapsulated as FastMCP tools (`fastmcp`), ensuring standardized, secure tool execution.
5. **Rigorous Causal Classification**: Relationships in the Knowledge Graph are never labeled simply as "correlated". Every transmission edge is categorized into one of five rigorous tiers: `THEORY`, `STATISTICAL_ASSOCIATION`, `LAGGED_RELATIONSHIP`, `GRANGER_PREDICTIVE`, or `STRUCTURAL_CAUSAL_MODEL`.

---

## 2. Technology Stack & Architectural Rationale

| Layer | Technology | Architectural Rationale |
| :--- | :--- | :--- |
| **Orchestration** | `langgraph` (v1.2+) | Stateful, DAG-driven multi-agent orchestration with deterministic node execution and clear state aggregation. |
| **Agent Protocol** | `a2a-sdk` (v1.1+) + `pydantic` (v2.10+) | Formal Agent-to-Agent (A2A) protocol with JSON Schema validation and Server-Sent Events (SSE) streaming. |
| **Tool Protocol** | `fastmcp` (v3.4+) | Fast, lightweight Model Context Protocol implementation for domain data inspection and tool invocation. |
| **API Gateway** | `fastapi` + `uvicorn` | High-performance async REST & SSE gateway with mounted sector sub-applications. |
| **Analytical Store** | `duckdb` (v1.1+) | Embedded, high-performance in-process columnar SQL database (`macro_store.duckdb`). Provides sub-millisecond analytical queries, rolling window statistics, and zero external database configuration for developers. |
| **Knowledge Graph** | `networkx` (v3.4+) + `neo4j` | NetworkX delivers in-memory (<1ms) shortest path traversal, latency summation, and dynamic Mermaid flowchart generation. Neo4j driver provides enterprise graph persistence when enabled. |
| **Econometrics** | `statsmodels`, `scipy`, `scikit-learn` | Vector autoregression, Granger causality $F$-tests, elasticity-scaled impulse response propagation, and rolling statistical distributions. |
| **LLM Engine** | `langchain-groq` | Resilient model-agnostic client utilizing Groq Cloud (`llama-3.3-70b-versatile` for deep causal synthesis, `llama-3.1-8b-instant` for fast query decomposition) with exponential retry and deterministic offline fallback. |

---

## 3. Canonical Data Dictionary & Hierarchy

All economic variables in the platform follow the hierarchical dot-notation: `in.macro.<sector>.<indicator>`.

### Canonical Indicators Catalog
| Canonical Indicator ID | Descriptive Name | Sector | Unit | Frequency | Authority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `in.macro.real.gdp_growth` | Quarterly Real GDP Growth Rate | Real Economy | % YoY | Quarterly | MoSPI |
| `in.macro.real.iip_growth` | Index of Industrial Production Growth | Real Economy | % YoY | Monthly | MoSPI |
| `in.macro.real.gfcf_investment` | Gross Fixed Capital Formation | Real Economy | % of GDP | Quarterly | MoSPI |
| `in.macro.prices.cpi_headline` | All India CPI Combined Headline Inflation | Prices & Inflation | % YoY | Monthly | MoSPI |
| `in.macro.prices.cpi_food` | Consumer Food Price Index Inflation | Prices & Inflation | % YoY | Monthly | MoSPI |
| `in.macro.prices.wpi_all` | Wholesale Price Index All Commodities | Prices & Inflation | % YoY | Monthly | OEA / DPIIT |
| `in.macro.prices.brent_crude` | Brent Crude Oil Benchmark Spot Price | Prices & Inflation | USD/barrel | Daily | EIA / Markets |
| `in.macro.monetary.repo_rate` | RBI Policy Repo Rate | Monetary & Banking | % p.a. | Policy / Bi-monthly | RBI DBIE |
| `in.macro.monetary.standing_deposit_facility` | Standing Deposit Facility (SDF) Rate | Monetary & Banking | % p.a. | Bi-monthly | RBI DBIE |
| `in.macro.monetary.cash_reserve_ratio` | Cash Reserve Ratio (CRR) | Monetary & Banking | % of NDTL | Bi-monthly | RBI DBIE |
| `in.macro.monetary.bank_credit_growth` | Scheduled Commercial Banks Credit Growth | Monetary & Banking | % YoY | Fortnightly | RBI DBIE |
| `in.macro.fiscal.debt_to_gdp` | General Government Debt-to-GDP Ratio | Fiscal | % of GDP | Annual | MoF / RBI |
| `in.macro.fiscal.central_capex_growth` | Central Government Capital Expenditure Growth | Fiscal | % YoY | Monthly / Annual | CGA / MoF |
| `in.macro.fiscal.gross_tax_growth` | Gross Tax Revenue Growth | Fiscal | % YoY | Monthly / Annual | CGA |
| `in.macro.external.forex_reserves` | Foreign Exchange Reserves | External | Billion USD | Weekly | RBI DBIE |
| `in.macro.external.usd_inr_exchange_rate` | USD/INR Spot Reference Rate | External | INR per USD | Daily | RBI / Markets |
| `in.macro.external.merchandise_trade_deficit`| Merchandise Trade Deficit | External | Billion USD | Monthly | MoC |
| `in.macro.capmarkets.nifty_50` | NIFTY 50 Benchmark Equity Index | Capital Markets | Points | Daily | NSE |
| `in.macro.capmarkets.india_vix` | India VIX Volatility Index | Capital Markets | Points | Daily | NSE |
| `in.macro.capmarkets.corporate_earnings_growth` | Corporate Earnings (EPS/PAT) Growth | Capital Markets | % YoY | Quarterly | NSE / BSE |
| `in.macro.capmarkets.dii_mutual_fund_flows` | DII & Mutual Fund Net Equity Inflows | Capital Markets | INR Crore | Monthly | AMFI / SEBI |
| `in.macro.agri.foodgrain_production` | Total Foodgrain Production Volume | Agriculture & Rural | Million Tonnes | Annual / Advance | MoA&FW |
| `in.macro.agri.minimum_support_price_growth` | Minimum Support Price (MSP) Growth | Agriculture & Rural | % YoY | Seasonal | CACP / MoA&FW |
| `in.macro.labour.epfo_additions` | Net Monthly EPFO Payroll Additions | Labour & Employment | Net Persons | Monthly | EPFO / MoSPI |
| `in.macro.labour.unemployment_rate` | PLFS Current Weekly Status Unemployment Rate | Labour & Employment | % | Quarterly | MoSPI |

---

## 4. Current Implementation State & Code Audit

### What is Completed & Operational
1. **Canonical Schema & Pydantic Data Layer** ([backend/core/data/schema.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/data/schema.py)): Complete definition of indicators, observations, causal relations, and scenario results.
2. **Embedded DuckDB Macro Store** ([backend/core/database/macro_store.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/database/macro_store.py)): Active file `macro_store.duckdb` seeded with baseline official historical observations across all 8 sectors.
3. **Macroeconomic Knowledge Graph & Ontology** ([backend/core/knowledge_graph/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/knowledge_graph/)): In-memory NetworkX directed graph engine with shortest path search, multi-hop latency summation, and dynamic Mermaid diagram generation.
4. **Causal Econometric Engine** ([backend/core/econometrics/causal_engine.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/econometrics/causal_engine.py)): Impulse response scenario simulation with transmission lag propagation and Granger causality $F$-test computation.
5. **Dynamic A2A Protocol Layer** ([backend/core/protocols/a2a/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/protocols/a2a/)): Central `AgentRegistry`, Pydantic models for `AgentCard`, `TaskRequest`, and `TaskResponse`, and async SSE chunk streaming.
6. **LangGraph Multi-Agent Orchestrator** ([backend/core/orchestrator/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/core/orchestrator/)): Full StateGraph pipeline coordinating decomposition, A2A dispatch, KG traversal, and Groq LLM synthesis.
7. **FastMCP Servers**: 6 active FastMCP servers (`real_sector_mcp`, `finance_sector_mcp`, `capital_markets_mcp`, `prices_sector_mcp`, `monetary_sector_mcp`, `labour_sector_mcp`).
8. **Unified FastAPI Gateway** ([backend/main.py](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/main.py)): REST routes for `/health`, `/api/v1/analyze`, `/api/v1/simulate`, `/api/v1/kg/path`, `/api/v1/kg/impacts`, and `/a2a/registry`.
9. **Full Automated Test Suite** ([backend/tests/](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/tests/)): 27/27 unit and integration tests passing cleanly.

### Identified Gaps & Modifications Required in Existing Code
1. **Full 8-Sector A2A Executor Decoupling**:
   - In `backend/core/orchestrator/registry_bootstrap.py`, only 3 domain executors (`RealSectorAgentExecutor`, `FinanceSectorAgentExecutor`, `CapitalMarketsAgentExecutor`) are currently registered.
   - In `backend/core/orchestrator/graph.py`, `PRICES_INFLATION`, `MONETARY_BANKING`, `FISCAL`, and `EXTERNAL` are currently handled by the Finance Sector executor, while `AGRICULTURE_RURAL` and `LABOUR_EMPLOYMENT` are handled by the Real Sector executor.
   - *Modification Planned*: Create dedicated `AgentExecutor` classes for Prices, Monetary, Fiscal, External, Agriculture, and Labour so all 8 domains are standalone A2A entities.
2. **Sub-Application Mounts in Gateway**:
   - Only `/real-sector`, `/finance-sector`, and `/capital-markets` are mounted in `backend/main.py`. The remaining sectors should have dedicated sub-apps mounted.
3. **Frontend Dashboard Scaffold**:
   - The directory `frontend/` is currently empty. A modern React + Vite + TypeScript web dashboard needs to be created with Plotly financial time-series charts, Cytoscape.js interactive Knowledge Graph visualizer, and scenario simulation sliders.
4. **Policy Document RAG (Qdrant)**:
   - Vector database ingestion for RBI circulars, Union Budget speeches, and Economic Survey PDF documents using semantic chunking.

---

## 5. Environment & Execution Conventions

- **Operating System**: Windows (PowerShell shell).
- **Python Version**: Python 3.12 (Virtual environment at `.venv\`).
- **Activation Command**:
  ```powershell
  .venv\Scripts\activate
  ```
- **Running Tests**:
  ```powershell
  .venv\Scripts\pytest backend/tests -v
  ```
- **Running Platform Demo**:
  ```powershell
  .venv\Scripts\python backend/demo_platform.py
  ```
- **Starting FastAPI Backend Server**:
  ```powershell
  .venv\Scripts\uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
  ```

---

## 6. Antigravity Customization Architecture

Customizations are stored in:
- Workspace root: `.agents/skills/<skill-name>/SKILL.md` (the official Antigravity discovery root).
- Global root: `~/.gemini/config/`.
- Every `SKILL.md` must contain valid YAML frontmatter with `name` and `description`, followed by markdown instructions, domain indicators, analytical guidelines, and MCP tool references.
