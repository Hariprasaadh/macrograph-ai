# Labour & Employment Sector Agent (`labour_sector`)

A specialized macroeconomic intelligence agent for India's employment trends, labour force participation, unemployment metrics, and wage dynamics.

---

## 1. Domain Scope & Core Responsibilities

The **Labour & Employment Sector Agent** is the **exclusive owner** of sovereign labour market statistics and employment indicators for the Indian economy.

It answers four fundamental macroeconomic questions:
1. **Unemployment Trajectory:** What is India's national Unemployment Rate (UR) under Usual Status (ps+ss) and Current Weekly Status (CWS)?
2. **Workforce Engagement:** How are the Labour Force Participation Rate (LFPR) and Worker Population Ratio (WPR) moving across rural and urban geographies?
3. **Gender Participation:** What is the trajectory of the Female Labour Force Participation Rate (FLFPR), a key structural growth parameter?
4. **Employment Quality & Wages:** How is the workforce distributed across regular wage/salaried, self-employed, and casual labour, and how are real earnings evolving?

---

## 2. Core Indicators Owned by this Sector

### 1. Headline Labour Market Rates
- **Unemployment Rate (UR %)**: Percentage of persons in the labour force who are unemployed (Usual Status & CWS).
- **Labour Force Participation Rate (LFPR %)**: Percentage of persons in the labour force (working or seeking work) in the population.
- **Worker Population Ratio (WPR %)**: Percentage of employed persons in the total population.

### 2. Demographic & Geographic Disaggregation
- **Rural vs Urban**: Rural LFPR/UR vs Urban LFPR/UR.
- **Gender Disaggregation**: Male LFPR/UR vs Female LFPR/UR (FLFPR dynamics).
- **Youth Unemployment**: Unemployment rate in the 15-29 age bracket.

### 3. Employment Category & Quality
- **Activity Status Breakdown**:
  - Self-employed (Own account workers & unpaid household helpers).
  - Regular wage / salaried employees.
  - Casual labour.
- **Sectoral Distribution**: Proportion of workers in Agriculture, Manufacturing, Construction, and Services.
- **Average Daily / Monthly Earnings**: Wages across activity statuses and genders.

---

## 3. Official Indian Data Sources (MoSPI eSankhyiki MCP)

All empirical data is retrieved from official **Ministry of Statistics and Programme Implementation (MoSPI)** endpoints via the **eSankhyiki MCP Server** (`https://mcp.mospi.gov.in/`).

### MoSPI Datasets & Indicators

| Indicator Category | MoSPI Dataset Key | Parameters / Hierarchy | Frequency | Official Source |
| :--- | :--- | :--- | :--- | :--- |
| **Periodic Labour Force Survey** | `PLFS` | `level`, `classification_year`, `gender`, `sector` (Rural/Urban) | Quarterly (Urban) & Annual (Rural+Urban) | National Statistical Office (NSO), MoSPI |
| **Time Use Survey** | `TUS` | Unpaid care work, time allocation | Periodic | NSO, MoSPI |

### Verified MCP Retrieval Protocol

The agent queries the live MoSPI MCP server at `https://mcp.mospi.gov.in/`:

```
list_datasets() ──► get_indicators("PLFS") ──► get_metadata("PLFS", ...) ──► get_data("PLFS", filters)
```

- **Endpoint:** `https://mcp.mospi.gov.in/`
- **Transport:** HTTP / Server-Sent Events (SSE)
- **Auth:** Zero authentication required

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `labour_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Industrial Output & Value Added** | Total labour supply, employment shares, and worker counts | **`real_sector` owns:** National GDP, GVA, and physical factory output (IIP, ASI) | Labour supplies workforce numbers to Real Sector via A2A to compute labour productivity (GVA / worker). |
| **Consumer Prices & Living Costs** | Nominal wage earnings across activity categories | **`prices_sector` owns:** CPI, WPI, and rural labour inflation indices (CPIALRL) | Labour consumes CPIALRL from Prices via A2A to compute real wage growth adjusted for inflation. |
| **Agricultural Farm Labor** | Overall rural workforce participation and casual wages | **`agriculture_sector` owns:** Sowing progress, farm harvest output, MSP | Agriculture monitors crop seasons; Labour tracks structural movement of workforce out of agriculture. |
| **Fiscal Social Spending** | Demand for work under employment schemes | **`fiscal_sector` owns:** MGNREGA budget allocation and actual fiscal disbursements | Fiscal tracks budget outlay; Labour tracks rural employment slack and reservation wages. |

---

## 5. FastMCP Tool Interface

Exposed by `labour_sector/mcp_server.py`:

1. `get_unemployment_rate(lookback_quarters: int = 8, status_type: str = "CWS")`
   - Returns national, rural, and urban unemployment rates.
2. `get_labour_participation(lookback_quarters: int = 8)`
   - Returns LFPR and WPR with gender breakdown (Male vs Female).
3. `get_employment_distribution(survey_year: str = "latest")`
   - Returns workforce share across regular salaried, self-employed, and casual labour, plus broad industry sectors.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any unemployment rate, participation ratio, or wage statistic without explicitly stating its source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from MoSPI MCP or DuckDB canonical store, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "labour_sector",
  "source_authority": "National Statistical Office (NSO), MoSPI",
  "document_title": "Periodic Labour Force Survey (PLFS) Quarterly Bulletin",
  "dataset_reference": "PLFS",
  "indicator_id": "in.macro.labour.unemployment_rate_cws",
  "observation_period": "2026-Q1",
  "value": 6.7,
  "unit": "%",
  "url": "https://mcp.mospi.gov.in"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `real_sector`: Employment numbers and worker counts for productivity estimation.
  - To `monetary_sector`: Labour market slack (unemployment rate vs non-accelerating inflation rate of unemployment / NAIRU).
  - To `fiscal_sector`: Rural and urban employment health to assess social scheme targeting.
- **Inbound (Consumes via A2A):**
  - From `prices_sector`: CPI-AL and CPI-RL to adjust nominal wages for inflation.
  - From `real_sector`: GVA growth in labour-intensive sectors (Construction, Trade, Manufacturing).
