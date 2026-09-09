---
name: finance-sector-agent
description: Analytical workflows and protocol specifications for macro-financial stability, monetary transmission, fiscal sustainability, and foreign exchange buffers.
---

# Finance Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded interest rates, GDP levels, forex reserves, or debt-to-GDP percentages are strictly prohibited.
- **Live API Ingestion**: All financial metrics must be retrieved dynamically from live official APIs (e.g., RBI DBIE for repo/forex, MoSPI API for GDP growth, Ministry of Finance/CGA for debt statistics).
- **Explicit Error Handling**: If any live financial data feed is unavailable or returns an error, the agent/tool **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_FINANCE_API_UNAVAILABLE", "message": "Failed to fetch live finance sector data: <details>"}`). It must **never** fall back to fabricated numbers or hardcoded estimates.

## Domain Scope
Monitors macro-financial stability, fiscal buffers, and external liquidity resilience:
1. **Monetary Transmission**: Policy repo rate changes transmitting through the banking sector to commercial lending rates.
2. **Growth-Inflation Balancing**: Real GDP growth rate from MoSPI and Headline CPI against the RBI's target band.
3. **Fiscal Sustainability**: General Government Debt-to-GDP ratio (`in.macro.fiscal.debt_to_gdp`) and fiscal consolidation trajectories under the FRBM framework.
4. **External Liquidity**: Foreign Exchange Reserves (`in.macro.external.forex_reserves`) and import cover adequacy.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.monetary.repo_rate` | RBI Policy Repo Rate | % p.a. | Bi-monthly | RBI DBIE |
| `in.macro.prices.cpi_headline`| All India CPI Combined Headline | % YoY | Monthly | MoSPI |
| `in.macro.fiscal.debt_to_gdp` | General Government Debt-to-GDP | % of GDP | Annual | MoF / RBI |
| `in.macro.external.forex_reserves`| Foreign Exchange Reserves | Billion USD | Weekly | RBI DBIE |

## Standard Analytical Guidelines
- **Real Policy Rate Assessment**: Compute $\text{Repo Rate} - \text{Headline CPI Inflation}$. $> +1.50\%$ indicates tight policy; $< +0.50\%$ indicates accommodative policy.
- **Import Cover Benchmark**: Assess Forex reserves in terms of months of prospective merchandise imports (minimum prudential threshold: 8-10 months).
- **Fiscal Space**: Debt-to-GDP ratios $> 80\%$ limit countercyclical fiscal stimulus capacity.

## FastMCP Tools (`finance_sector_mcp`)
- `get_gdp_growth_snapshot(prices)`: Fetches Real GDP growth rate via live API. Returns explicit error if unavailable.
- `get_cpi_inflation_snapshot()`: Fetches Headline CPI via live API. Returns explicit error if unavailable.
- `get_repo_rate_snapshot()`: Fetches RBI Policy Repo Rate, SDF, MSF, and CRR via live API. Returns explicit error if unavailable.
- `get_debt_to_gdp_snapshot()`: Fetches General Government Debt-to-GDP ratio via live API. Returns explicit error if unavailable.
- `get_forex_reserves_snapshot()`: Fetches Foreign Exchange Reserves and import cover via live API. Returns explicit error if unavailable.
