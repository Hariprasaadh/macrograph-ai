# Monetary Policy Sector Agent (`monetary_sector`)

A specialized macroeconomic intelligence agent for Reserve Bank of India (RBI) monetary policy, policy rate corridor, systemic liquidity, and central bank money supply aggregates.

---

## 1. Domain Scope & Core Responsibilities

The **Monetary Policy Sector Agent** is the **exclusive owner** of sovereign monetary policy instruments and money supply in India.

It answers four fundamental macroeconomic questions:
1. **Policy Rate Stance:** What is the current policy repo rate, and how is the policy corridor bounded (SDF floor to MSF ceiling)?
2. **Systemic Liquidity:** Is the banking system in net surplus or deficit liquidity under the Liquidity Adjustment Facility (LAF)?
3. **Money Supply Dynamics:** How rapidly are reserve money (M0) and broad money (M3) expanding, and what drives currency in circulation?
4. **Policy Stance & Real Rates:** In conjunction with peer sectors via A2A, is monetary policy restrictive, neutral, or accommodative relative to real headline inflation?

---

## 2. Core Indicators Owned by this Sector

### 1. Policy Rates & Corridor
- **Policy Repo Rate (%)**: RBI benchmark lending rate.
- **Standing Deposit Facility (SDF Rate %)**: Floor of the policy corridor.
- **Marginal Standing Facility (MSF Rate %)**: Ceiling of the policy corridor.
- **Bank Rate (%)**: Long-term benchmark rate.
- **Reverse Repo Rate (%)**: Fixed reverse repo rate.

### 2. Statutory Reserve Ratios
- **Cash Reserve Ratio (CRR %)**: Percentage of NDTL banks must maintain in liquid cash with RBI.
- **Statutory Liquidity Ratio (SLR %)**: Mandatory percentage of NDTL in approved government securities.

### 3. Money Stock & Reserve Money Aggregates
- **Reserve Money (M0)**: Currency in Circulation (CIC) + Bankers' deposits with RBI + Other deposits with RBI.
- **Broad Money (M3)**: Currency with the public + Demand deposits + Time deposits with commercial banks.
- **Narrow Money (M1)**: Currency with the public + Demand deposits + Other deposits.
- **Money Multiplier**: Ratio of Broad Money (M3) to Reserve Money (M0).

### 4. Systemic Liquidity Operations
- **Daily Net LAF Liquidity**: Net absorption / injection by the RBI (₹ Crore).
- **Daily Weighted Average Call Money Rate (WACR %)**: Operating target of monetary policy.

---

## 3. Official Indian Data Sources (RBI DBIE)

All empirical data is retrieved from official **Reserve Bank of India (RBI)** publications via the **Reserve Bank Innovation Hub (RBIH) DBIE mirror** (`https://dev.dbie.rbihub.in` and `https://dbie.rbihub.in/data/`).

### Exact RBI DBIE Table Keys & JSON Endpoints

| Indicator | Official DBIE Table Reference | Frequency | Format |
| :--- | :--- | :--- | :--- |
| **Policy Rates & Reserve Ratios** | `financial_sector.r531_key_rates` | Policy cycle / Daily | Database Table API |
| **Reserve Money (M0)** | `financial_sector.r543_reserve_money` | Weekly / Monthly | Database Table API |
| **Money Stock (M1, M2, M3)** | `financial_sector.r541_money_stock_measures`<br>`financial_sector.r542_sources_of_money_stock` | Fortnightly / Monthly | Database Table API |
| **Daily Liquidity Operations** | `https://dbie.rbihub.in/data/liquidity-operations.json` | Daily | Curated Static JSON Mirror |
| **Call Money Rates (WACR)** | `https://dbie.rbihub.in/data/daily-call-money-rates.json` | Daily | Curated Static JSON Mirror |

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `monetary_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Commercial Bank Rates** | Sovereign policy rates (Repo, SDF, MSF, CRR) | **`finance_sector` owns:** Commercial bank lending rates (WALR, MCLR) and deposit rates (WADTDR) | Monetary **never** fetches commercial lending rates; receives transmission data from Finance via A2A. |
| **Inflation Metrics** | Real policy rate calculation (`Repo - CPI`) | **`prices_sector` owns:** Headline CPI, Core CPI, CFPI, WPI | Monetary **never** fetches or recomputes CPI; accepts official CPI from Prices via A2A. |
| **Government Borrowing** | Reserve ratios (CRR, SLR) and primary market liquidity | **`fiscal_sector` owns:** Central government borrowing target, fiscal deficit | Fiscal monitors sovereign debt issuance; Monetary assesses absorption capacity and liquidity impact. |
| **Exchange Market Operations** | Forex operations liquidity impact (RBI balance sheet) | **`external_sector` owns:** Forex reserves stock, USD/INR rate, BoP | External monitors dollar reserves; Monetary monitors the rupee liquidity sterilization impact. |

---

## 5. FastMCP Tool Interface

Exposed by `monetary_sector/mcp_server.py`:

1. `get_policy_rates(lookback_months: int = 12)`
   - Returns Repo rate, SDF, MSF, Bank rate, CRR, and SLR.
2. `get_money_supply_aggregates(lookback_months: int = 12)`
   - Returns M0, M1, M3, Currency in Circulation, and YoY growth rates.
3. `get_systemic_liquidity(lookback_days: int = 30)`
   - Returns daily net LAF liquidity position (surplus/deficit ₹ Cr) and Weighted Average Call Money Rate (WACR).

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any rate, percentage, or money stock volume without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from DBIE or DuckDB canonical store, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "monetary_sector",
  "source_authority": "Reserve Bank of India (RBI)",
  "document_title": "RBI DBIE - Key Rates & Policy Corridor",
  "table_reference": "financial_sector.r531_key_rates",
  "indicator_id": "in.macro.monetary.policy_repo_rate",
  "observation_period": "2026-08",
  "value": 6.50,
  "unit": "%",
  "url": "https://dev.dbie.rbihub.in/statistics?table=financial_sector.r531_key_rates"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `finance_sector`: Policy Repo Rate and corridor for calculating lending rate transmission lag.
  - To `capital_market_sector`: Policy stance and systemic liquidity for bond yield curve modeling.
  - To `external_sector`: Interest rate differentials for exchange rate pressure analysis.
- **Inbound (Consumes via A2A):**
  - From `prices_sector`: Headline CPI to determine real policy rate (`Repo - CPI`) and MPC mandate compliance.
  - From `finance_sector`: Commercial bank credit growth and WALR pass-through efficiency.
  - From `real_sector`: Output gap and GDP growth momentum.
