---
name: finance-sector-agent
description: Analytical workflows and protocol specifications for Indian monetary policy, banking system liquidity, fiscal deficit, and external sector reserves.
---

# Finance Sector Macroeconomic Intelligence Skill

## Domain Scope
Monitors macro-financial stability, monetary transmission, and fiscal buffers:
1. **Monetary Policy Stance**: RBI Policy Repo Rate, SDF, MSF, Bank Rate, CRR, SLR, and real policy rates ($\text{Repo} - \text{CPI}$).
2. **Growth & Price Stability**: Real GDP growth rate from MoSPI and Headline CPI against RBI's $4.0\% \pm 2.0\%$ target band.
3. **Fiscal Sustainability**: General Government Debt to GDP ratio and fiscal consolidation trajectories.
4. **External Liquidity**: Foreign Exchange Reserves (Billion USD) and import cover adequacy.

## Standard Analytical Guidelines
- **Real Rate Assessment**: Compute real policy rate = $\text{Repo Rate} - \text{Latest Headline CPI Inflation}$. If $> +1.5\%$, policy is tight; if $< +0.5\%$, policy is accommodative.
- **External Buffer Health**: Assess Forex reserves against import requirements (benchmark: minimum 8-10 months of import cover).
- **FastMCP Tools**:
  - `get_gdp_growth_snapshot(prices)`
  - `get_cpi_inflation_snapshot()`
  - `get_repo_rate_snapshot()`
  - `get_debt_to_gdp_snapshot()`
  - `get_forex_reserves_snapshot()`
