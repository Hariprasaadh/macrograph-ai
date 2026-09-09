---
name: prices-inflation-agent
description: Analytical workflows and protocol specifications for Indian consumer price inflation (CPI), food inflation, wholesale prices (WPI), and crude oil pass-through.
---

# Prices & Inflation Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded, mock, synthetic, or dummy values are strictly forbidden across all agent workflows, price data clients, and MCP tools.
- **Live API Ingestion**: All price indices, commodity rates, and inflation statistics must be retrieved dynamically from live official APIs (e.g., MoSPI API for CPI, DPIIT/Office of Economic Adviser for WPI, live commodity APIs/Yahoo Finance for Brent Crude).
- **Explicit Error Handling**: If any live API endpoint cannot be reached or returns an error, the tool/agent **must immediately return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_PRICE_API_UNAVAILABLE", "message": "Failed to fetch live price data for <indicator>: <details>"}`). It must **never** substitute fake numbers or hardcoded values.

## Domain Scope
Analyzes price dynamics, inflationary pressures, and cost pass-through mechanisms across the Indian economy:
1. **Headline & Food CPI**: All India CPI Combined Headline (`in.macro.prices.cpi_headline`) and Consumer Food Price Index (`in.macro.prices.cpi_food`).
2. **Wholesale Pricing Pressure**: Wholesale Price Index All Commodities (`in.macro.prices.wpi_all`).
3. **Imported Commodity Pressure**: Brent Crude Oil Benchmark (`in.macro.prices.brent_crude`) spot pricing and domestic fuel pass-through.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.prices.cpi_headline` | All India CPI Combined Headline | % YoY | Monthly | MoSPI |
| `in.macro.prices.cpi_food` | Consumer Food Price Index | % YoY | Monthly | MoSPI |
| `in.macro.prices.wpi_all` | Wholesale Price Index All Commodities | % YoY | Monthly | OEA / DPIIT |
| `in.macro.prices.brent_crude` | Brent Crude Oil Benchmark | USD/barrel | Daily | EIA / Markets |

## Standard Analytical Guidelines
- **RBI Target Band Assessment**: Evaluate Headline CPI relative to the RBI's $4.0\% \pm 2.0\%$ target tolerance band ($2.0\% - 6.0\%$).
- **Food vs Headline Divergence**: Determine whether inflation is driven by transient perishables/food shocks (vegetables, pulses) or persistent generalized core inflation.
- **Pass-Through Elasticity**: An empirical $\$10/\text{barrel}$ persistent increase in Brent crude translates to an estimated $25-30\text{ bps}$ increase in headline CPI with a $1-2$ month lag via WPI and logistics channels.

## FastMCP Tools (`prices_sector_mcp`)
- `get_cpi_snapshot(params)`: Fetches All India CPI Combined Headline inflation via live API. Returns explicit error if unavailable.
- `get_wpi_snapshot(params)`: Fetches Wholesale Price Index all commodities inflation via live API. Returns explicit error if unavailable.
- `get_crude_oil_snapshot(params)`: Fetches Brent crude benchmark spot price via live API. Returns explicit error if unavailable.
