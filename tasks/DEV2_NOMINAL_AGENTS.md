# Developer 2 — Nominal Economy & Macro-Financial Domain Engineer

## Mission Summary
You are responsible for three core nominal and macro-financial sectors:
1. **Prices & Inflation Sector** (`backend/prices_sector/`)
2. **Monetary & Banking Sector** (`backend/monetary_sector/`)
3. **Fiscal Sector** (`backend/fiscal_sector/` — New Package)

Your job is to implement dedicated A2A `AgentExecutor` classes, live data clients with official API endpoints and verified DuckDB fallback, tool registries, and FastAPI sub-apps.

---

## Assigned Files & Directory Scope
```
backend/
├── prices_sector/
│   ├── config.py                      # Indicator IDs, timeouts, portal URLs
│   ├── mcp_server.py                  # [EXISTING] Prices FastMCP server
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /prices-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── price_data_client.py       # Live client (MoSPI CPI, DPIIT WPI, Yahoo Crude BZ=F)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # PricesToolInput & tool invoke registry
│       └── executor.py                # PricesInflationAgentExecutor & get_agent_card()
├── monetary_sector/
│   ├── config.py                      # Indicator IDs, timeouts, RBI DBIE URLs
│   ├── mcp_server.py                  # [EXISTING] Monetary FastMCP server
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /monetary-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── monetary_data_client.py    # Live client (RBI DBIE Repo/CRR/Credit)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # MonetaryToolInput & tool invoke registry
│       └── executor.py                # MonetaryBankingAgentExecutor & get_agent_card()
├── fiscal_sector/                     # [NEW PACKAGE]
│   ├── __init__.py
│   ├── config.py                      # Indicator IDs, CGA/MoF endpoints
│   ├── mcp_server.py                  # FastMCP server for debt & capex tools
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /fiscal-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── fiscal_data_client.py      # Live client (CGA accounts, Data.gov.in)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # FiscalToolInput & tool invoke registry
│       └── executor.py                # FiscalSectorAgentExecutor & get_agent_card()
└── tests/
    └── test_nominal_domain_agents.py  # [NEW] Tests for Prices, Monetary & Fiscal agents
```

---

## Architectural Reference Blueprint
Use `backend/capital_market_sector/agents/executor.py` and `backend/finance_sector/agents/executor.py` as your exact structural patterns:
1. Inherit from `core.protocols.a2a.AgentExecutor`.
2. Implement `@classmethod get_agent_card(...) -> AgentCard` advertising capabilities and `AgentSkill` items.
3. Implement `async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse`.
4. Return `A2AArtifact` containing both JSON metrics and a Markdown narrative summary with cryptographic SHA-256 provenance hashes.

---

## Detailed Specifications by Sector

### 1. Prices & Inflation Sector
- **Agent Name**: `"Prices & Inflation Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/prices-sector`
- **Canonical Indicators**:
  - `in.macro.prices.cpi_headline`: Headline CPI YoY (%) — MoSPI
  - `in.macro.prices.cpi_food`: Consumer Food Price Index YoY (%) — MoSPI
  - `in.macro.prices.wpi_all`: WPI All Commodities YoY (%) — DPIIT / OEA
  - `in.macro.prices.brent_crude`: Brent Crude Benchmark Spot (USD/bbl) — Yahoo `BZ=F`
- **Live Client Implementation (`price_data_client.py`)**:
  - For `brent_crude`: Use `yfinance.Ticker("BZ=F").history(period="5d")['Close'].iloc[-1]`.
  - On network timeout or HTTP 5xx: Use `macro_store.get_latest_canonical_observation()` as verified fallback cache.
  - If neither live nor cache is available: Return `LiveAPIErrorResponse`.
- **FastMCP Tools**: Ensure tools in `mcp_server.py` (`get_cpi_snapshot`, `get_wpi_snapshot`, `get_crude_oil_snapshot`) consume the client.

### 2. Monetary & Banking Sector
- **Agent Name**: `"Monetary & Banking Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/monetary-sector`
- **Canonical Indicators**:
  - `in.macro.monetary.repo_rate`: RBI Policy Repo Rate (%) — RBI DBIE
  - `in.macro.monetary.standing_deposit_facility`: SDF Rate (%) — RBI DBIE
  - `in.macro.monetary.cash_reserve_ratio`: CRR (% of NDTL) — RBI DBIE
  - `in.macro.monetary.bank_credit_growth`: Non-Food Bank Credit Growth (% YoY) — RBI DBIE
- **Live Client Implementation (`monetary_data_client.py`)**:
  - Parse DBIE SDMX/REST responses with fallback to verified DuckDB observations.
- **Analytical Metrics**: Compute **Real Policy Rate** ($\text{Repo Rate} - \text{Headline CPI}$) and **Monetary Policy Stance** (Hawkish / Neutral / Accommodative).

### 3. Fiscal Sector (New Package)
- **Agent Name**: `"Fiscal Sector Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/fiscal-sector`
- **Canonical Indicators**:
  - `in.macro.fiscal.debt_to_gdp`: General Government Debt-to-GDP (%) — MoF / RBI
  - `in.macro.fiscal.central_capex_growth`: Central Capex YoY Growth (%) — CGA
  - `in.macro.fiscal.gross_tax_growth`: Gross Tax & GST Growth (% YoY) — CGA
- **FastMCP Server (`mcp_server.py`)**:
  - Tool `get_debt_to_gdp_snapshot()`
  - Tool `get_capex_growth_snapshot()`
  - Tool `get_tax_revenue_snapshot()`

---

## Verification & Test Commands
Author `backend/tests/test_nominal_domain_agents.py` testing:
1. Each executor runs without errors on both keyword queries and generic requests.
2. `get_agent_card()` returns valid skills and schemas.
3. Live clients return valid data or fallback to cached observations cleanly.
4. Error handling produces valid `LiveAPIErrorResponse` when an endpoint is unreachable.

Run your tests:
```powershell
.venv\Scripts\pytest backend/tests/test_nominal_domain_agents.py -v
```

## Definition of Done (DoD)
- [ ] `PricesInflationAgentExecutor`, `MonetaryBankingAgentExecutor`, and `FiscalSectorAgentExecutor` are fully implemented and export `get_agent_card()`.
- [ ] All 3 sub-apps (`/prices-sector`, `/monetary-sector`, `/fiscal-sector`) boot cleanly with Swagger docs.
- [ ] Zero fake or hardcoded numbers: all indicators derive from live API endpoints or verified DuckDB baseline records.
- [ ] All unit tests in `test_nominal_domain_agents.py` pass.
