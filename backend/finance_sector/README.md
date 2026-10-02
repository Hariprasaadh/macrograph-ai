# Finance & Banking Sector Agent (`finance_sector`)

A specialized macroeconomic intelligence agent for the Indian commercial banking system, credit transmission, and balance sheet health.

---

## 1. Domain Scope & Core Responsibilities

The **Finance & Banking Sector Agent** focuses strictly on the health, credit intermediation, and interest rate transmission of India's **Scheduled Commercial Banks (SCBs)**.

It answers four fundamental macroeconomic questions:
1. **Credit Expansion:** Is commercial bank credit growing fast enough to support real economic activity, and where is credit flowing (Agriculture, Industry, Services, Retail)?
2. **Monetary Transmission:** How rapidly and completely are RBI repo rate adjustments passing through into real lending rates (WALR, MCLR) and deposit rates (WADTDR)?
3. **Banking Solvency & Asset Quality:** What is the trajectory of bad loans (GNPA, NNPA ratios) and capital buffers (CRAR) across Public, Private, and Foreign banks?
4. **Liquidity & Intermediation Stress:** Are commercial banks facing structural funding pressures, as reflected by the Credit-to-Deposit (CD) ratio and CASA share?

---

## 2. The 4 Core Sub-Domains

### 1. Bank Credit Growth & Deployment
- Total SCB Non-Food Gross Bank Credit (% YoY, fortnightly Form A).
- Sectoral credit deployment:
  - **Agriculture & Allied Activities** (priority target adherence).
  - **Industry** (Micro, Small, Medium, and Large Enterprises).
  - **Services** (Commercial Real Estate, Transport, Trade, NBFC lending).
  - **Personal / Retail Loans** (Housing, Vehicle, Unsecured Credit).

### 2. Asset Quality & Capital Adequacy
- **Gross NPA (GNPA)** and **Net NPA (NNPA)** ratios across bank groups (PSBs, Private Banks, Foreign Banks).
- **Capital to Risk-Weighted Assets Ratio (CRAR / Basel III)** and CET-1 buffers.
- Provision Coverage Ratio (PCR) trends.

### 3. Lending Rates & Policy Transmission
- **Weighted Average Lending Rate (WALR)** on fresh rupee loans.
- **Weighted Average Lending Rate (WALR)** on outstanding rupee loans.
- **1-Year Median MCLR** (Marginal Cost of Funds based Lending Rate).
- **Weighted Average Domestic Term Deposit Rate (WADTDR)** on fresh & outstanding deposits.
- **Lending Spread** over the policy repo rate (`WALR - Repo`).

### 4. Deposit Mobilization & CD Ratio
- Aggregate Commercial Bank Deposits (% YoY growth).
- **CASA (Current & Savings Account)** deposit ratio.
- **Credit-to-Deposit (CD) Ratio** and incremental CD dynamics.

---

## 3. Official Indian Data Sources (RBI DBIE)

All empirical data is retrieved from official **Reserve Bank of India (RBI)** publications via the **Reserve Bank Innovation Hub (RBIH) DBIE mirror** (`https://dev.dbie.rbihub.in` and `data-api.dbie.rbihub.in`) and the `@reserve-bank-innovation-hub/dbie-mcp` tool layer.

### Exact RBI DBIE Table Keys

| Pillar | Official RBI Publication & DBIE Table Identifier | Frequency | Primary Indicators |
| :--- | :--- | :--- | :--- |
| **Credit Growth** | • `financial_sector.r1130_food_non_food_credit_of_scheduled_commercial_banks`<br>• `financial_sector.r539_deployment_of_bank_credit_by_major_sectors`<br>• `financial_sector.r999_sectoral_deployment_of_non_food_gross_bank_credit_outstand` | Fortnightly / Monthly | Non-food gross credit, Agriculture, Industry, Services, Retail credit |
| **Asset Quality** | • `financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou`<br>• `financial_sector.r329_distribution_of_scheduled_commercial_banks_by_crar`<br>• `financial_sector.r332_scheduled_commercial_banks_ratios` | Annual / Half-Yearly (FSR) | Gross NPA %, Net NPA %, CRAR %, RoA, RoE |
| **Lending Rates** | • `financial_sector.r531_key_rates`<br>• *RBI Monthly Bulletin Current Statistics Table 44* | Monthly / Policy Cycle | Fresh WALR, Outstanding WALR, 1-Yr Median MCLR, WADTDR |
| **Deposits & CD** | • `financial_sector.r689_business_of_scheduled_banks`<br>• `financial_sector.r901_scheduled_commercial_banks_select_aggregates`<br>• `financial_sector.r937_business_of_scheduled_banks_in_india` | Fortnightly / Monthly | Aggregate Deposits (% YoY), Bank Credit, Credit-to-Deposit (CD) Ratio |
| **Household Debt & Indebtedness** | • **MoSPI MCP `NSS77`** (`module="aidis"`, NSS 77th Round All India Debt & Investment Survey) | Decennial / Periodic | Household debt, asset distribution, cash loans, institutional vs non-institutional borrowing |
| **Qualitative Context** | • **Qdrant Policy Corpus (RAG)** | As published | RBI Banking Supervision Circulars, FSR Risk Outlook, MPC Policy Minutes |

### Verified Live Retrieval Endpoints (Zero Auth, Zero API Keys)

Data retrieval is available through two complementary interfaces:

1. **Curated Static JSON Mirror (CloudFront CDN - High Speed):**
   - **Sectoral Credit Deployment:** `https://dbie.rbihub.in/data/bank-credit-by-sector.json` (Monthly credit to Agri, Industry, Services, Retail/Housing)
   - **Commercial Bank Survey:** `https://dbie.rbihub.in/data/commercial-bank-survey.json` (Fortnightly aggregate deposits, non-food credit, domestic credit)
   - **Business of Scheduled Banks:** `https://dbie.rbihub.in/data/business-of-scheduled-banks.json` (Fortnightly SCB aggregates & CD ratio components)
   - **Call Money & Rates:** `https://dbie.rbihub.in/data/daily-call-money-rates.json` (Daily weighted average money market rates)
   - **Liquidity Operations:** `https://dbie.rbihub.in/data/liquidity-operations.json` (Daily SDF, MSF, LAF injections/absorptions)

2. **Live Database Table API (Postgres REST API - 1,033 Tables):**
   - Base endpoint: `https://data-api.dbie.rbihub.in/api/tables/{schema}/{table}/rows`
   - **Gross & Net NPA Ratios (Bank Group-Wise):** `https://data-api.dbie.rbihub.in/api/tables/financial_sector/r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou/rows`
   - **Capital Adequacy (CRAR Distribution):** `https://data-api.dbie.rbihub.in/api/tables/financial_sector/r329_distribution_of_scheduled_commercial_banks_by_crar/rows`
   - **Key Rates (Historical & Current):** `https://data-api.dbie.rbihub.in/api/tables/financial_sector/r531_key_rates/rows`

---

## 4. Single Source of Truth & Boundary Rules

To avoid duplicate tools or conflicting numbers across sector agents:

| Domain | `finance_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Monetary & Policy Rates** | Commercial lending rates (WALR, MCLR) & deposit rates (WADTDR) | **`monetary_sector` owns:** Policy Repo Rate, Reverse Repo, SDF, MSF, CRR, SLR, M0/M1/M3, LAF liquidity | Finance **never** fetches Repo rate; receives it via A2A from Monetary to compute lending rate spreads. |
| **Equities & Securities** | Commercial bank balance sheet solvency (CRAR, CET-1, RoA) | **`capital_market_sector` owns:** NIFTY 50, NIFTY Bank index points, India VIX, corporate earnings, IPOs | Capital Markets analyzes bank equity market valuation; Finance analyzes actual bank balance sheet health and NPAs. |
| **Sovereign & Public Debt** | Commercial private credit to enterprises, MSMEs, and retail | **`fiscal_sector` owns:** Fiscal deficit, GST collections, Central Capex, Government Market Borrowing (G-Sec issuances) | Fiscal analyzes government debt; Finance analyzes bank credit flow to private economic agents. |
| **Macro Output & Industry** | Bank credit deployed to Industry (Large/Medium/MSME) & Services | **`real_sector` owns:** GDP, GVA, Index of Industrial Production (IIP), Gross Fixed Capital Formation (GFCF) | Finance supplies credit availability data to Real Sector via A2A; Real Sector evaluates actual physical output. |
| **External & Foreign Flow** | Domestic rupee credit and domestic commercial deposits | **`external_sector` owns:** BoP, Forex reserves, External Commercial Borrowings (ECBs), Current Account Deficit | External tracks cross-border dollar flows and foreign borrowings; Finance tracks domestic banking system intermediation. |

---

## 5. FastMCP Tool Interface (4 Clean Tools)

Exposed by `finance_sector/mcp_server.py`:

1. `get_bank_credit_growth(lookback_months: int = 12)`
   - Returns non-food credit growth and broad sectoral deployment (Agri, Industry, Services, Retail).
2. `get_asset_quality(bank_group: str = "ALL_SCB", lookback_quarters: int = 8)`
   - Returns GNPA ratio, NNPA ratio, and CRAR across bank groups.
3. `get_lending_and_deposit_rates(lookback_months: int = 12)`
   - Returns WALR (fresh and outstanding), 1-yr MCLR, WADTDR, and lending spread over repo.
4. `get_deposits_and_cd_ratio(lookback_months: int = 12)`
   - Returns aggregate deposit growth, CASA ratio, and Credit-to-Deposit (CD) ratio.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any financial metric, percentage, rate, or trend without explicitly stating its source.
- **Zero Hallucination / No Hardcoding:** Never hallucinate, estimate, or hardcode random/mock values as factual data. If a data point cannot be retrieved from DBIE or the verified DuckDB canonical store, the agent must return a structured `status: "unavailable"` error rather than inventing numbers.

### Citation Metadata Attached to Every Observation:
```json
{
  "source_agent": "finance_sector",
  "source_authority": "Reserve Bank of India (RBI)",
  "document_title": "RBI DBIE - Sectoral Deployment of Bank Credit",
  "table_reference": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
  "indicator_id": "in.macro.finance.bank_credit_growth",
  "observation_period": "2024-06",
  "value": 15.4,
  "unit": "% YoY",
  "url": "https://dev.dbie.rbihub.in/statistics?table=financial_sector.r539_deployment_of_bank_credit_by_major_sectors"
}
```

---

## 7. A2A Collaboration Protocols

- **Inbound (Consumes via A2A):**
  - From `monetary_sector`: Repo rate & policy stance (to measure lending rate pass-through).
  - From `prices_sector`: Headline CPI (to compute real lending rates).
  - From `real_sector`: GVA / GDP industrial output (to benchmark credit demand elasticity).
- **Outbound (Provides via A2A):**
  - To `monetary_sector`: Lending rate transmission lag (WALR responsiveness) and credit expansion pace.
  - To `capital_market_sector`: Underlying bank asset quality (GNPA, PCR) for financial stock valuation.
  - To `real_sector`: Credit flow into manufacturing, infrastructure, and MSME capital formation.
