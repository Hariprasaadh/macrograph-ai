---
name: fiscal-sector-agent
description: Analytical workflows and protocol specifications for Indian public finance, debt-to-GDP sustainability, central capex multipliers, and GST revenue trends.
---

# Fiscal Sector Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded fiscal deficit numbers, dummy tax collections, or synthetic debt ratios are strictly prohibited.
- **Live API Ingestion**: All public finance statistics must be fetched dynamically from live official portals (e.g., Controller General of Accounts monthly accounts, Ministry of Finance Union Budget portal, GSTN revenue releases).
- **Explicit Error Handling**: If live fiscal data cannot be fetched or an endpoint returns an error, the agent/tool **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_FISCAL_API_UNAVAILABLE", "message": "Failed to fetch live fiscal metrics from CGA/MoF: <details>"}`). It must **never** substitute fake numbers or hardcoded estimates.

## Domain Scope
Monitors the sovereign balance sheet, public debt dynamics, and fiscal stimulus:
1. **Public Debt Sustainability**: General Government Debt-to-GDP (`in.macro.fiscal.debt_to_gdp`) incorporating both Central and State liabilities.
2. **Quality of Spending**: Central Government Capital Expenditure Growth (`in.macro.fiscal.central_capex_growth`) vs. revenue expenditure.
3. **Revenue Buoyancy**: Gross Tax and GST revenue growth (`in.macro.fiscal.gross_tax_growth`) reflecting formal economic activity.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.fiscal.debt_to_gdp` | General Government Debt-to-GDP | % of GDP | Annual | MoF / RBI |
| `in.macro.fiscal.central_capex_growth` | Central Capex Growth | % YoY | Monthly / Annual | CGA / MoF |
| `in.macro.fiscal.gross_tax_growth` | Gross Tax Revenue Growth | % YoY | Monthly / Annual | CGA |

## Standard Analytical Guidelines
- **Capex Multiplier**: Capital spending has an estimated GDP multiplier of $2.5-4.8\text{x}$ over a 3-year horizon, compared to $< 1.0\text{x}$ for revenue expenditure.
- **Fiscal Glide Path**: Track Central Fiscal Deficit target progress toward the $4.5\%$ of GDP target by FY26 under FRBM guidelines.
- **Tax Buoyancy**: A tax buoyancy coefficient $> 1.0$ indicates that tax receipts are expanding faster than nominal GDP.

## FastMCP Tools (`finance_sector_mcp`)
- `get_debt_to_gdp_snapshot()`: Fetches General Government Debt-to-GDP ratio via live API. Returns explicit error if unavailable.
