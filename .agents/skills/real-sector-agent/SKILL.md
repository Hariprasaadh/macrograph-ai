---
name: real-sector-agent
description: Workflows, indicator definitions, and analytical protocols for analyzing the Indian Real Sector (Real/Nominal GDP, IIP, GFCF Investment, Manufacturing).
---

# Real Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded, synthetic, or dummy values are strictly forbidden across all agent workflows, data clients, and MCP tools.
- **Live API Ingestion**: All economic observations, indicator levels, and statistics must be retrieved dynamically from live official APIs (e.g., MoSPI API, e-Sankhyiki, RBI).
- **Explicit Error Handling**: If a live API endpoint is unreachable, down, or returns invalid data, the agent/tool **must return an explicit structured error** (`{"status": "error", "error_code": "LIVE_API_UNAVAILABLE", "message": "Failed to fetch live real sector data from MoSPI API: <details>"}`). It must **never** fall back to fabricated numbers or hardcoded values.

## Domain Scope
Analyzes the core physical productive sectors of the Indian economy:
1. **National Income & Output**: Real GDP at Constant 2011-12 prices (`in.macro.real.gdp_growth`), Nominal GDP, Gross Fixed Capital Formation (`in.macro.real.gfcf_investment`).
2. **Industrial Activity**: Index of Industrial Production (`in.macro.real.iip_growth`), use-based classifications (Primary, Capital, Intermediate, Consumer Goods) and Manufacturing.
3. **Productive Capacity**: Gross Fixed Capital Formation (GFCF) as % of GDP to assess private and public capex cycle turnaround.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.real.gdp_growth` | Quarterly Real GDP Growth | % YoY | Quarterly | MoSPI |
| `in.macro.real.iip_growth` | IIP Industrial Production Growth | % YoY | Monthly | MoSPI |
| `in.macro.real.gfcf_investment`| Gross Fixed Capital Formation | % of GDP | Quarterly | MoSPI |

## Standard Analytical Guidelines
- **Statistical Benchmark**: Calculate 10-year rolling percentiles and historical Z-scores for IIP growth and GDP momentum.
- **Investment Cycle Tracking**: Evaluate GFCF % of GDP against historical capex thresholds ($>32\%$ indicates an expansionary investment cycle).
- **Manufacturing Health**: Correlate IIP Manufacturing with bank credit flow to industrial sectors and electricity generation.

## FastMCP Tools
- `get_national_income_snapshot(start_date, end_date)`: Fetches quarterly Real GDP, Nominal GDP, and GFCF via live data pipeline. Returns error if live source is unreachable.
- `get_industry_snapshot(start_date, end_date)`: Fetches IIP use-based indicators and manufacturing output via live data pipeline. Returns error if live source is unreachable.
