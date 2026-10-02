# Prices & Inflation Sector Agent (`prices_sector`)

A specialized macroeconomic intelligence agent for Indian inflation metrics, price indices, and cost of living trends.

---

## 1. Domain Scope & Core Responsibilities

The **Prices Sector Agent** is the **exclusive owner** of all inflation and price index metrics for the Indian economy.

It answers three core macroeconomic questions:
1. **Headline Inflation:** What is the current year-on-year trajectory of the Consumer Price Index (CPI All-India, Rural, Urban)?
2. **Underlying Pressures:** Are inflationary impulses driven by volatile food and fuel supply shocks (CFPI) or sticky generalized demand pressures (Core CPI)?
3. **Producer Price Pipeline:** What is the cost-push pressure in the production pipeline as reflected by the Wholesale Price Index (WPI)?

---

## 2. Core Indicators Owned by this Sector

### 1. Consumer Price Index (Retail Inflation)
- **CPI Combined (Headline % YoY)**: Overall cost of living benchmark.
- **CPI Rural & CPI Urban**: Geographic divergence in retail inflation.
- **Consumer Food Price Index (CFPI)**: Cereals, Vegetables, Pulses, Milk, Oils and Fats.
- **Core CPI (% YoY)**: Headline CPI excluding Food & Beverages and Fuel & Light.
- **Base Years**: 2012 series and latest 2024 series.

### 2. Wholesale Price Index (Producer / Wholesale Inflation)
- **WPI All Commodities (% YoY)**: Wholesale price benchmark.
- **WPI Primary Articles**: Food articles, Non-food articles, Minerals.
- **WPI Fuel & Power**: Mineral oils, Electricity, Coal.
- **WPI Manufactured Products**: Core wholesale manufacturing costs.

### 3. Rural & Agricultural Labour Inflation
- **CPI-AL (Agricultural Labourers)** & **CPI-RL (Rural Labourers)**: Cost of living for vulnerable rural workers.

---

## 3. Official Indian Data Sources (MoSPI eSankhyiki MCP)

All empirical data is retrieved from official **Ministry of Statistics and Programme Implementation (MoSPI)** endpoints via the **eSankhyiki MCP Server** (`https://mcp.mospi.gov.in/`).

### MoSPI Datasets & Indicators

| Indicator | MoSPI Dataset Key | Hierarchy / Parameters | Frequency | Official Publisher |
| :--- | :--- | :--- | :--- | :--- |
| **Headline & Sub-Group CPI** | `CPI` | `level="Group"`, `base_year="2012"` / `"2024"` | Monthly | NSO, MoSPI |
| **Commodity Item CPI** | `CPI` | `level="Item"`, `base_year="2012"` / `"2024"` | Monthly | NSO, MoSPI |
| **Wholesale Price Index** | `WPI` | `base_year="2011-12"` | Monthly | Office of Economic Adviser, DPIIT / MoSPI |
| **Agricultural Labourers CPI** | `CPIALRL` | Rural labour price basket | Monthly | Labour Bureau / MoSPI |

### Verified MCP Retrieval Protocol

The agent queries the live MoSPI MCP server at `https://mcp.mospi.gov.in/`:

```
list_datasets() ──► get_indicators("CPI") ──► get_metadata("CPI", ...) ──► get_data("CPI", filters)
```

- **Endpoint:** `https://mcp.mospi.gov.in/`
- **Transport:** HTTP / Server-Sent Events (SSE)
- **Auth:** Zero authentication / public open data
- **FastMCP Version:** FastMCP 3.3

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `prices_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Monetary Policy** | Headline CPI, Core CPI, CFPI | **`monetary_sector` owns:** Policy Repo Rate, Reverse Repo, SDF, MSF, M3 | Prices supplies CPI to Monetary via A2A; Monetary computes real interest rate (`Repo - CPI`). |
| **Agricultural Mandi Prices** | Retail food price indices (CFPI) | **`agriculture_sector` owns:** Mandi arrivals, MSP announcements, Crop production estimates | Prices measures end-consumer food inflation; Agriculture monitors farmgate prices and supply shocks. |
| **Commercial Bank Rates** | Deflators for real borrowing costs | **`finance_sector` owns:** Commercial bank lending rates (WALR, MCLR), NPAs | Prices supplies inflation rate to Finance via A2A to calculate real lending rates (`WALR - CPI`). |
| **National Output** | Price deflators | **`real_sector` owns:** GDP, GVA, Industrial Production (IIP) | Real Sector uses price deflators to compute real GDP from nominal GDP. |

---

## 5. FastMCP Tool Interface

Exposed by `prices_sector/mcp_server.py`:

1. `get_cpi_inflation(lookback_months: int = 12, base_year: str = "2012")`
   - Returns Headline CPI, Rural, Urban, CFPI (Food), and Core CPI inflation (% YoY).
2. `get_cpi_subgroups(lookback_months: int = 6)`
   - Returns group-level breakdown (Food, Fuel & Light, Clothing & Footwear, Housing, Miscellaneous).
3. `get_wpi_inflation(lookback_months: int = 12)`
   - Returns Headline WPI, Primary Articles, Fuel & Power, and Manufactured Products (% YoY).

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any inflation metric, percentage, or index level without explicitly citing its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from MoSPI MCP or DuckDB canonical store, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "prices_sector",
  "source_authority": "National Statistical Office (NSO), MoSPI",
  "document_title": "Consumer Price Index (CPI) Monthly Release",
  "dataset_reference": "CPI",
  "indicator_id": "in.macro.prices.cpi_headline_yoy",
  "observation_period": "2026-08",
  "value": 3.65,
  "unit": "% YoY",
  "url": "https://mcp.mospi.gov.in"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `monetary_sector`: Headline CPI and Core CPI for monetary policy review and inflation targeting.
  - To `finance_sector`: CPI deflator for real lending rate calculations.
  - To `real_sector`: CPI and WPI for GDP deflator estimation.
- **Inbound (Consumes via A2A):**
  - From `agriculture_sector`: Crop yield failures and mandi price spikes for forward-looking food inflation forecasting.
  - From `external_sector`: Imported crude oil price trends and rupee exchange rate pass-through.
