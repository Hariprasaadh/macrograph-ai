# Tasks & Todo List

## Current Tasks
- [x] 1. Update `backend/core/config.py` to support per-sector keys (`AGR_REAL_KEY`, `FIN_FIS_KEY`, `CAP_MON_KEY`, `ORCH_KEY`, `PRIC_LAB_KEY`, `SERV_EXT_KEY`), Tavily keys (`TVLY_KEY_1`, `TVLY_KEY_2`, `TVLY_KEY_3`), `openai/gpt-oss-20b`/`120b` models, robust `.env` resolution, and CORS origins.
- [x] 2. Fix hardcoded Tavily API key in `mcp.json` using `${TVLY_KEY_1}` environment variable interpolation.
- [x] 3. Delete dead root `main.py` file.
- [x] 4. Refactor `backend/main.py` (previously 1142 lines) into modular sub-modules under `backend/api/` (`backend/api/chat.py`, `backend/api/chat_helpers.py`, `backend/api/chat_config.py`, and `backend/api/dashboard.py`) so every file is strictly under 400 lines (all under 330 lines).
- [x] 5. Close the dashboard placeholder gap: wire `backend/api/dashboard.py` to query real data across DuckDB stores (`real_sector`, `capital_market_sector`, `external_sector`, `labour_sector`, `monetary_sector`, `finance_sector`) with accurate citations, and update `frontend/src/components/DashboardView.tsx` to display verified indicators rather than empty mock previews.
- [x] 6. Fix CORS policy in `backend/main.py` to use configured origins instead of invalid `allow_origins=["*"]` with `allow_credentials=True`.
- [x] 7. Verify all tests pass (`pytest backend/tests/ -v`), verify frontend builds (`npm run build`), and ensure all Python files satisfy the 400-line rule.

## Active Phase: Institutional Dark-Mode Macroeconomic Intelligence Dashboard

- [x] 1. Trace and resolve HTTP 500 root causes:
  - Add `read_only=True` support to DuckDB connection managers in `backend/finance_sector/database.py` to prevent Windows file-lock contention.
  - Ensure `finance_sector.database.initialise_schema(seed_baseline=True)` is called in `backend/main.py` alongside other sectors.
  - Implement smart frontend gateway connection diagnostics with auto-reconnect countdown in `frontend/src/components/DashboardView.tsx`.
- [x] 2. Enrich backend telemetry endpoints (`backend/api/dashboard.py`):
  - Add historical time-series arrays for Bank Credit (13 periods), Asset Quality (9 periods), Lending Rates (7 periods), Aggregate Deposits (14 periods), GST collections (10 periods), and Fiscal Deficit (3 periods).
  - Include real live indicators from Fiscal Sector, Real Sector, and Services Sector DuckDB stores.
  - Ensure strict anti-hallucination citations (source agent, table reference, observation period).
- [x] 3. Update frontend TypeScript contracts (`frontend/src/types/index.ts`):
  - Define `TimeSeriesPoint`, `FiscalSectorData`, `RealSectorData`, `ServicesSectorData`, and expand `DashboardOverview`.
- [x] 4. Build institutional UI components & interactive visualizations:
  - Create `frontend/src/components/charts/TimeSeriesChart.tsx` (smooth SVG area/line chart with tooltips, crosshairs, time pills).
  - Create `frontend/src/components/charts/RadialGauge.tsx` (Solvency & Capital Adequacy CRAR / PCR gauge).
  - Create `frontend/src/components/charts/SectorBreakdown.tsx` (Credit deployment distribution).
  - Create `frontend/src/components/CommandPalette.tsx` (Keyboard-accessible search `Cmd+K` / `⌘F` for indicators, sectors, and actions).
  - Create `frontend/src/components/EvidenceDrawer.tsx` (Contextual drill-down drawer for citation provenance and calculations).
- [x] 5. Redesign `frontend/src/components/DashboardView.tsx`:
  - Donezo-inspired layout adapted for institutional dark mode (`#040814` / `#0a1226`).
  - Executive KPI cards with large typography, YoY badges, and DBIE citation pills.
  - Multi-sector perspective tabs (All, Finance, Fiscal, Real, Services).
  - Live market/policy ticker bar (Repo rate, GNPA multi-decadal low, sync status).
  - Restrained 3D depth and subtle ambient grid.
- [x] 6. Testing & verification:
  - Add pytest test suite in `backend/tests/test_dashboard_api.py`.
  - Verify all tests pass (`pytest backend/tests/test_dashboard_api.py -v`).
  - Verify frontend compiles cleanly (`npm run build`).
  - Verify no Python file exceeds 400 lines (backend/api/dashboard.py is 383 lines).

## Phase 3: Multi-Sector Dynamic Workspace, Analytical Studio & Open Data Integration

- [x] 1. Resolve Static / Identical Views Across Tabs:
  - Previously, changing tabs (`All`, `Finance`, `Fiscal`, `Real`, `Services`) did not update views or swap out charts.
  - Refactored `frontend/src/components/DashboardView.tsx` and modularized into 7 dedicated sector workspaces in `frontend/src/components/tabs/`:
    - `AllSectorsTabView.tsx`: Executive Cockpit, Scenario Simulator, Cross-Sector Studio, Anomaly Feed, and Daily Briefing.
    - `FinanceTabView.tsx`: Commercial Bank Credit Expansion, Fresh WALR vs Deposit Spread Chart, Solvency Radial Gauges, Sectoral Credit Deployment Breakdown, Deposits CD Ratio.
    - `FiscalTabView.tsx`: Union Budget 2025-26 (Expenditure ₹50.65L Cr, Receipts ₹34.96L Cr, Deficit 4.4%), Ministry Allocations Table, Monthly GST Inflow Time Series (10 periods).
    - `ExternalTabView.tsx`: USD/INR FBIL Reference Rate Chart, Forex Reserves ($700.2 Bn) Chart, Merchandise Trade Balance Table, CAD vs GDP (-0.8%).
    - `MarketsTabView.tsx`: 10-Year Benchmark G-Sec Yield Curve Chart, India VIX Volatility Chart, Monetary Policy Rate Corridor Matrix (Repo 6.50%, SDF 6.25%, MSF 6.75%, CRR 4.50%).
    - `RealLabourTabView.tsx`: 8-Core Infrastructure Industries YoY Breakdown (Coal, Steel, Cement), Services PMI Headline Index (59.2), MoSPI PLFS Unemployment Trend Chart, Sectoral GVA Share.
    - `StatesTabView.tsx`: National GSDP Aggregate (₹272.2L Cr), Top State Economy (Maharashtra ₹36.42L Cr), State GSDP Leaderboard Table with Growth Rates and Per Capita NSDP.
- [x] 2. Ingest Open Data Feeds (Indian Data Project & RBI DBIE):
  - Created `backend/api/open_data_helpers.py` ingesting static CORS-enabled JSON datasets:
    - `/data/budget/2025-26/summary.json` & `/data/budget/2025-26/expenditure.json`
    - `/data/states/2025-26/summary.json` & `/data/states/2025-26/gsdp.json`
    - `/data/employment/2025-26/summary.json` & `/data/employment/2025-26/unemployment.json`
    - `/data/economy/2025-26/summary.json` & `/data/economy/2025-26/sectors.json`
  - Integrated with official RBI DBIE Data API (`https://data-api.dbie.rbihub.in/api/tables`).
- [x] 3. Build Advanced Economic Intelligence Studio Tools:
  - `ScenarioSimulator.tsx`: Interactive macroeconomic shock sliders (Repo rate, Brent crude, USD/INR) with multi-quarter impulse response projections.
  - `CrossSectorStudio.tsx`: Dual-axis comparison studio with dynamic series alignment, Pearson correlation coefficient `r`, lead-lag indicators, and causal transmission notes.
  - `AnomalyFeed.tsx`: AI-detected structural macro shifts feed (Multi-decadal low GNPA, Credit expansion outpacing deposits, GST monthly record, Historic Forex reserves).
  - `DailyBriefingCard.tsx`: Macroeconomic institutional executive brief with 4 pillars and upcoming catalysts event horizon.
- [x] 4. Testing & Code Quality Assurance:
  - Expanded `backend/tests/test_dashboard_api.py` with `test_dashboard_open_data_telemetry`.
  - All 5 pytest tests pass (`pytest backend/tests/test_dashboard_api.py -v`).
  - Frontend builds with zero errors (`npm run build`, `tsc && vite build`).
  - All Python modules strictly adhere to the < 400 lines limit (`dashboard.py` = 326 lines, `dashboard_helpers.py` = 284 lines, `open_data_helpers.py` = 209 lines).
  - Strict citation and zero-hallucination policy enforced across all rendered statistics.



## Knowledge Graph hardening (Causal GraphRAG)
- [x] llm_client: add missing `import os` (NameError when no Groq key); offline notice wording fixed.
- [x] schema: ID regex, frequency whitelist, sign `+`/`-`, mechanism min length, non-empty assumptions, p-value rule (None only for THEORY), self-loop guard.
- [x] ontology: stable `rel-<8 hex>` IDs (uuid5), `validate()` rejects self-loops/unknown endpoints/duplicate IDs.
- [x] networkx_engine: 4-key neighborhood shape for known and unknown nodes; `has_node`.
- [x] causal_engine: first-seen-order provenance; Granger failure results carry cause/effect.
- [x] neo4j_store: lazy, settings-only, optional (`NEO4J_URI` empty disables), `AFFECTS` schema, `sync_ontology` is the only write path; synced at gateway startup when enabled; `neo4j` optional extra in pyproject.
- [x] orchestrator: deterministic first-seen indicator order, pair only KG-known IDs (no 20-pair cap), synthesis prompt carries paths/relation_ids/mechanisms/scenario, causal-path table, verbatim taxonomy line, deterministic offline fallback, documentary evidence marked unavailable.
- [x] API: typed `ScenarioShock`, `Simulation error:` detail, `neo4j_enabled` in /health, causal_paths/scenario_result in chat payloads.
- [x] canonical_ids: removed wrong `manufacturing_gva -> gdp_growth` alias.
- [x] Tests: test_kg_schema, test_kg_networkx, test_causal_engine, test_kg_neo4j, test_kg_orchestrator, test_kg_api, test_llm_client.
- [ ] Follow-ups: regenerate `uv.lock` (`uv lock`) for the neo4j extra; fix KnowledgeGraphView field names and render Mermaid in the UI; Qdrant documentary evidence; real/agri/labour sectors emitting seed IDs.
- [x] Live E2E fixes: sector-native IDs alias onto ontology; live observations seed scenario baselines; prompt carries shocked_peak; KnowledgeGraphView rewritten against real API shape; uv.lock regenerated. 
