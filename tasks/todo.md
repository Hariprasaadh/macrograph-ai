# Tasks & Todo List

## Current Tasks
- [x] 1. Update `backend/core/config.py` to support per-sector keys (`AGR_REAL_KEY`, `FIN_FIS_KEY`, `CAP_MON_KEY`, `ORCH_KEY`, `PRIC_LAB_KEY`, `SERV_EXT_KEY`), Tavily keys (`TVLY_KEY_1`, `TVLY_KEY_2`, `TVLY_KEY_3`), `openai/gpt-oss-20b`/`120b` models, robust `.env` resolution, and CORS origins.
- [x] 2. Fix hardcoded Tavily API key in `mcp.json` using `${TVLY_KEY_1}` environment variable interpolation.
- [x] 3. Delete dead root `main.py` file.
- [x] 4. Refactor `backend/main.py` (previously 1142 lines) into modular sub-modules under `backend/api/` (`backend/api/chat.py`, `backend/api/chat_helpers.py`, `backend/api/chat_config.py`, and `backend/api/dashboard.py`) so every file is strictly under 400 lines (all under 330 lines).
- [x] 5. Close the dashboard placeholder gap: wire `backend/api/dashboard.py` to query real data across DuckDB stores (`real_sector`, `capital_market_sector`, `external_sector`, `labour_sector`, `monetary_sector`, `finance_sector`) with accurate citations, and update `frontend/src/components/DashboardView.tsx` to display verified indicators rather than empty mock previews.
- [x] 6. Fix CORS policy in `backend/main.py` to use configured origins instead of invalid `allow_origins=["*"]` with `allow_credentials=True`.
- [x] 7. Verify all tests pass (`pytest backend/tests/ -v`), verify frontend builds (`npm run build`), and ensure all Python files satisfy the 400-line rule.

## Review & Documented Results
- **Configuration Alignment (`core/config.py`)**: Sourced per-sector keys (`AGR_REAL_KEY`, `FIN_FIS_KEY`, `CAP_MON_KEY`, `ORCH_KEY`, `PRIC_LAB_KEY`, `SERV_EXT_KEY`), Tavily keys (`TVLY_KEY_1`, `TVLY_KEY_2`, `TVLY_KEY_3`), and defaulted models to `openai/gpt-oss-20b` and `openai/gpt-oss-120b` as defined in `.env`.
- **MCP Security**: Removed hardcoded dev key in `mcp.json` and replaced with `${TVLY_KEY_1}` interpolation.
- **Dead Code Cleaned**: Removed obsolete 7-line `main.py` from repository root.
- **400-Line Limit Compliance**: Refactored monolithic `backend/main.py` (1,142 lines) into `backend/main.py` (221 lines), `backend/api/dashboard.py` (320 lines), `backend/api/chat.py` (248 lines), `backend/api/chat_helpers.py` (328 lines), and `backend/api/chat_config.py` (251 lines).
- **CORS Restricted**: Replaced wildcard `allow_origins=["*"]` with `settings.CORS_ORIGINS`.
- **Dashboard Telemetry Enriched**: Real DuckDB stores across active sectors now populate verified indicators with explicit periods and citation references. Frontend displays verified telemetry cards instead of empty mock previews.
- **Verification**: All 21 core tests and all 75 sector tests pass; `npm run build` succeeds cleanly.
