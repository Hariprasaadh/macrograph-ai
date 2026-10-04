# Capital Markets Sector Agent — Macrograph-AI

A multi-agent Indian macroeconomic intelligence module for Capital Markets with a production-grade architecture combining **FastMCP** (agent-to-data retrieval), **A2A Protocol** (agent-to-agent reasoning), and a **DuckDB analytical data store**.

---

## 1. Domain Scope & Core Responsibilities

The Capital Markets Sector Agent is the **single source of truth** for Indian equity markets, volatility, institutional flows, listed corporate valuations, and capital-market-to-macroeconomy linkages.

| Domain Responsibility | Analytical Scope | Key Indicators | Authoritative Data Source |
| :--- | :--- | :--- | :--- |
| **1. Equity Market Performance** | Track and analyze Indian equity market movements, returns, and index trends. | NIFTY 50 (`^NSEI`), SENSEX (`^BSESN`), NIFTY 500, broad index returns | NSE India / BSE India / Yahoo Finance Provider Snapshot |
| **2. Market Volatility & Sentiment** | Measure uncertainty, investor risk appetite, and volatility regimes. | India VIX (`^INDIAVIX`), Volatility Regimes (Low <13, Normal 13-18, Elevated 18-24, High >24) | NSE India Volatility Index Feed |
| **3. Mutual Fund Flows** | Monitor domestic mutual fund investment activity, SIP inflows, and liquidity demand. | Equity MF net inflows (₹ Cr), Monthly SIP contributions (₹ Cr), Total Industry AUM (₹ Lakh Cr) | AMFI (Association of Mutual Funds in India) / `api.mfapi.in` |
| **4. Foreign Portfolio Investment (FPI)** | Analyze foreign institutional investment activity and domestic counter-flows. | FPI Gross Purchases, Sales, Net Equity Investment (₹ Cr & $ Mn), DII Net Investment | NSDL Fortnightly Archives / SEBI FPI Monitor |
| **5. Corporate Earnings & Valuation** | Assess listed-company earnings growth, profitability, and valuation multiples. | NIFTY 50 TTM EPS, P/E ratio, P/B ratio, Dividend Yield (%), PAT Growth YoY (%) | NSE Historical Valuation Factsheets & Results |
| **6. Market Liquidity & Breadth** | Evaluate market participation, liquidity depth, and advance-decline momentum. | Total traded volume (shares), Turnover (₹ Cr), Advances, Declines, Advance/Decline ratio | NSE Daily Bhavcopy & Market Breadth Summary |
| **7. Sectoral Market Performance** | Compare listed industry sectors to identify market leadership and capital rotation. | NIFTY Bank (`^NSEBANK`), NIFTY IT (`^CNXIT`), NIFTY Auto, NIFTY Pharma, NIFTY FMCG | NSE Sectoral Indices / Provider Snapshots |
| **8. Primary Capital Markets (IPOs)** | Monitor equity fundraising through IPOs, QIPs, and rights issues. | IPO issue count, IPO proceeds mobilized (₹ Cr), QIP proceeds, total equity raised | SEBI Monthly Bulletin: Primary Market Mobilization |
| **9. Market Structure & Participation** | Analyze investor demographics and retail vs. institutional participation. | Total Demat Accounts (CDSL + NSDL in Crores), Monthly additions (Lakhs), Retail cash turnover share (%) | SEBI / NSDL / CDSL Depository Statistics |
| **10. Market-Economy Linkages** | Examine transmission between capital markets and macroeconomic aggregates via A2A. | Equity Risk Premium (NIFTY Earnings Yield − 10Y G-Sec), Buffett Indicator (Market Cap to GDP %) | RBI DBIE SGL Yields (`r217`) + NSE Synthesis (A2A Boundaries Respected) |

---

## 2. Comprehensive Data Source & MCP Server Evaluation

To guarantee uninterrupted analytical capability, large coverage, and strict empirical validity, the Capital Markets Sector implements an evaluated multi-tier retrieval pipeline:

```
                        ┌────────────────────────────────────────────────────────┐
                        │               CAPITAL MARKETS SECTOR AGENT             │
                        └───────────────────────────┬────────────────────────────┘
                                                    │
     ┌──────────────────────────────────────────────┴──────────────────────────────────────────────┐
     │                               MULTI-SOURCE DATA RETRIEVAL LAYER                             │
     ├──────────────────────────┬───────────────────────────┬──────────────────────────────────────┤
     │   LIVE REAL-TIME TIER    │  OFFICIAL STATUTORY TIER  │        MCP PROTOCOL TIERS            │
     ├──────────────────────────┼───────────────────────────┼──────────────────────────────────────┤
     │ • Yahoo Finance Provider │ • RBI DBIE Catalog Tables │ • MoSPI MCP (https://mcp.mospi.gov.in)│
     │   (^NSEI, ^INDIAVIX,     │ • AMFI India Statutory    │ • IMF MCP (https://imf.caseyjhand.com)│
     │    ^NSEBANK, ^CNXIT)     │ • SEBI / NSDL Disclosures │ • mcp-india-stack (Offline + yfinance│
     │ • Zero IP blocks, 100% up│ • Statutory monthly lags  │ • indian-market-mcp / finstack-mcp   │
     └──────────────────────────┴───────────────────────────┴──────────────────────────────────────┘
                                                    │
                                      ┌─────────────▼─────────────┐
                                      │   DUCKDB ANALYTICAL STORE │
                                      │  • Parameterized queries  │
                                      │  • Upstream Snapshots     │
                                      │  • Verified Cached State  │
                                      └───────────────────────────┘
```

### In-Depth Empirical Evaluation of MCP Servers & Data Sources

| MCP Server / Source | Tools & Coverage | Empirical Verification & Performance | Limitations & Failure Modes | Architectural Role in Macrograph-AI |
| :--- | :--- | :--- | :--- | :--- |
| **`mcp-india-stack`** *(PyPI: `0.6.7`)* | 76 tools (identity, tax, banking, stocks) | Installed via `uv` in `.venv`. Fast offline-first lookup for IFSC, PAN, GSTIN, and built-in stock quotes via `yfinance`. | Offline datasets require background CDN sync for changes; stock tools rely on `yfinance`. | **Local Utility & Stock Verification Layer**: Integrated for fast symbol lookups and corporate compliance verification. |
| **`MoSPI MCP Server`** *(Govt of India)* | 4 core tools (`list_datasets`, `get_indicators`, `get_data`, `get_metadata`) | Verified live at `https://mcp.mospi.gov.in` via Streamable HTTP JSON-RPC. Direct access to 27 national statistical datasets (NAS/GDP, CPI, IIP, ASI, PLFS, RBI). | Read-only statistical aggregates; not intended for second-by-second equity ticks. | **Macro Linkage Verification Layer**: Validates GDP (`NAS`), Industrial Production (`IIP`), and National Accounts against market capitalization. |
| **`IMF MCP Server`** *(`@cyanheads`)* | 6 tools (`imf_list_databases`, `imf_get_database`, `imf_query_dataset`, etc.) | Verified live at `https://imf.caseyjhand.com/mcp` via Streamable HTTP. Keyless SDMX 3.0 queries across 190 countries with DuckDB DataCanvas staging. | Large global datasets can exceed single-call character budgets without DataCanvas. | **Cross-Border Capital & External Linkage Layer**: Provides global cross-border capital flows, BOP, and comparative emerging-market flows. |
| **`RBI DBIE`** *(Official Reserve Bank)* | Official Database of Indian Economy (14 Indicator Tables + 58 Financial Market Tables) | Authoritative public data catalog: `financial_markets.r1351_market_capitalisation_nse`, `r1354_net_investments_by_fiis`, `r1357_turnover_in_the_equity_derivatives`, `r1360_net_resources_mobilised_by_mutual_funds`, `yield_gov_sec_rn`. | Web pages protected by session tokens; automated direct scraping can face rate limits. | **Statutory Truth Baseline**: Primary canonical citation authority for sovereign G-Sec yields, FII net totals, and market capitalization. |
| **`indian-market-mcp`** *(Afthab VP)* | 68 tools (Equities, F&O, Option Chain, PCR, Max Pain, MF, IPO, SGB) | Rich options tools. However, empirical testing on Render (`https://indian-market-mcp-wweh.onrender.com/mcp`) shows underlying requests to `nseindia.com` fail with HTTP 403 Forbidden due to Akamai WAF. | NSE blocks cloud datacenter IPs aggressively (~3 req/min limit). | **Optional Sandbox Backend**: Excellent for local workstation broker connections (Angel One / Zerodha) with residential IPs. |
| **`finstack-mcp`** *(FinStack Labs)* | 95 tools (AI agent debate, AMFI fund flows, SEBI SAST filings, GST-to-stock) | High conceptual coverage; direct integration with AMFI `mfapi.in` and SEBI public filings. | Requires individual broker API credentials for real-time Level 2 depth. | **Benchmark for AMFI Flow Schemas & Sentiment Analysis**. |
| **`nse-mcp`** *(Jugaad Data)* | ~17 tools (Bhavcopy, live equity, derivatives, corporate announcements) | Clean Python `jugaad-data` wrapper for NSE archives and live equity. | Relies on direct scraping of `nseindia.com`, triggering HTTP 403 when executed in automated cloud environments. | **Reference Schema Provider** for NSE bhavcopy structures and advance-decline parsing. |
| **`Yahoo Finance Chart API`** | Global indices, historical OHLCV, volume, intraday bars | 100% uptime, zero rate limits, reliable historical depth for `^NSEI`, `^BSESN`, `^INDIAVIX`, `^NSEBANK`, `^CNXIT`. | Third-party aggregated snapshot rather than direct raw exchange tick stream. | **Primary Real-Time & Chart Feed**: Guaranteed high-availability provider for equity indices, volatility regimes, and sectoral performance. |
| **`AMFI India`** *(`api.mfapi.in` + Monthly Disclosures)* | 47,000+ schemes, monthly industry SIP & AUM disclosures | Statutory authority for Indian Mutual Funds. Unrestricted JSON API for scheme NAVs and official monthly releases. | Monthly industry-wide aggregate reports published with ~8-day lag. | **Primary Statutory Authority** for mutual fund net flows, SIP momentum, and domestic institutional liquidity. |

---

## 3. Strict Citation & Anti-Hallucination Policy

Macrograph-AI enforces an absolute, non-negotiable **"No Source, No Answer"** rule:
- **Zero Hallucination / No Mock Values:** The agent never invents, estimates, or hardcodes random numbers. If an upstream service is temporarily unreachable, it returns a structured unavailable status (`freshness: "unavailable"`) or verified canonical data labeled `freshness: "cached"`.
- **Complete Attribution Chain:** Every response, metric, and reasoning conclusion must output:
  1. `source_agent`: `"capital_market_sector"`
  2. `source_authority`: Official issuing agency (e.g. NSE, RBI DBIE, SEBI, AMFI, MoSPI)
  3. `document_title`: Specific report or publication title
  4. `table_reference`: Exact table or tool identifier (e.g., `financial_markets.r217_gsec_yields`, `amfi.monthly_fund_flows`)
  5. `retrieval_url`: Direct verification link or canonical endpoint
  6. `observation_period`: Observation date or reporting month (e.g., `2024-09` or `2024-09-30`)
  7. `freshness`: `live`, `upstream_snapshot`, `cached`, or `unavailable`

---

## 4. Analytical Intelligence: Explaining User Queries in Detail

A core tenet of the Capital Markets Sector is that **the agent must never simply dump raw numbers onto the screen**. Every user query must be analyzed, interpreted, and explained in clear, non-jargon macroeconomic context:

1. **Causal Mechanisms Over Data Dumps:**
   - Instead of stating *"NIFTY rose 0.8% while FPI sold ₹2,000 Cr"*, the agent explains: *"Indian equities decoupled from foreign selling due to domestic institutional counter-flows, driven by structural monthly SIP inflows of ₹24,500+ Cr, which absorb secondary market selling pressure."*
2. **Equity Risk Premium (ERP) & Asset Allocation:**
   - Interprets the spread between NIFTY Earnings Yield ($1 / PE$) and the 10-Year Indian G-Sec Yield (`financial_markets.yield_gov_sec_rn`).
   - If ERP is deeply negative, the agent explains why fixed income offers superior risk-adjusted yields and what that signals for corporate capital costs.
3. **Volatility Regime Contextualization:**
   - Classifies India VIX into defined regimes:
     - **Low (< 13):** Complacency or calm consolidation; option premiums are depressed.
     - **Normal (13 – 18):** Healthy market dynamics consistent with long-term baseline.
     - **Elevated (18 – 24):** Anticipation of major macro events (budget, election, RBI MPC, geopolitical shock).
     - **High (> 24):** Acute risk aversion, aggressive hedging, and potential liquidity dislocation.
4. **Sectoral Leadership & Capital Rotation:**
   - Evaluates whether rallies are broad-based or narrowly concentrated in defensive sectors (Pharma, FMCG) versus growth/cyclicals (Bank Nifty, Auto, IT).
5. **Cross-Sector A2A Boundaries:**
   - When answering macroeconomic linkages (e.g., impact of inflation or interest rates on equity multiples), the agent respects domain ownership: it draws CPI from `prices_sector`, repo rate from `monetary_sector`, and GDP growth from `real_sector` via A2A rather than recomputing them independently.

---

## 5. FastMCP Tools Reference

The sector exposes 12 FastMCP tools in `capital_market_sector/mcp_server.py`:

| Tool Name | Title | Parameters | Return Type | Data Source |
| :--- | :--- | :--- | :--- | :--- |
| `get_nifty_snapshot` | NIFTY 50 Snapshot | None | `NiftySnapshotResponse` | Yahoo Finance / NSE |
| `get_market_history` | Historical Valuations | `lookback_months: int = 12` | `MarketHistoryResponse` | NSE Factsheet / DuckDB |
| `get_india_vix` | India Volatility Index | `lookback_days: int = 30` | `IndiaVixResponse` | Yahoo Finance / NSE |
| `get_market_breadth` | NSE Market Breadth | None | `MarketBreadthResponse` | NSE Bhavcopy MCP |
| `get_gsec_yield_snapshot` | G-Sec Yield Curve | None | `GSecYieldResponse` | RBI DBIE Table `r217` |
| `get_mutual_fund_flows` | AMFI Mutual Fund Inflows | None | `MutualFundFlowsResponse` | AMFI Monthly Data |
| `get_fpi_equity_flows` | FPI & DII Investment | None | `FpiFlowsResponse` | NSDL / SEBI FPI Monitor |
| `get_corporate_earnings_valuation` | Listed Corporate Valuations | None | `CorporateEarningsResponse` | NSE Valuation Factsheet |
| `get_sectoral_performance` | Sectoral Rotation | None | `SectoralPerformanceResponse` | NSE Sectoral Indices |
| `get_primary_market_ipos` | Primary Market IPOs | None | `PrimaryMarketResponse` | SEBI Monthly Bulletin |
| `get_investor_participation` | Demat Account Growth | None | `InvestorParticipationResponse` | SEBI / NSDL / CDSL |
| `get_market_economy_linkages` | Equity Risk Premium (ERP) | None | `MarketEconomyLinkageResponse` | NSE & RBI DBIE Synthesis |

---

## 6. REST API Endpoints

The sub-application is mounted under `/capital-markets` on the main gateway:

```bash
# Health check
GET /capital-markets/health

# Domain metadata & owned indicators
GET /capital-markets/metadata

# Empirical indicator endpoints
GET /capital-markets/nifty-snapshot
GET /capital-markets/market-history?lookback_months=12
GET /capital-markets/india-vix?lookback_days=30
GET /capital-markets/market-breadth
GET /capital-markets/gsec-yields
GET /capital-markets/mutual-fund-flows
GET /capital-markets/fpi-flows
GET /capital-markets/corporate-earnings
GET /capital-markets/sectoral-performance
GET /capital-markets/primary-market-ipos
GET /capital-markets/investor-participation
GET /capital-markets/market-economy-linkages
```

---

## 7. A2A Protocol & Agent Card

The Capital Markets Sector Agent publishes an **Agent Card** at `/.well-known/agent.json` enabling autonomous discovery by the Orchestrator and peer sector agents:

- **Advertised Skills:**
  - `equity_market_analysis`: NIFTY 50 and equity index dynamics, returns, and multiples.
  - `volatility_sentiment_analysis`: India VIX volatility regimes, market sentiment, and breadth.
  - `institutional_flows_analysis`: AMFI mutual fund SIP inflows and NSDL/SEBI foreign portfolio investment.
  - `macro_market_linkages`: Equity Risk Premium (ERP), G-Sec yield curve slope, and cost of equity capital.

### Single-Source-of-Truth & A2A Boundary Rule
- If another sector agent requires NIFTY 50 returns, India VIX, or G-Sec yields, it **must** request them from `capital_market_sector` via A2A.
- Conversely, `capital_market_sector` **never** re-fetches or re-calculates GDP (owned by `real_sector`), CPI inflation (owned by `prices_sector`), or the Repo Rate (owned by `monetary_sector`). Cross-sector correlations are computed by consuming peer findings via A2A.

---

## 8. Quick Start & Verification

### Run the Demo
```powershell
# From the backend directory
cd backend
python demo_capital_market_sector.py
```
This tests all 12 FastMCP tools and executes an end-to-end A2A task synthesizing equity performance, volatility, institutional flows, and macro linkages into a structured markdown report.

### Run Tests
```powershell
# Run the Capital Market Sector test suite (27 tests)
pytest backend/capital_market_sector/tests/ -v

# Run the complete test suite
pytest backend/tests/ -v
```

---

## 9. Directory Structure

```
backend/capital_market_sector/
├── __init__.py
├── README.md                      # Sector architecture & domain documentation
├── agent.py                       # LangGraph reasoning node & service keywords
├── config.py                      # CapitalMarketSectorSettings
├── database.py                    # DuckDB connection & parameterized queries
├── database_seed.py               # Canonical baseline seed data
├── client.py                      # High-level client API & caching layer
├── mcp_server.py                  # FastMCP server exposing 12 domain tools
├── mcp_client.py                  # Client for external FastMCP servers
├── models.py                      # Pydantic v2 data models & citations
├── parsers.py                     # Parsers for G-Sec yields and market breadth
├── executor.py                    # A2A AgentExecutor implementation
├── data_sources/                  # Specialized retrieval submodules (<= 400 lines)
│   ├── __init__.py
│   ├── yahoo_data.py              # Yahoo Finance indices, VIX & sectoral chart parser
│   ├── amfi_data.py               # AMFI mutual fund & SIP flow fetcher
│   └── institutional_data.py      # FPI flows, earnings, IPOs, demat & ERP linkages
├── api/
│   └── app.py                     # FastAPI sub-application mounted at /capital-markets
└── tests/
    ├── test_capital_market_sector.py  # Models, DuckDB, FastMCP, and API tests
    ├── test_live_market_data.py       # Live & cached provider tests
    └── test_mcp_client.py             # FastMCP protocol & SSE tests
```
