# External Sector Agent (`external_sector`)

A specialized, evidence-grounded macroeconomic intelligence agent for India's balance of payments, foreign exchange reserves, international trade, currency exchange rates, cross-border remittances, external debt, and real-time market intelligence.

---

## 1. Domain Scope & Core Responsibilities

The **External Sector Agent** is the **exclusive canonical owner** of cross-border financial flows, sovereign foreign exchange reserves, international trade balances, and external debt solvency for the Indian economy.

It addresses the 6 core pillars of external sector intelligence:

### 1. International Trade & Trade Balance
- **Merchandise Trade**: Exports, imports, and trade balance/deficit (in USD Billion and ₹ Crore).
- **Composition Analysis**: Oil vs. Non-Oil imports/exports, electronics, gems & jewellery, and critical capital goods.
- **Services Trade**: Services exports, imports, and net invisibles surplus offsetting the goods trade deficit.
- **Import Dependency**: Exposure to global Brent crude oil prices and supply chain vulnerabilities.
- **Terms of Trade**: Export-to-import price indices and purchasing power of exports.

### 2. Balance of Payments (BoP) Analysis
- **Current Account Balance & CAD**: Current Account Deficit in USD Billion and as a % of GDP.
- **Components**: Merchandise balance, net services surplus, primary income (investment returns), and secondary income (remittances).
- **Capital & Financial Account**: Net Foreign Direct Investment (FDI), Foreign Portfolio Investment (FPI), External Commercial Borrowings (ECBs), and banking capital.
- **Financing Patterns**: Sustainability of capital inflows covering the external financing requirement.

### 3. Foreign Exchange Reserves & External Liquidity
- **Total Forex Reserves**: Official weekly stock in USD Million / Billion and ₹ Crore.
- **Reserve Composition**: Foreign Currency Assets (FCA), Gold Reserves, Special Drawing Rights (SDRs), and Reserve Tranche Position (RTP) in the IMF.
- **Import Cover**: Months of merchandise and services imports covered by reserves (adequacy benchmark: > 10 months).
- **Short-Term Debt Coverage**: Ratio of forex reserves to short-term external debt (Guidotti-Greenspan rule).
- **Reserve Trajectory**: Weekly and monthly reserve accumulation/depletion trends.

### 4. Exchange Rate & External Competitiveness
- **Spot Exchange Rates**: Official RBI reference rates and live spot rates for USD/INR, EUR/INR, GBP/INR, and JPY/INR.
- **Effective Exchange Rates**: 40-currency basket Real Effective Exchange Rate (REER) and Nominal Effective Exchange Rate (NEER).
- **Volatility & Pass-Through**: Currency depreciation rates and imported inflation impacts (crude oil to domestic prices).
- **Competitiveness Caveats**: Valuation assessment without taking over monetary policy analysis or duplicating capital market feeds.

### 5. Remittances & Cross-Border Income Flows
- **Private Remittances**: Inward personal transfers and workers' remittances (receipts, payments, and net USD Million).
- **Secondary Income**: Contribution of private remittances to cushioning the Current Account Deficit.
- **Services Invisibles**: Software exports, business services, travel, and transportation receipts.

### 6. External Capital Flows & External Debt
- **External Debt Stock**: Total external debt (USD Billion and ₹ Crore), General Government sovereign debt vs. commercial debt.
- **Maturity Structure**: Short-term debt vs. long-term debt, refinancing exposures, and debt-to-GDP ratios.
- **BoP Capital Flows**: FDI net inflows, BoP-reported portfolio flows, and NRI deposit balances.

---

## 2. Multi-Layered Official Data Architecture

All empirical data is retrieved through verified official endpoints with automatic fallback to a local DuckDB cache:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        External Sector Client                          │
├─────────────────┬───────────────────┬────────────────┬─────────────────┤
│  RBI DBIE CDN   │   MoSPI MCP API   │ Yahoo Finance  │   Tavily Search │
│  & REST Tables  │ (eSankhyiki 'RBI')│ Live Spot & Oil│ Breaking News   │
└────────┬────────┴─────────┬─────────┴────────┬───────┴────────┬────────┘
         │                  │                  │                │
         ▼                  ▼                  ▼                ▼
   Forex Reserves    Invisibles/Remit     USD/INR Spot     Breaking Context
   Trade Balance     External Debt        Brent Crude      Macro News &
   USD/INR Daily     Oil/Non-Oil Trade    Currency Basket  Policy Releases
         │                  │                  │                │
         └──────────────────┼──────────────────┘                │
                            ▼                                   │
              DuckDB Local Cache (Zero Stale)                   │
                            │                                   │
                            ▼                                   ▼
             Structured Pydantic Models ──► LLM Synthesis & Reasoning
```

### 1. Reserve Bank of India (RBI DBIE)
- **Forex Reserves CDN**: `https://dbie.rbihub.in/data/forex-reserves.json` (weekly high-frequency series).
- **Trade Balance Table**: `external_sector.r433_india_s_foreign_trade_us_dollars` (monthly merchandise trade).
- **Exchange Rates Table**: `external_sector.r575_exchange_rate` (daily spot reference rates).
- **REER / NEER Table**: `external_sector.inx_neer_reer_m_rn` (monthly 40-currency basket indices).

### 2. Ministry of Statistics and Programme Implementation (MoSPI eSankhyiki MCP)
- **MCP Server URL**: `https://mcp.mospi.gov.in/` (dataset `RBI`).
- **Invisibles & Remittances**: `sub_indicator_code=9` (Private transfers net, receipts, payments, non-factor services).
- **External Debt**: `sub_indicator_code=27` (External debt of India quarterly, General Government, total debt).
- **Oil vs Non-Oil Trade**: `sub_indicator_code=42` (Broad commodity composition of merchandise trade).
- **BoP Indicators**: `sub_indicator_code=22` (CAD to GDP, trade & invisibles ratios).

### 3. Live Market Data (`yfinance`)
- **Spot FX Tickers**: `INR=X` (USD/INR), `EURINR=X`, `GBPINR=X`, `JPYINR=X`.
- **Global Commodity Benchmark**: `BZ=F` (Brent Crude Oil in USD/barrel).

### 4. Real-Time Web Intelligence (`Tavily AI`)
- **API Endpoint**: `https://api.tavily.com/search` using `TVLY_KEY_1`.
- **Purpose**: Enriches official statistical releases with breaking geopolitical developments, Red Sea trade route updates, RBI FX intervention commentary, and global macro sentiment.

---

## 3. FastMCP Tool Interface

Exposed by `external_sector/mcp_server.py`:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_forex_reserves` | `lookback_weeks: int = 12` | Total reserves (USD Mn / ₹ Cr), FCA, Gold, SDRs, RTP, and import cover months. |
| `get_trade_balance` | `lookback_months: int = 12` | Merchandise exports, imports, oil vs non-oil trade, and trade deficit (USD Bn). |
| `get_balance_of_payments` | `lookback_quarters: int = 8` | Current Account Balance (% of GDP), Capital Account, and net BoP financing. |
| `get_exchange_rate_snapshot` | `lookback_months: int = 12` | Official USD/INR daily reference rates and 40-currency REER/NEER indices. |
| `get_live_market_rates` | *(None)* | Real-time spot FX rates (USD/INR, EUR/INR, GBP/INR, JPY/INR) and Brent crude oil. |
| `get_remittances_and_invisibles` | `lookback_years: int = 5` | Private remittances, worker transfers, gross receipts/payments, and services net. |
| `get_external_debt` | `lookback_quarters: int = 8` | External debt stock (USD Bn / ₹ Cr), sovereign debt, short-term debt to reserves. |
| `get_external_flows` | `lookback_months: int = 12` | Net Foreign Direct Investment (FDI) and Foreign Portfolio Investment (FPI) flows. |
| `get_realtime_external_intelligence` | `query: str` | Live macroeconomic web intelligence and breaking news synthesized via Tavily. |
| `get_imf_external_outlook` | `start_year: str, end_year: str` | Medium-term multilateral WEO projections for India's CAD (% GDP) and export growth. |

---

## 4. MCP Servers Comparative Analysis & Sector Assignments

| Candidate MCP | Protocol & Auth | Evaluated Capabilities | Strategic Sector Assignment | Rationale & Architectural Boundaries |
| :--- | :--- | :--- | :--- | :--- |
| **@cyanheads/imf-mcp-server** | Streamable HTTP (`https://imf.caseyjhand.com/mcp`)<br>**Zero Auth (Public)** | - **WEO**: Medium-term CAD/GDP projections (`BCA_NGDPD`), export growth (`TX_RPCH`)<br>- **BOP**: BPM6 standardized balance of payments<br>- **IL / IFS**: International Liquidity & SDR holdings<br>- **EER**: 60-country REER/NEER indices | **INTEGRATED INTO `external_sector`** | Direct, authoritative global multilateral benchmark for India's external solvency and medium-term balance of payments outlook. |
| **NSE Market Data MCP** | Streamable HTTP (`mcp.nseindia.in/cmmkt/mcp`)<br>**Zero Auth (Public)** | - **CM Market Live**: NIFTY 50 live index, stock quotes, gainers/losers<br>- **Bhavcopy**: 5-yr OHLCV, market breadth, turnover | **ASSIGNED TO `capital_market_sector`** | Single Source of Truth rule (`AGENTS.md`): `capital_market_sector` exclusively owns domestic equity indices, FII/DII stock market turnover, and domestic market breadth. External Sector deals with BoP capital flows and spot FX, not domestic equity ticks. |
| **mcp-india-stack** | Local FastMCP (`mcp_india_stack`)<br>**Zero Auth (Bundled)** | - **Validation**: GSTIN, PAN, Aadhaar, Voter ID, CIN, DIN<br>- **Lookups**: IFSC, Pincode, HSN/SAC<br>- **Calculators**: Income Tax, TDS, GST, EPF/ESIC | **ASSIGNED TO `fiscal_sector` & `finance_sector`** | Contains zero external trade, balance of payments, forex reserves, or external debt datasets. Belongs in domestic fiscal and banking sectors. |

---

## 5. Single Source of Truth & Cross-Sector Boundaries

| Domain | `external_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **FPI Flows** | Cross-border BoP net portfolio flow balance | **`capital_market_sector` owns:** Daily exchange-traded FII/DII net flows & NIFTY indices | Capital Markets tracks stock exchange turnover; External tracks cross-border BoP financial accounts. |
| **Rupee Liquidity** | Gross RBI dollar purchases/sales & forex intervention | **`monetary_sector` owns:** Net LAF systemic liquidity, Repo rate, M0/M3 money supply | External tracks currency stabilization; Monetary handles the domestic liquidity sterilization impact. |
| **Imported Price Pressure** | Global Brent crude price, USD/INR depreciation rate | **`prices_sector` owns:** Headline CPI, WPI Fuel & Power, Core inflation | External provides imported cost-push metrics to Prices via A2A. |
| **Domestic Bank Deposits** | NRI deposits and cross-border currency liabilities | **`finance_sector` owns:** Domestic commercial bank deposits, CASA, and credit deployment | Finance tracks domestic banking intermediation; External tracks cross-border NRI dollar deposits. |

---

## 6. Strict Provenance Chain & "No Source, No Answer" Policy

- **No Source, No Answer:** Every data point carries a full `Citation` metadata chain with the authoritative agency, document title, table reference, observation period, retrieval URL, and data freshness (`live` or `cached`).
- **Zero Hallucination:** No dummy, random, or hardcoded economic figures are permitted. If official endpoints and local DuckDB are unreachable, the tool returns a typed `UnavailableResponse` detailing the failure.

---

## 7. Verification & Testing

Run the full sector test suite:
```powershell
pytest backend/external_sector/tests/test_external_sector.py -v
```

All **21 comprehensive tests** pass (100% success rate), covering:
- Pydantic models for all 6 pillars, live market rates, Tavily intelligence, and IMF outlook.
- Live and mock parsers for DBIE tables and MoSPI eSankhyiki payloads.
- DuckDB schema migrations, sequence generation, and conflict resolution.
- Live market feeds (`yfinance`), real-time news retrieval (`Tavily`), and IMF SDMX 3.0 MCP client.
- FastMCP tool invocation (all 10 tools) and FastAPI REST routes.
