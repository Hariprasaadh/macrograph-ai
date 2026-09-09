---
name: external-sector-agent
description: Analytical workflows and protocol specifications for foreign exchange reserves, import cover adequacy, USD/INR spot exchange rates, and merchandise trade balance.
---

# External Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded foreign exchange figures, mock exchange rates, or simulated trade deficits are strictly prohibited.
- **Live API Ingestion**: All external sector statistics must be fetched dynamically from live official APIs (e.g., RBI DBIE weekly FX reserves release, RBI reference rate feed, Ministry of Commerce trade portal).
- **Explicit Error Handling**: If live external sector data cannot be fetched or an endpoint fails, the tool/agent **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_EXTERNAL_API_UNAVAILABLE", "message": "Failed to fetch live external sector metrics from RBI/MoC: <details>"}`). It must **never** return fake or hardcoded reserves or currency values.

## Domain Scope
Monitors India's external trade balance, currency valuation, and foreign exchange reserves:
1. **Foreign Exchange Reserves**: Gross Foreign Exchange Reserves in Billion USD (`in.macro.external.forex_reserves`) and foreign currency assets (FCA).
2. **Exchange Rate Dynamics**: USD/INR Spot Reference Rate (`in.macro.external.usd_inr_exchange_rate`) and Real Effective Exchange Rate (REER 40-currency basket).
3. **Trade & Current Account**: Merchandise Trade Deficit (`in.macro.external.merchandise_trade_deficit`) and Current Account Deficit (CAD) as % of GDP.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.external.forex_reserves` | Foreign Exchange Reserves | Billion USD | Weekly | RBI DBIE |
| `in.macro.external.usd_inr_exchange_rate` | USD/INR Spot Reference Rate | INR per USD | Daily | RBI / Markets |
| `in.macro.external.merchandise_trade_deficit` | Merchandise Trade Deficit | Billion USD | Monthly | MoC |

## Standard Analytical Guidelines
- **Import Cover Buffer**: Foreign exchange reserves must cover at least $8-10$ months of projected imports to provide adequate insulation against global capital reversal shocks.
- **Current Account Sustainable Threshold**: CAD $\le 2.0-2.5\%$ of GDP is generally considered sustainable without debt financing stress.
- **Crude-Forex Sensitivity**: As India imports $> 85\%$ of its crude oil requirements, a $\$10/\text{barrel}$ rise in Brent crude expands the annual trade deficit by approximately $\$12-14\text{ billion}$, creating depreciatory pressure on USD/INR.

## FastMCP Tools (`finance_sector_mcp`)
- `get_forex_reserves_snapshot()`: Fetches Foreign Exchange Reserves and import cover buffers via live API. Returns explicit error if unavailable.
