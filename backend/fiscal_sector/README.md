# Fiscal & Public Finance Sector Agent (`fiscal_sector`)

A specialized macroeconomic intelligence agent for Indian Government Finances, Union Budget, Sovereign Debt, and Taxation.

---

## 1. Domain Scope & Core Responsibilities

The **Fiscal & Public Finance Sector Agent** focuses strictly on the fiscal stance, budgetary accounts, sovereign debt sustainability, and tax mobilization of India.

It answers five fundamental macroeconomic questions:
1. **Fiscal Consolidation & Deficit Path:** Is the Government of India adhering to its fiscal consolidation roadmap (targeting below 4.5% of GDP by FY26), and what are the trajectories of the Fiscal Deficit, Revenue Deficit, and Primary Deficit?
2. **Quality of Fiscal Expenditure:** How is government expenditure partitioned between growth-enhancing **Capital Expenditure (Capex)** and operational **Revenue Expenditure**, and how does this affect gross fixed capital formation?
3. **Sovereign Debt Sustainability:** What is the consolidated **General Government Gross Debt-to-GDP** ratio under international standards (IMF WEO benchmarks) versus domestic FRBM recommendations?
4. **Tax Revenue Mobilization:** How resilient are direct taxes (Corporate & Personal Income Tax) and indirect taxes (**Monthly Gross GST Collections**), and how do product taxes bridge GVA to GDP?
5. **Tax Policy & Compliance Mechanics:** What are the exact mathematical breakdowns of GST (CGST/SGST vs IGST), GSTIN validation, and the structural trade-offs between the New and Old Income Tax regimes?

---

## 2. The 6 Core Sub-Domains (Pillars)

### 1. Union Budget Accounts & Fiscal Deficit
- **Revenue Receipts:** Net Tax Revenue to Centre and Non-Tax Revenue (dividends from RBI and PSUs).
- **Capital Receipts:** Non-debt capital receipts (disinvestment, loan recoveries).
- **Expenditure Thrust:** Capital Expenditure (Capex) vs Revenue Expenditure.
- **Deficit Indicators:** Fiscal Deficit (in ₹ Crore and as % of GDP), Revenue Deficit, and Primary Deficit.

### 2. Consolidated General Government Debt & Fiscal Balance (IMF WEO)
- **General Government Gross Debt (% of GDP)** across Central and State Governments.
- **General Government Net Lending/Borrowing (% of GDP)** according to IMF SDMX 3.0 / WEO standards.
- International comparability and sovereign creditworthiness benchmarks.

### 3. Goods & Services Tax (GST Collections)
- **Monthly Gross GST Collections** (₹ Crore).
- Sub-components: **CGST** (Central GST), **SGST** (State GST), **IGST** (Integrated GST on imports and inter-state trade), and **Compensation Cess**.
- Year-on-Year (**YoY %**) growth rates and buoyancy tracking.

### 4. MoSPI National Accounts Fiscal Aggregates
- **Net Taxes on Products** at current and constant (2011-12) prices (MoSPI NAS Indicator 2).
- **Taxes on Products** and **Subsidies on Products** (MoSPI NAS Indicators 3 & 4).
- **Government Final Consumption Expenditure (GFCE)** (MoSPI NAS Indicator 11).

### 5. Tax Policy & Regulatory Calculators
- **GST Split Calculator:** Mechanical, verified calculation of CGST + SGST (intra-state) or IGST (inter-state) with full CBIC statutory provenance.
- **GSTIN Validator:** Mod-36 checksum verification and issuing State/UT decoding.
- **Income Tax Regime Comparison:** Comparison between the New Regime (Finance Act FY 2025-26 / FY 2026-27 with ₹75k standard deduction and Section 87A rebate) and Old Regime.

### 6. Real-Time Fiscal & Budgetary Context
- Ministry of Finance official press releases and Gazette notifications.
- Controller General of Accounts (CGA) monthly fiscal updates and advance releases via Tavily AI.

---

## 3. Official Data Sources & FastMCP Integration

Data is retrieved via a multi-server MCP architecture:

| Pillar | Official Authority | Primary Protocol / MCP Server | Endpoint / Identifier |
| :--- | :--- | :--- | :--- |
| **Union Budget & Deficit** | Controller General of Accounts (CGA) / Ministry of Finance | Local FastMCP & Verified DuckDB Store | `cga.nic.in` & Union Budget at a Glance |
| **Sovereign Debt** | International Monetary Fund (IMF) | IMF SDMX 3.0 MCP Server (`imf.caseyjhand.com/mcp`) | Dataflow: `WEO` (Series: `IND.GGXWDG_NGDP.A`, `IND.GGXCNL_NGDP.A`) |
| **GST Collections** | GST Council / Ministry of Finance | PIB Official Releases & Verified DuckDB Store | Monthly Gross GST Revenue Releases |
| **Product Taxes & GFCE** | Ministry of Statistics and Programme Implementation (MoSPI) | MoSPI eSankhyiki FastMCP Server (`mcp.mospi.gov.in`) | Dataset: `NAS` (Indicators: 2, 3, 4, 11) |
| **Tax Calculation Rules** | CBIC & CBDT | `eco-policy-mcp` (Offline-first zero-auth engine) | CGST Act 2017 & Income Tax Act (Finance Act FY26) |
| **Real-time News** | Press Information Bureau (PIB) / MoF | Tavily AI Search Tool | `api.tavily.com` (PIB MoF filter) |

---

## 4. Single Source of Truth & Boundary Rules

To prevent conflicting figures across sector agents:

| Data Point | `fiscal_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Fiscal Deficit & Sovereign Debt** | Union Fiscal Deficit (% of GDP, ₹ Cr), General Government Gross Debt (% of GDP) | **`real_sector` owns:** GDP, GVA, National Income | Fiscal Agent **never** recomputes GDP; consumes official GDP via A2A from Real Sector to evaluate deficit and debt ratios. |
| **Monetary Transmission & Yields** | Government borrowing requirements & sovereign issuances | **`monetary_sector` owns:** Policy Repo Rate, SDF, MSF, LAF operations | Fiscal Agent receives Repo rate via A2A to project sovereign debt interest servicing burden. |
| **Commercial Bank Intermediation** | Central Government market borrowing program absorption | **`finance_sector` owns:** Scheduled Commercial Bank credit, SLR investments | Finance tracks banking system liquidity; Fiscal tracks sovereign treasury demands. |
| **Inflation Adjustments** | Nominal tax collections and excise duty receipts | **`prices_sector` owns:** CPI, WPI, Core & Food Inflation | Fiscal receives CPI from Prices Agent via A2A to compute real tax buoyancy. |

---

## 5. FastMCP Tool Interface (8 Live Tools)

Exposed by `fiscal_sector/mcp_server.py`:

1. `get_union_fiscal_deficit(lookback_records: int = 5)`
   - Returns Union Government accounts: Revenue Receipts, Capex, and Fiscal Deficit (₹ Crore and % of GDP).
2. `get_general_government_debt(start_year: int = 2018, end_year: int = 2025)`
   - Returns General Government Gross Debt (% of GDP) and Net Lending/Borrowing from IMF WEO SDMX/MCP.
3. `get_gst_collections(lookback_months: int = 12)`
   - Returns monthly Gross GST collections, CGST/SGST/IGST/Cess breakup, and YoY growth rates.
4. `get_mospi_product_taxes(lookback_years: int = 5)`
   - Returns Net Taxes on Products from MoSPI eSankhyiki FastMCP.
5. `calculate_gst(amount: float, rate_percent: float, intra_state: bool = True)`
   - Calculates exact GST split (CGST+SGST vs IGST) per statutory rules.
6. `validate_gstin(gstin: str)`
   - Validates 15-character GSTIN format, mod-36 checksum, and decodes the issuing State.
7. `compare_tax_regimes(gross_salary: float, deductions_80c: float = 150000.0, age: int = 35)`
   - Compares New vs Old income tax liability with 87A rebate and standard deductions.
8. `get_fiscal_news(query: str, max_results: int = 5)`
   - Retrieves real-time PIB and Ministry of Finance announcements via Tavily AI.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any financial metric, percentage, rate, or trend without explicitly stating its source.
- **Zero Hallucination / No Hardcoding:** Never hallucinate, estimate, or hardcode random/mock values as factual data. If an external fetch times out, data is served from the verified DuckDB canonical store stamped with `freshness: "cached"`.

### Citation Metadata Structure:
```json
{
  "source_agent": "fiscal_sector",
  "source_authority": "Ministry of Finance / Controller General of Accounts (CGA)",
  "document_title": "Union Budget 2024-25 - Budget at a Glance",
  "table_reference": "Statement 1: Budget at a Glance",
  "indicator_id": "in.macro.fiscal.fiscal_deficit",
  "observation_period": "2024-25 (BE)",
  "value": 4.9,
  "unit": "% of GDP",
  "url": "https://www.indiabudget.gov.in/",
  "freshness": "cached",
  "retrieved_at": "2026-10-06T00:00:00Z"
}
```

---

## 7. A2A Collaboration Protocols

- **Inbound (Consumes via A2A):**
  - From `real_sector`: Real GDP growth and nominal GDP values (to compute fiscal ratios and tax buoyancy).
  - From `prices_sector`: Headline CPI and WPI (to adjust nominal collections for inflation).
  - From `monetary_sector`: Repo rate & stance (to model debt servicing costs on dated G-Sec issuances).
- **Outbound (Provides via A2A):**
  - To `monetary_sector`: Fiscal deficit path and gross market borrowing program (G-Sec supply pressure).
  - To `finance_sector`: Government capex disbursements (crowding-in private infrastructure lending).
  - To `external_sector`: Customs revenue receipts and sovereign external borrowing footprint.
