---
name: real-sector-agent
description: Specialized workflows, indicator definitions, and analytical protocols for analyzing the Indian Real Sector (GDP/GVA, IIP, Prices, Agriculture).
---

# Real Sector Macroeconomic Intelligence Skill

## Domain Scope
Analyzes the core physical productive sectors of the Indian economy:
1. **National Income & Output**: Real GDP (2011-12 base), Nominal GDP, Gross Fixed Capital Formation (GFCF).
2. **Industrial Activity**: Index of Industrial Production (IIP) Use-Based (Primary, Capital, Intermediate, Consumer Goods) and Manufacturing.
3. **Price Indices**: All India CPI Combined (Headline, Food, Core), Wholesale Price Index (WPI), RBI House Price Index (HPI).
4. **Agriculture & Rural Economy**: Foodgrain production, Yield per Hectare, Minimum Support Price (MSP) trends.

## Standard Analytical Guidelines
- **Statistical Benchmark**: Calculate 10-year rolling percentiles and Z-scores for IIP growth and CPI momentum.
- **Inflation Signal**: Evaluate whether Food CPI is diverging from Headline CPI (supply shock vs demand-pull).
- **Investment Momentum**: Track GFCF as a % of GDP to assess domestic capital expenditure cycles.
- **FastMCP Tools**:
  - `get_national_income_snapshot(start_date, end_date)`
  - `get_industry_snapshot(start_date, end_date)`
  - `get_prices_snapshot(start_date, end_date)`
  - `get_agriculture_snapshot(start_date, end_date)`
