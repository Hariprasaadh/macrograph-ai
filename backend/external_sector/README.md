# External Sector Agent (`external_sector`)

A specialized macroeconomic intelligence agent for India's balance of payments, foreign exchange reserves, currency exchange rates, foreign trade, and external debt.

---

## 1. Domain Scope & Core Responsibilities

The **External Sector Agent** is the **exclusive owner** of cross-border financial flows, sovereign foreign exchange reserves, and international trade balance for the Indian economy.

It answers four fundamental macroeconomic questions:
1. **Forex Buffer & Adequacy:** What is the current stock of India's foreign exchange reserves (in USD billions and months of import cover)?
2. **External Vulnerability:** What is the trajectory of the Current Account Deficit (CAD as % of GDP) and Balance of Payments (BoP)?
3. **Currency & Competitiveness:** How is the Indian Rupee (INR) moving against the US Dollar and other major currencies, both nominally and in trade-weighted terms (NEER/REER)?
4. **Trade Balance Dynamics:** How are merchandise exports/imports (oil vs non-oil) and software/services exports performing?

---

## 2. Core Indicators Owned by this Sector

### 1. Foreign Exchange Reserves (Stock & Composition)
- **Total Forex Reserves (USD Billion)**.
- **Foreign Currency Assets (FCA)**.
- **Gold Reserves**.
- **Special Drawing Rights (SDRs)** & **Reserve Tranche Position (RTP)** in the IMF.
- **Import Cover**: Ratio of reserves to monthly goods & services imports.

### 2. Balance of Payments (BoP)
- **Current Account Balance (USD Million & % of GDP)**: Merchandise trade deficit offset by services surplus and secondary income (remittances).
- **Capital Account Balance**: Foreign Direct Investment (FDI net), Foreign Portfolio Investment (FPI net), External Commercial Borrowings (ECBs).
- **Net BoP (Change in reserves on BoP basis)**.

### 3. Currency & Exchange Rates
- **Spot Exchange Rates**: USD/INR, EUR/INR, GBP/INR, JPY/INR (RBI Reference Rates).
- **Nominal Effective Exchange Rate (NEER)** (40-currency basket).
- **Real Effective Exchange Rate (REER)** (40-currency basket trade-weighted).

### 4. Foreign Trade & External Debt
- **Merchandise Trade**: Oil vs Non-Oil Exports and Imports (USD and INR).
- **Services Trade**: Net services export surplus.
- **External Debt**: Sovereign vs non-sovereign debt, short-term debt to total reserves ratio, NRI deposits.

---

## 3. Official Indian Data Sources (Dual Layer: DBIE + MoSPI MCP)

All empirical data is retrieved from official **Reserve Bank of India (RBI)** and **Ministry of Statistics and Programme Implementation (MoSPI)** endpoints.

### 1. RBI DBIE Mirror (Weekly & Daily High-Frequency Series)

| Indicator | Official DBIE Table Reference | Frequency | Endpoint / Format |
| :--- | :--- | :--- | :--- |
| **Forex Reserves** | `external_sector.r574_foreign_exchange_reserves` | Weekly | `https://dev.dbie.rbihub.in/statistics?table=external_sector.r574_foreign_exchange_reserves` |
| **Exchange Rates** | `external_sector.r575_exchange_rate` | Daily | `https://dev.dbie.rbihub.in/statistics?table=external_sector.r575_exchange_rate` |
| **Current Account** | `external_sector.r580_invisibles`<br>`external_sector.r578_balance_of_payments` | Quarterly | Database Table API |

### 2. MoSPI eSankhyiki MCP Server (`RBI` Dataset)

The **eSankhyiki MCP Server** (`https://mcp.mospi.gov.in/`) exposes 39 official external indicators under dataset `RBI`:

| Indicator | MoSPI Sub-Indicator Code / Key | Description |
| :--- | :--- | :--- |
| **BoP Indicators** | `sub_indicator_code=22` | Balance of Payments overall indicators |
| **Merchandise Trade (USD)** | `sub_indicator_code=42` | Oil and Non-Oil Exports/Imports in US Dollars |
| **Merchandise Trade (INR)** | `sub_indicator_code=24` | Oil and Non-Oil Exports/Imports in Rupees |
| **Direction of Trade** | `sub_indicator_code=11` | Direction of foreign trade by country group |
| **Exchange Rate Series** | `sub_indicator_code=31`, `32`, `35` | Financial and calendar year average rates, monthly high/low |

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `external_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Domestic Bank Deposits** | NRI deposits and cross-border currency liabilities | **`finance_sector` owns:** Domestic commercial bank deposits, CASA, and credit deployment | Finance tracks domestic banking intermediation; External tracks cross-border dollar flows. |
| **Rupee Liquidity** | Gross dollar purchases/sales by RBI (forex intervention) | **`monetary_sector` owns:** Net LAF systemic liquidity, Repo rate, M0/M3 money supply | External assesses currency stabilization; Monetary handles the rupee sterilization impact. |
| **Domestic Industry Capex** | External Commercial Borrowings (ECBs) | **`real_sector` owns:** National GDP, Gross Fixed Capital Formation (GFCF) | External supplies external debt financing data to Real Sector via A2A. |
| **Imported Price Pressure** | Global crude prices, exchange rate depreciation rate | **`prices_sector` owns:** Headline CPI, WPI Fuel & Power, Core inflation | External provides imported inflation pressure metrics to Prices via A2A. |

---

## 5. FastMCP Tool Interface

Exposed by `external_sector/mcp_server.py`:

1. `get_forex_reserves(lookback_weeks: int = 12)`
   - Returns Total Reserves (USD Billion), Foreign Currency Assets, Gold, SDRs, and RTP.
2. `get_exchange_rates(currency: str = "USD", lookback_days: int = 30)`
   - Returns daily spot exchange rates and percentage appreciation/depreciation.
3. `get_balance_of_payments(lookback_quarters: int = 8)`
   - Returns Current Account Deficit (USD Million & % of GDP), Capital Account, and net BoP.
4. `get_merchandise_trade(lookback_months: int = 12)`
   - Returns Oil and Non-Oil Exports, Imports, and Trade Deficit.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any forex reserve figure, exchange rate, or trade deficit amount without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock values. If an indicator cannot be fetched from DBIE or MoSPI MCP, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "external_sector",
  "source_authority": "Reserve Bank of India (RBI) / MoSPI",
  "document_title": "RBI DBIE - Foreign Exchange Reserves Weekly Statistical Supplement",
  "table_reference": "external_sector.r574_foreign_exchange_reserves",
  "indicator_id": "in.macro.external.forex_reserves_total_usd",
  "observation_period": "2026-09-18",
  "value": 704.88,
  "unit": "USD Billion",
  "url": "https://dev.dbie.rbihub.in/statistics?table=external_sector.r574_foreign_exchange_reserves"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `monetary_sector`: Forex intervention volumes to evaluate rupee liquidity sterilization needs.
  - To `prices_sector`: Rupee depreciation rate and imported commodity price pressure.
  - To `fiscal_sector`: Sovereign external debt servicing costs and customs tariff impact.
- **Inbound (Consumes via A2A):**
  - From `monetary_sector`: Domestic interest rates to evaluate interest rate parity (US Fed vs RBI repo).
  - From `real_sector`: Nominal GDP to express Current Account Deficit as a percentage of GDP (`CAD / GDP`).
