# Real Sector Agent Module (A2A & MCP Protocol Compliant)

The Real Sector module ingests data workbooks under `backend/real_sector/data/raw`, maintains untouched raw sources, and produces normalized CSV tables in `backend/real_sector/data/processed` via `RealSectorPipeline.refresh()`.

It operates as an **A2A (Agent-to-Agent) Protocol** compliant domain agent and exposes tools over the **Model Context Protocol (MCP)** standard.

---

## 1. Agent-to-Agent (A2A) Protocol Specifications

### Agent Card Discovery (`/.well-known/agent.json`)
The Real Sector Agent advertises its capabilities via an Agent Card JSON structure hosted at:
- `GET /.well-known/agent.json`
- `GET /real-sector/agent-card`

### Advertised Skills:
1. `national_income_analysis`: Quarterly real GDP, nominal GDP, and Gross Fixed Capital Formation (GFCF).
2. `industrial_production_analysis`: IIP use-based indicators and manufacturing growth.
3. `price_inflation_analysis`: Headline CPI, Core CPI, WPI, and House Price Index.
4. `agricultural_snapshot`: Foodgrain production, yield, and Minimum Support Prices (MSP).
5. `real_sector_comprehensive_synthesis`: Integrated real-sector macroeconomic report.

### Task Management API:
- `POST /a2a/tasks`: Submit asynchronous or synchronous A2A task requests.
- `GET /a2a/tasks/{task_id}`: Inspect task lifecycle state (`submitted` → `working` → `completed`), returned `A2AMessage` objects, and `A2AArtifact` payloads (JSON metrics matrix + Markdown economic reasoning report).
- `POST /a2a/tasks/{task_id}/cancel`: Cancel an ongoing task.

---

## 2. Model Context Protocol (MCP) Integration

Exposes tool specifications and a JSON-RPC 2.0 interface for LLMs:
- `POST /mcp` or `POST /real-sector/mcp`

### Supported JSON-RPC Methods:
- `tools/list`: Returns JSON Schema specifications for `get_agriculture_snapshot`, `get_industry_snapshot`, `get_national_income_snapshot`, and `get_prices_snapshot`.
- `tools/call`: Executes tool with arguments `{ "name": "get_prices_snapshot", "arguments": {} }`.

---

## 3. Legacy REST Tool Interface

For direct integration without A2A/MCP wrappers:
- `GET /real-sector/tools`: List tools in OpenAI functions format.
- `POST /real-sector/tools/{tool_name}`: Directly invoke a sector tool.
