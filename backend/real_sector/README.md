# Real Sector module

The module reads every supplied workbook under `backend/real_sector/data/raw`, keeps those
source files untouched, and writes normalized CSV tables to `backend/real_sector/data/processed`
only when `RealSectorPipeline.refresh()` is called.

It exposes four independent tools for an LLM integration:

- `get_agriculture_snapshot`
- `get_industry_snapshot`
- `get_national_income_snapshot`
- `get_prices_snapshot`

Register `SectorToolRegistry(pipeline).openai_functions()` with an LLM provider, then
pass the selected function name and validated arguments to `registry.invoke(...)`.
The same functions are available over FastAPI at `GET /real-sector/tools` and
`POST /real-sector/tools/{tool_name}`. No multi-agent orchestrator is included.
