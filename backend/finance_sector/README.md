# Finance Sector Agent Module (A2A & MCP Protocol Compliant)

The **Finance Sector Agent** provides explainable macroeconomic intelligence, live data fetchers, and AI tool capabilities for 5 key Indian financial indicators:

1. **Quarterly Real GDP Growth**: Direct query from official **MoSPI Power BI API** (`Quaterly GDP Rate(%)Base24`, `modelId: 6182686`).
2. **Headline CPI Inflation Rate**: **MoSPI CPI Release / World Bank API**.
3. **RBI Policy Repo Rate**: **Reserve Bank of India (RBI) Monetary Policy Committee**.
4. **General Government Debt-to-GDP Ratio**: **IMF World Economic Outlook / Ministry of Finance**.
5. **Foreign Exchange Reserves**: **Reserve Bank of India (RBI) Weekly Statistical Supplement**.

---

## 1. Agent-to-Agent (A2A) Protocol Specifications

### Agent Card Discovery (`/.well-known/agent.json`)
Exposes capability specifications at:
- `GET /.well-known/agent.json`
- `GET /finance-sector/agent-card`

### Advertised Skills:
1. `gdp_growth_analysis`: Quarterly Real & Nominal GDP Growth analysis.
2. `cpi_inflation_analysis`: Headline CPI Inflation rate YoY analysis.
3. `repo_rate_analysis`: RBI Repo Rate, SDF, MSF, and interest rate transmission.
4. `debt_to_gdp_analysis`: General Government Debt to GDP ratio & fiscal sustainability.
5. `forex_reserves_analysis`: Total Foreign Exchange Reserves (Billion USD) & external liquidity buffer.
6. `finance_sector_comprehensive_synthesis`: Integrated explainable financial sector intelligence report.

### Task Management API:
- `POST /a2a/tasks`: Submit asynchronous or synchronous A2A task requests.
- `GET /a2a/tasks/{task_id}`: Query task lifecycle state (`submitted` → `working` → `completed`), returned `A2AMessage` objects, and `A2AArtifact` payloads (JSON metrics matrix + Markdown explainable report).
- `POST /a2a/tasks/{task_id}/cancel`: Cancel an ongoing task.

---

## 2. Model Context Protocol (MCP) Integration

Exposes tool specifications and a JSON-RPC 2.0 interface for LLMs:
- `POST /mcp` or `POST /finance-sector/mcp`

### Supported JSON-RPC Methods:
- `tools/list`: Returns JSON Schema specifications for `get_gdp_growth_snapshot`, `get_cpi_inflation_snapshot`, `get_repo_rate_snapshot`, `get_debt_to_gdp_snapshot`, and `get_forex_reserves_snapshot`.
- `tools/call`: Executes tool with arguments `{ "name": "get_gdp_growth_snapshot", "arguments": {"prices": "Constant"} }`.

---

## 3. Explainable Macroeconomic Reasoning Engine

Produces structured markdown reports with:
- **Executive Summary & Macroeconomic Stance**
- **Deep Sector Explanations**: Inflation target bands, Real interest rate transmission (`Repo Rate minus Inflation`), Fiscal interest coverage, Import cover (months of imports protected).
- **Mermaid Interplay Diagrams**: Visualizing causal links between inflation, monetary policy rates, GDP capital growth, fiscal debt, and foreign reserves.
