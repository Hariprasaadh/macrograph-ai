# Services Sector Agent (`services_sector`)

A specialized macroeconomic intelligence agent for India's services production, services trade, high-frequency activity trackers, and service sector sentiment.

---

## 1. Domain Scope & Core Responsibilities

The **Services Sector Agent** is the **exclusive owner** of high-frequency services output indices, sector-specific operational volumes, and services purchasing sentiment for the Indian economy.

It answers four fundamental macroeconomic questions:
1. **High-Frequency Services Growth:** How is the formal services sector expanding as measured by the monthly Index of Service Production (ISP)?
2. **Business Sentiment & Momentum:** What are the demand conditions and business activity trends captured by the Services PMI?
3. **Core Service Verticals:** How are key service sub-sectors (Trade, Hotels, Transport, Communication, Real Estate, Professional Services) performing?
4. **Digital & Telecom Activity:** What do telecom broadband subscriptions and digital platform activity reveal about tertiary sector velocity?

---

## 2. Core Indicators Owned by this Sector

### 1. Index of Service Production (MoSPI ISP - Monthly)
- **ISP General Index (% YoY & MoM)**: Monthly counterpart to IIP for services (Base Year 2024-25).
- **Sub-Sector Indices** (19 sub-sectors covering ~60% of services GVA):
  - Wholesale and Retail Trade.
  - Land, Water, and Air Transport.
  - Warehousing and Support Activities.
  - Telecommunications & Information Services.
  - Real Estate Activities.
  - Professional, Scientific, and Technical Services.

### 2. High-Frequency Volume Trackers
- **Civil Aviation**: Domestic passenger traffic, International passenger traffic, and air freight (DGCA).
- **Railway Freight Traffic**: Revenue-earning freight loading (Million Tonnes).
- **Major Port Cargo Traffic**: Container and bulk cargo volumes (IPA).
- **Telecom Indicators**: Wireless subscriber base, broadband connections, and monthly data usage (TRAI).

### 3. Services Sentiment & Expectations
- **Services PMI (Purchasing Managers' Index)**: Headline business activity, new export orders, input costs, and employment sentiment (S&P Global / HSBC).

---

## 3. Official Indian Data Sources (MoSPI eSankhyiki MCP)

Services production and survey datasets are retrieved from official **Ministry of Statistics and Programme Implementation (MoSPI)** endpoints via the **eSankhyiki MCP Server** (`https://mcp.mospi.gov.in/`). Services PMI sentiment is sourced from S&P Global / HSBC, and high-frequency transport & telecom metrics are sourced from DGCA, IPA, and TRAI.

### MoSPI Dataset Key

| Indicator | MoSPI Dataset Key | Parameters | Frequency | Official Source |
| :--- | :--- | :--- | :--- | :--- |
| **Index of Service Production** | `ISP` | `base_year="2024-25"`, sub-sector codes | Monthly | Service Statistics Wing, NSO, MoSPI |
| **Telecom & Digital Connectivity** | `NSS80` | `module="CMST"` (Mobile, Internet usage) | Periodic | NSO, MoSPI |

### Verified MCP Retrieval Protocol

```
list_datasets() ──► get_indicators("ISP") ──► get_metadata("ISP", ...) ──► get_data("ISP", filters)
```

- **Endpoint:** `https://mcp.mospi.gov.in/`
- **Transport:** HTTP / Server-Sent Events (SSE)
- **Auth:** Zero authentication required

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `services_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **National Accounts Output** | High-frequency ISP and sector-specific volumes | **`real_sector` owns:** Aggregate Services GVA (Quarterly/Annual National Accounts) | Services Sector provides high-frequency lead indicators to Real Sector via A2A to forecast quarterly GVA. |
| **Financial & Banking Services** | Real estate, professional, and transport services | **`finance_sector` owns:** Scheduled Commercial Banks, Credit deployment, Asset quality | Finance tracks banking system intermediation; Services tracks non-financial services verticals. |
| **Services Exports & Remittances** | IT/ITeS volume trends and software sector momentum | **`external_sector` owns:** BoP net services export balance (USD Million) | External tracks cross-border dollar balance; Services tracks underlying domestic capacity and headcount. |
| **Service Workforce & Jobs** | Service sector operational capacity | **`labour_sector` owns:** Overall tertiary sector employment share, wages | Labour tracks formal/informal workforce counts; Services tracks enterprise output momentum. |

---

## 5. FastMCP Tool Interface

Exposed by `services_sector/mcp_server.py`:

1. `get_isp_growth(lookback_months: int = 12)`
   - Returns monthly Index of Service Production (General and 19 sub-sectors).
2. `get_services_pmi(lookback_months: int = 12)`
   - Returns Services PMI headline activity, new orders, and input cost trends.
3. `get_transport_and_freight_indicators(lookback_months: int = 6)`
   - Returns aviation passenger traffic, port cargo traffic, and railway freight.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any ISP index value, PMI level, or traffic volume without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from MoSPI MCP or DuckDB, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "services_sector",
  "source_authority": "National Statistical Office (NSO), MoSPI",
  "document_title": "Index of Service Production (ISP) Monthly Release",
  "dataset_reference": "ISP",
  "indicator_id": "in.macro.services.isp_general_yoy",
  "observation_period": "2026-06",
  "value": 6.8,
  "unit": "% YoY",
  "url": "https://mcp.mospi.gov.in"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `real_sector`: Monthly ISP momentum as high-frequency lead indicator for quarterly Services GVA.
  - To `external_sector`: Software and IT/ITeS service capacity to explain services export trends.
  - To `labour_sector`: Services activity sentiment to benchmark urban employment demand.
- **Inbound (Consumes via A2A):**
  - From `finance_sector`: Commercial bank credit flow to Services (NBFCs, Trade, Real Estate).
  - From `prices_sector`: Miscellaneous CPI services inflation (Transport, Education, Healthcare).
