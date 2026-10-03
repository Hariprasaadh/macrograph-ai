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

All empirical data is retrieved through the official **RBIH DBIE MCP** package:
[`@reserve-bank-innovation-hub/dbie-mcp`](https://github.com/Reserve-Bank-Innovation-Hub/dbie.rbihub.in/tree/main/mcp).
The package is launched over stdio with Node.js 20+ and `npx`; it is not an HTTP MCP endpoint.
Its documented tools are `search_tables`, `list_tables`, `get_series`, and `get_table`.

The implementation discovers tables through the MCP catalogue and uses `get_table` for these verified published tables:

| Application function | Verified DBIE table title | Published path returned by MCP | Observed response data |
| :--- | :--- | :--- | :--- |
| `get_policy_rates` | Select Economic Indicators (RBI Bulletin Table 1) | `/banking/select-economic-indicators` | Monthly rows with policy repo, reverse repo, SDF, MSF, bank rate, CRR, and SLR fields |
| `get_money_supply` | Money Stock Measures (RBI Bulletin Table 6) | `/banking/money-stock-measures` | Dated rows with a nested `values` object; unit is Rupees crores |
| `get_system_liquidity` | Liquidity Operations by RBI (RBI Bulletin Table 3) | `/banking/liquidity-operations` | Dated operation components; unit is Rupees Crores |
| `get_monetary_stance_snapshot` | Derived only from sourced policy-rate observations | Uses the policy-rate table citation | Unsupported stance, real-rate, M3-growth, and net-liquidity fields remain unavailable |

`get_table` returns JSON in an MCP text content item, including `source`, `note`, and a `data` object. The monetary client retains the returned source note, source base, table path, units, frequency when published, observation period, and raw row values in citation metadata.

The source note explicitly states that values reflect the DBIE deployment's **last scrape**, not real-time data. The client labels them `upstream_snapshot`; it does not call them live.

### Runtime requirement

Node.js 20+ and `npx` must be available to the backend runtime. The client invokes the pinned official MCP package version `0.1.0`. If it cannot start or return a valid response, the client logs the failure and falls back to validated DuckDB rows. No direct DBIE HTTP endpoint or non-official source is used.

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
2. `get_money_supply(lookback_months: int = 12)`
   - Returns reported money-stock components and aggregates (M1, M2, M3). Unreported values and growth rates remain null.
3. `get_system_liquidity(lookback_months: int = 6)`
   - Returns reported RBI operation components. It does not derive a net LAF amount or surplus/deficit label.
4. `get_monetary_stance_snapshot()`
   - Returns a sourced policy-rate snapshot. An official stance label, real policy rate, M3 growth, and net liquidity status are not inferred.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any rate, percentage, or money stock volume without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from DBIE or DuckDB canonical store, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "monetary_sector",
  "source_authority": "Reserve Bank of India (RBI)",
  "document_title": "Select Economic Indicators (Monthly), RBI Bulletin Table 1",
  "table_reference": "/banking/select-economic-indicators",
  "observation_period": "Jul 2026",
  "freshness": "upstream_snapshot",
  "source_base_url": "https://dbie.rbihub.in",
  "source_note": "Data is from https://dbie.rbihub.in and reflects its last scrape of the RBI DBIE portal"
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
