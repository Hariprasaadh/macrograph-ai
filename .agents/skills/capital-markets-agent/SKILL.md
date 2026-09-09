---
name: capital-markets-agent
description: Analytical workflows and protocol specifications for Indian equity indices, volatility regimes, corporate earnings, and institutional capital flows.
---

# Capital Markets Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded stock prices, index levels, VIX values, or simulated institutional flows are strictly prohibited.
- **Live API Ingestion**: All equity benchmarks (NIFTY 50, SENSEX), volatility indicators (India VIX), corporate earnings, and DII/FII mutual fund flows must be pulled live from market data APIs (e.g., NSE/BSE live feeds, Yahoo Finance `yfinance`, SEBI/AMFI disclosures).
- **Explicit Error Handling**: If live market data fails to fetch or the market API returns an error, the tool/agent **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_MARKET_API_UNAVAILABLE", "message": "Failed to fetch live capital market data from source: <details>"}`). It must **never** return fake or hardcoded index levels.

## Domain Scope
Analyzes Indian capital markets as a leading indicator of macroeconomic health:
1. **Benchmark Equities**: NIFTY 50 (`in.macro.capmarkets.nifty_50`) and SENSEX valuation multiples, returns, and momentum.
2. **Market Risk & Volatility**: India VIX (`in.macro.capmarkets.india_vix`) levels and regime categorization.
3. **Corporate Fundamentals**: Aggregate corporate earnings per share growth and profit after tax (PAT) margins (`in.macro.capmarkets.corporate_earnings_growth`).
4. **Institutional Liquidity**: Domestic Institutional Investor (DII) & Mutual Fund net equity inflows (`in.macro.capmarkets.dii_mutual_fund_flows`) and primary market mobilization.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.capmarkets.nifty_50` | NIFTY 50 Benchmark Index | Points | Daily | NSE |
| `in.macro.capmarkets.india_vix` | India VIX Volatility Index | Points | Daily | NSE |
| `in.macro.capmarkets.corporate_earnings_growth` | Corporate Earnings (EPS/PAT) Growth | % YoY | Quarterly | NSE / BSE |
| `in.macro.capmarkets.dii_mutual_fund_flows` | DII & Mutual Fund Inflows | INR Crore | Monthly | AMFI / SEBI |

## Standard Analytical Guidelines
- **Volatility Regimes**:
  - $< 15.0$: Low Risk / Complacent market conditions.
  - $15.0 - 22.0$: Normal historical risk regime.
  - $> 22.0$: High Risk / Risk-off regime (correlated with currency depreciation and foreign portfolio outflows).
- **Domestic Absorption Buffer**: Track monthly DII/SIP inflows to determine domestic institutional absorption of foreign portfolio investor (FPI) selling.
- **Valuation Premium**: Compare NIFTY 50 trailing P/E against the 10-year mean ($21.5\text{x}$) to evaluate valuation stretch.

## FastMCP Tools (`capital_markets_mcp`)
- `get_equity_snapshot(include_source_metadata)`: Fetches NIFTY 50 / SENSEX levels via live market API. Returns explicit error if unavailable.
- `get_vix_snapshot(include_source_metadata)`: Fetches India VIX regime classification via live API. Returns explicit error if unavailable.
- `get_earnings_snapshot(include_source_metadata)`: Fetches aggregate corporate earnings via live disclosures. Returns explicit error if unavailable.
- `get_primary_market_snapshot(include_source_metadata)`: Fetches IPO and debt mobilization stats via live disclosures. Returns explicit error if unavailable.
- `get_mf_flows_snapshot(include_source_metadata)`: Fetches mutual fund and DII net equity flows via live AMFI disclosures. Returns explicit error if unavailable.
