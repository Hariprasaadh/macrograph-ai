---
name: causal-econometrics-agent
description: Workflows and methodologies for Structural Causal Modeling (SCM), 5-tier causal taxonomy, impulse response simulation, and Granger predictive causality testing.
---

# Causal Econometrics Agent Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: No hardcoded shock values, elasticity coefficients, or impulse trajectories may be injected without grounding in live empirical data or explicit user-defined scenario inputs.
- **Live Empirical Series**: Granger causality tests, stationarity transformations, and vector autoregressions must operate on time series retrieved from live data stores.
- **Explicit Error Handling**: If required time-series data cannot be fetched or degrees of freedom are insufficient, the engine **must return an explicit, structured error** (`{"status": "error", "error_code": "INSUFFICIENT_TIME_SERIES", "message": "Failed to fetch necessary live observation series for Granger causality test"}`).

## Domain Scope
Executes rigorous causal econometric inference and macroeconomic scenario simulations:
1. **5-Tier Causal Taxonomy Enforcement**: Categorizes transmission links into `THEORY`, `STATISTICAL_ASSOCIATION`, `LAGGED_RELATIONSHIP`, `GRANGER_PREDICTIVE`, and `STRUCTURAL_CAUSAL_MODEL`.
2. **Impulse Response Scenario Simulation**: Propagates exogenous shocks (e.g. Brent crude $+20\%$, Repo rate $-50\text{ bps}$) along directed causal transmission pathways with multi-period horizon forecasts.
3. **Statistical Predictive Causality**: Executes bivariate Granger causality $F$-tests on stationary time series, evaluating $p$-values and optimal lag lengths $k \in [1, 12]$.

## 5-Tier Classification Rules
- **Tier 1: `THEORY`**: Standard economic theory consensus from academic literature.
- **Tier 2: `STATISTICAL_ASSOCIATION`**: Contemporaneous Pearson/Spearman correlation ($p < 0.05$).
- **Tier 3: `LAGGED_RELATIONSHIP`**: Cross-correlation peaking at lag $k \ge 1$ months.
- **Tier 4: `GRANGER_PREDICTIVE`**: Past values of $X$ contain statistically significant predictive information about future $Y$ beyond past values of $Y$ alone ($F\text{-test } p < 0.05$).
- **Tier 5: `STRUCTURAL_CAUSAL_MODEL`**: Explicit DAG/SCM with identified causal mechanisms and bounded assumptions.

## Simulation API
- `POST /api/v1/simulate`:
  ```json
  {
    "scenario_name": "Crude Oil Shock (+20%)",
    "shock_variable": "in.macro.prices.brent_crude",
    "shock_magnitude": 20.0,
    "horizon_periods": 4
  }
  ```
- Returns: Baseline values, shocked forecast paths, transmission lags, and traversed causal relation IDs.
