---
name: monetary-banking-agent
description: Analytical workflows and protocol specifications for RBI monetary policy, repo rate changes, bank credit expansion, and liquidity transmission.
---

# Monetary & Banking Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded policy rates, spreads, or dummy bank credit numbers are strictly forbidden.
- **Live API Ingestion**: All policy rates (Repo, SDF, MSF, CRR, SLR) and credit growth statistics must be fetched dynamically from live official endpoints (e.g., RBI DBIE database, RBI policy press releases, Scheduled Commercial Bank returns).
- **Explicit Error Handling**: If live monetary or credit data cannot be retrieved, the tool/agent **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_MONETARY_API_UNAVAILABLE", "message": "Failed to fetch live monetary metrics from RBI DBIE: <details>"}`). Under no circumstances should fabricated numbers or hardcoded fallbacks be returned.

## Domain Scope
Analyzes the central bank monetary policy stance, commercial banking system liquidity, and credit allocation:
1. **Policy Rates & Corridor**: RBI Policy Repo Rate (`in.macro.monetary.repo_rate`), Standing Deposit Facility (SDF, `in.macro.monetary.standing_deposit_facility`), Marginal Standing Facility (MSF), and Bank Rate.
2. **Statutory Requirements**: Cash Reserve Ratio (CRR, `in.macro.monetary.cash_reserve_ratio`) and Statutory Liquidity Ratio (SLR).
3. **Credit Expansion**: Scheduled Commercial Banks Non-Food Credit Growth (`in.macro.monetary.bank_credit_growth`).

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.monetary.repo_rate` | RBI Policy Repo Rate | % p.a. | Bi-monthly | RBI DBIE |
| `in.macro.monetary.standing_deposit_facility` | Standing Deposit Facility | % p.a. | Bi-monthly | RBI DBIE |
| `in.macro.monetary.cash_reserve_ratio` | Cash Reserve Ratio | % of NDTL | Bi-monthly | RBI DBIE |
| `in.macro.monetary.bank_credit_growth` | Commercial Bank Credit Growth | % YoY | Fortnightly | RBI DBIE |

## Standard Analytical Guidelines
- **Real Policy Rate**: $\text{Real Repo Rate} = \text{Policy Repo Rate} - \text{Headline CPI Inflation}$.
  - $> +1.50\%$: Restrictive / Hawkish.
  - $+0.50\% \text{ to } +1.50\%$: Neutral stance.
  - $< +0.50\%$: Accommodative stance.
- **Monetary Transmission Lag**: Changes in the policy repo rate typically transmit to bank lending rates (MCLR/EBLR) over $1-3$ months and to broader aggregate demand over $3-6$ months.
- **Credit-Deposit Spread**: Monitor non-food credit growth relative to aggregate deposit growth to assess liquidity friction.

## FastMCP Tools (`monetary_sector_mcp`)
- `get_repo_rate_snapshot(params)`: Fetches RBI Policy Repo Rate via live API. Returns explicit error if unavailable.
- `get_credit_growth_snapshot(params)`: Fetches Scheduled Commercial Banks credit growth YoY via live API. Returns explicit error if unavailable.
