# Real Economy & Output Sector Agent (`real_sector`)

A specialized macroeconomic intelligence agent for India's national accounts, GDP/GVA growth, capital formation, and industrial production indices.

---

## 1. Domain Scope & Core Responsibilities

The **Real Economy Sector Agent** is the **exclusive owner** of sovereign production, national income accounts, and physical industrial output for the Indian economy.

It answers four fundamental macroeconomic questions:
1. **Economic Momentum:** What is India's quarterly and annual Real GDP and Gross Value Added (GVA) growth rate?
2. **Growth Drivers (Demand Side):** Is economic expansion propelled by private consumption (PFCE), government spending (GFCE), or fixed capital investment (GFCF)?
3. **Supply-Side Capacity:** How is output distributed across Agriculture, Industry (Manufacturing, Mining, Utilities, Construction), and Services?
4. **High-Frequency Production:** What do monthly Index of Industrial Production (IIP) and Index of Service Production (ISP) indicate about near-term economic momentum?

---

## 2. Core Indicators Owned by this Sector

### 1. National Accounts Statistics (NAS / GDP / GVA)
- **Real GDP (% YoY)** & **Nominal GDP (% YoY)**.
- **Real Gross Value Added (GVA at Basic Prices)**.
- **Sectoral GVA Breakdown**:
  - Agriculture, Forestry & Fishing GVA.
  - Industry GVA (Manufacturing, Mining & Quarrying, Electricity/Gas/Water, Construction).
  - Services GVA (Trade, Hotels, Transport, Communication, Financial, Real Estate, Public Admin).
- **Expenditure Aggregates**:
  - **PFCE** (Private Final Consumption Expenditure).
  - **GFCF** (Gross Fixed Capital Formation / Investment Rate % of GDP).
  - **GFCE** (Government Final Consumption Expenditure).
  - **Net Exports** of Goods and Services.

### 2. High-Frequency Industrial & Services Output
- **Index of Industrial Production (IIP General)** (% YoY growth).
- **Sectoral IIP**: Manufacturing (77.6% weight), Mining (14.4%), Electricity (8.0%).
- **Use-Based IIP**: Primary Goods, Capital Goods (proxy for capex), Intermediate Goods, Infrastructure/Construction Goods, Consumer Durables, Consumer Non-durables.
- **Index of Service Production (ISP)**: Monthly services output index.

### 3. Factory & Structural Industry Data
- **Annual Survey of Industries (ASI)**: Factory performance, gross output, net value added, invested capital.

---

## 3. Official Indian Data Sources (MoSPI eSankhyiki MCP)

All empirical data is retrieved from official **Ministry of Statistics and Programme Implementation (MoSPI)** endpoints via the **eSankhyiki MCP Server** (`https://mcp.mospi.gov.in/`).

### MoSPI Datasets & Indicators

| Indicator Category | MoSPI Dataset Key | Parameters / Hierarchy | Frequency | Official Source |
| :--- | :--- | :--- | :--- | :--- |
| **National Accounts (GDP/GVA)** | `NAS` | `base_year="2011-12"`, Quarterly & Annual | Quarterly / Annual | National Accounts Division (NAD), NSO |
| **Industrial Production (IIP)** | `IIP` | `base_year="2011-12"`, Sectoral & Use-based | Monthly | NSO, MoSPI |
| **Factory Performance (ASI)** | `ASI` | Factory output & capital parameters | Annual | Industrial Statistics Wing (ISW), NSO |
| **Household Consumption (HCES)** | `HCES` | Monthly Per Capita Expenditure (MPCE), 12 fractiles | Periodic | NSO, MoSPI |
| **Informal MSME Output (ASUSE)** | `ASUSE` | Unincorporated enterprises, MSME GVA per worker | Annual | NSO, MoSPI |

### Verified MCP Retrieval Protocol

The agent queries the live MoSPI MCP server at `https://mcp.mospi.gov.in/`:

```
list_datasets() ──► get_indicators("NAS") ──► get_metadata("NAS", ...) ──► get_data("NAS", filters)
```

- **Endpoint:** `https://mcp.mospi.gov.in/`
- **Transport:** HTTP / Server-Sent Events (SSE)
- **Auth:** Zero authentication required

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `real_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Bank Credit Intermediation** | Physical economic output and fixed capital formation | **`finance_sector` owns:** Sectoral bank credit deployment (Agri, MSME, Large Industry, Services) | Real Sector consumes credit deployment data from Finance via A2A to analyze credit-output elasticity. |
| **Inflation & Deflators** | Real and nominal production figures | **`prices_sector` owns:** CPI, WPI, CFPI | Real Sector receives price deflators from Prices via A2A; does not calculate its own retail inflation. |
| **Labour & Employment** | Aggregate economic output (GVA per sector) | **`labour_sector` owns:** Unemployment rate, LFPR, Worker Population Ratio | Real Sector correlates output momentum with employment data received from Labour via A2A. |
| **Fiscal Capex** | Total national capital formation (GFCF) | **`fiscal_sector` owns:** Central government budget capex and revenue expenditure | Fiscal monitors government budgetary spending; Real Sector tracks total national physical investment. |

---

## 5. FastMCP Tool Interface

Exposed by `real_sector/mcp_server.py`:

1. `get_gdp_growth(lookback_quarters: int = 8)`
   - Returns Real GDP, Nominal GDP, and GVA YoY growth rates.
2. `get_gva_sectoral(lookback_quarters: int = 8)`
   - Returns GVA growth across Agriculture, Manufacturing, Construction, and Services.
3. `get_iip_growth(lookback_months: int = 12)`
   - Returns IIP General, Manufacturing, Mining, Electricity, and Capital Goods (% YoY).

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any GDP growth rate, GVA figure, or IIP percentage without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from MoSPI MCP or DuckDB canonical store, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "real_sector",
  "source_authority": "National Statistical Office (NSO), MoSPI",
  "document_title": "Quarterly Estimates of GDP / National Accounts",
  "dataset_reference": "NAS",
  "indicator_id": "in.macro.real.gdp_constant_yoy",
  "observation_period": "2026-Q1",
  "value": 7.2,
  "unit": "% YoY",
  "url": "https://mcp.mospi.gov.in"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `monetary_sector`: Output gap and GDP growth momentum for policy stance decisions.
  - To `finance_sector`: Industrial and services GVA growth to benchmark credit demand.
  - To `fiscal_sector`: Nominal GDP figures for deficit-to-GDP ratio denominators.
- **Inbound (Consumes via A2A):**
  - From `finance_sector`: Commercial bank credit growth to Industry and Infrastructure.
  - From `prices_sector`: CPI and WPI deflators to convert nominal series to real values.
  - From `labour_sector`: Employment growth rates to evaluate labour productivity.
