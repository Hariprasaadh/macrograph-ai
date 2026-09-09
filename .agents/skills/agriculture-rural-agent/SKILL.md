---
name: agriculture-rural-agent
description: Analytical workflows and protocol specifications for foodgrain output, Minimum Support Prices (MSP), monsoon departure, and rural demand indicators.
---

# Agriculture & Rural Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded crop outputs, dummy MSP increases, or synthetic monsoon figures are strictly forbidden.
- **Live API Ingestion**: All agricultural data must be dynamically fetched from live official feeds (e.g., Ministry of Agriculture Advance Estimates, Agmarknet wholesale mandi prices, IMD rainfall bulletins).
- **Explicit Error Handling**: If live agricultural data cannot be fetched or an endpoint fails, the agent/tool **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_AGRI_API_UNAVAILABLE", "message": "Failed to fetch live agricultural data: <details>"}`). It must **never** substitute fake numbers or hardcoded values.

## Domain Scope
Analyzes agricultural production, rural incomes, and food supply shocks:
1. **Physical Crop Output**: Total Foodgrain Production Volume (`in.macro.agri.foodgrain_production`) across Kharif and Rabi seasons.
2. **Support Pricing Policy**: Minimum Support Price (MSP) growth rates (`in.macro.agri.minimum_support_price_growth`) set by the Cabinet Committee on Economic Affairs (CCEA).
3. **Weather & Rainfall Dynamics**: IMD Southwest Monsoon Long Period Average (LPA) % Departure.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.agri.foodgrain_production` | Foodgrain Production Volume | Million Tonnes | Annual / Advance | MoA&FW |
| `in.macro.agri.minimum_support_price_growth` | Minimum Support Price Growth | % YoY | Seasonal | CACP / MoA&FW |

## Standard Analytical Guidelines
- **Monsoon Impact**: A monsoon departure $< -10\%$ from LPA signals deficient monsoon risk, triggering a downward revision in Kharif output and upward pressure on vegetable and cereal CPI with a $1-2$ quarter lag.
- **MSP Cost-Push Floor**: Increases in MSP above $6\%$ act as an effective floor for open-market agricultural procurement prices, lifting rural disposable income while elevating persistent food inflation.
- **Rural Demand Proxy**: Cross-correlate agricultural gross value added (GVA) growth with two-wheeler sales, tractor registrations, and FMCG rural volume growth.

## FastMCP Tools (`real_sector_mcp`)
- `get_agriculture_snapshot(start_date, end_date)`: Fetches foodgrain production volume, crop yields, and Minimum Support Prices (MSP) via live data pipeline. Returns explicit error if unavailable.
