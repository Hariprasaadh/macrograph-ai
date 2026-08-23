---
name: capital-markets-agent
description: Analytical workflows and protocol specifications for Indian equity indices, volatility regimes, corporate earnings, and institutional flows.
---

# Capital Markets Sector Macroeconomic Intelligence Skill

## Domain Scope
Analyzes Indian capital markets as a leading indicator of macroeconomic health:
1. **Benchmark Equities**: NIFTY 50 and SENSEX valuation multiples, returns, and momentum.
2. **Market Risk & Volatility**: India VIX levels and regime categorization ($<15$: Low Risk, $15-22$: Normal, $>22$: High Risk / Stress).
3. **Corporate Fundamentals**: Aggregate corporate earnings per share (EPS) growth and profit after tax (PAT) margins.
4. **Primary Market & Liquidity**: IPO count/mobilization, debt issuances, and Domestic Institutional Investor (DII) & Mutual Fund net flows.

## Standard Analytical Guidelines
- **Volatility Regimes**: Cross-correlate India VIX spikes with foreign portfolio capital outflows and INR currency depreciation.
- **Institutional Liquidity Support**: Analyze DII monthly net inflows as a domestic absorption buffer against global emerging market volatility.
- **FastMCP Tools**:
  - `get_equity_snapshot()`
  - `get_vix_snapshot()`
  - `get_earnings_snapshot()`
  - `get_primary_market_snapshot()`
  - `get_mf_flows_snapshot()`
