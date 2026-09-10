# Developer 3 — Structural, Real Economy & External Sector Domain Engineer

## Mission Summary
You are responsible for three vital structural, real economy, and external sectors:
1. **Labour & Employment Sector** (`backend/labour_sector/`)
2. **Agriculture & Rural Sector** (`backend/agriculture_sector/` — New Package)
3. **External Sector** (`backend/external_sector/` — New Package)

Your job is to implement dedicated A2A `AgentExecutor` classes, live data clients with official API endpoints and verified DuckDB fallback, tool registries, FastMCP servers, and FastAPI sub-apps.

---

## Assigned Files & Directory Scope
```
backend/
├── labour_sector/
│   ├── config.py                      # Indicator IDs, timeouts, EPFO URLs
│   ├── mcp_server.py                  # [EXISTING] Labour FastMCP server
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /labour-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── labour_data_client.py      # Live client (EPFO payroll & PLFS)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # LabourToolInput & tool invoke registry
│       └── executor.py                # LabourEmploymentAgentExecutor & get_agent_card()
├── agriculture_sector/                # [NEW PACKAGE]
│   ├── __init__.py
│   ├── config.py                      # Indicator IDs, Agmarknet endpoints
│   ├── mcp_server.py                  # FastMCP server for crop & foodgrain tools
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /agriculture-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── agri_data_client.py        # Live client (Agmarknet, IMD monsoon, CCEA MSP)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # AgriToolInput & tool invoke registry
│       └── executor.py                # AgricultureRuralAgentExecutor & get_agent_card()
├── external_sector/                   # [NEW PACKAGE]
│   ├── __init__.py
│   ├── config.py                      # Indicator IDs, RBI FX endpoints
│   ├── mcp_server.py                  # FastMCP server for forex & trade balance
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # Sub-app mounted at /external-sector
│   ├── clients/
│   │   ├── __init__.py
│   │   └── external_data_client.py    # Live client (RBI WSS, Yahoo INR=X, MoC Trade)
│   └── agents/
│       ├── __init__.py
│       ├── tools.py                   # ExternalToolInput & tool invoke registry
│       └── executor.py                # ExternalSectorAgentExecutor & get_agent_card()
└── tests/
    └── test_structural_domain_agents.py # [NEW] Tests for Labour, Agri & External agents
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

### 1. Labour & Employment Sector
- **Agent Name**: `"Labour & Employment Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/labour-sector`
- **Canonical Indicators**:
  - `in.macro.labour.epfo_additions`: Net Monthly EPFO Payroll Additions (Workers) — EPFO
  - `in.macro.labour.unemployment_rate`: PLFS Unemployment Rate (%) — MoSPI
- **Live Client Implementation (`labour_data_client.py`)**:
  - Parse EPFO monthly payroll press bulletin figures with fallback to verified DuckDB observations.
  - Compute formalization momentum (% YoY growth in payroll additions).
- **FastMCP Tools**: Ensure tools in `mcp_server.py` (`get_epfo_payroll_snapshot`) consume the client.

### 2. Agriculture & Rural Sector (New Package)
- **Agent Name**: `"Agriculture & Rural Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/agriculture-sector`
- **Canonical Indicators**:
  - `in.macro.agri.foodgrain_production`: Total Foodgrain Output (Million Tonnes) — Ministry of Agriculture
  - `in.macro.agri.minimum_support_price_growth`: Average MSP Hike (% YoY) — CCEA / Agmarknet
  - `in.macro.agri.monsoon_departure`: IMD Southwest Monsoon % Departure from LPA — IMD
- **FastMCP Server (`mcp_server.py`)**:
  - Tool `get_foodgrain_production_snapshot()`
  - Tool `get_msp_growth_snapshot()`
  - Tool `get_monsoon_departure_snapshot()`

### 3. External Sector (New Package)
- **Agent Name**: `"External Sector Macroeconomic Agent"`
- **Endpoint URL**: `http://localhost:8000/external-sector`
- **Canonical Indicators**:
  - `in.macro.external.forex_reserves`: Foreign Exchange Reserves ($ Billion USD) — RBI DBIE
  - `in.macro.external.usd_inr_exchange_rate`: USD/INR Spot Reference Rate — Yahoo `INR=X` / RBI
  - `in.macro.external.merchandise_trade_deficit`: Merchandise Trade Balance ($ Billion USD) — MoC
  - `in.macro.external.current_account_deficit`: CAD as % of GDP — RBI
- **Live Client Implementation (`external_data_client.py`)**:
  - For `usd_inr_exchange_rate`: Use `yfinance.Ticker("INR=X").history(period="5d")['Close'].iloc[-1]`.
  - For `forex_reserves`: RBI Weekly Statistical Supplement data or verified DuckDB store.
  - Compute **Import Cover Adequacy** (Months of imports buffered by current FX reserves).
- **FastMCP Server (`mcp_server.py`)**:
  - Tool `get_forex_reserves_snapshot()`
  - Tool `get_exchange_rate_snapshot()`
  - Tool `get_trade_balance_snapshot()`

---

## Verification & Test Commands
Author `backend/tests/test_structural_domain_agents.py` testing:
1. Each executor runs without errors on both keyword queries and generic requests.
2. `get_agent_card()` returns valid skills and schemas.
3. Live clients return valid data or fallback to cached observations cleanly.
4. Error handling produces valid `LiveAPIErrorResponse` when an endpoint is unreachable.

Run your tests:
```powershell
.venv\Scripts\pytest backend/tests/test_structural_domain_agents.py -v
```

## Definition of Done (DoD)
- [ ] `LabourEmploymentAgentExecutor`, `AgricultureRuralAgentExecutor`, and `ExternalSectorAgentExecutor` are fully implemented and export `get_agent_card()`.
- [ ] All 3 sub-apps (`/labour-sector`, `/agriculture-sector`, `/external-sector`) boot cleanly with Swagger docs.
- [ ] Zero fake or hardcoded numbers: all indicators derive from live API endpoints or verified DuckDB baseline records.
- [ ] All unit tests in `test_structural_domain_agents.py` pass.
