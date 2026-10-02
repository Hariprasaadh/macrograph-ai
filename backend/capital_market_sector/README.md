# Capital Markets Sector Agent

A domain-specific sector module for Indian capital markets intelligence with a clean agent/tool/MCP/A2A architecture.

## Design Goals
- Sector agent for capital markets intelligence
- Specialized tools for each sub-domain
- MCP schema for LLM tool discovery and invocation
- A2A agent card for cross-agent coordination

## Sub-domains
1. Equity Market Indices (NIFTY 50 `^NSEI`, SENSEX `^BSESN`)
2. Market Volatility Index (India VIX `^INDIAVIX`)
3. Corporate Earnings & EPS (NIFTY 50 TTM EPS, PAT Growth)
4. Primary Market Activity (IPO Mobilization & Debt Issuances via SEBI)
5. Mutual Fund Flows & Domestic Institutional Activity (AMFI / SEBI DII Net Purchases)

## Data Sources & Yahoo Finance Integration
All empirical equity and market volatility indicators are retrieved through live financial feeds:
- **Yahoo Finance MCP / `yfinance` Client:**
  - `^NSEI`: NIFTY 50 index live prices and historical series
  - `^BSESN`: BSE SENSEX index live prices and historical series
  - `^INDIAVIX`: India VIX real-time volatility index
  - `INR=X`: USD/INR live spot exchange rate
- **SEBI & AMFI Canonical Stores:**
  - IPO Mobilization (Primary Market)
  - Equity Net Inflows & DII Net Purchases (Mutual Fund Flows)

## Quick Start

1. Open a terminal and navigate to the package:

```bash
cd backend/capital_market_sector
```

2. Install dependencies for the capital market sector:

```bash
python -m pip install -r requirements.txt
```

3. Run the tests to verify the package behavior:

```bash
python -m pytest tests/test_capital_market_sector.py
```

## Run the API

Start the FastAPI application:

```bash
uvicorn capital_market_sector.api.app:app --reload --port 8000
```

## Run the demo script

From the repository root, execute:

```bash
cd backend
python demo_capital_market_sector.py
```

This will run the Capital Markets A2A/MCP demo and print the agent card, available tools, and task artifacts.

## Verify output

### Check the agent card

```bash
curl http://127.0.0.1:8000/.well-known/agent.json
```

You should see JSON output containing the agent name:

```json
{
  "name": "Capital Markets Macroeconomic Agent",
  "description": "Specialized Indian Capital Markets Sector agent for equities, volatility, earnings, primary market, and mutual fund flows.",
  ...
}
```

### Send an A2A task request

```bash
curl -X POST http://127.0.0.1:8000/a2a/tasks \
  -H "Content-Type: application/json" \
  -d '{"query": "Check NIFTY 50 and VIX levels", "skills_required": ["equity_market_analysis", "volatility_analysis"]}'
```

A successful response should include a completed task and artifacts.

### Call the MCP tools listing endpoint


curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

A successful response should return a list of available tools.

## Notes

- The package now uses public-capital-market data sources and does not depend on internal DB persistence.
- If you run into network issues, the client includes fallback values so the package still returns valid output.
