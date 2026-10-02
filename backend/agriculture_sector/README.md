# Agriculture & Rural Economy Sector Agent (`agriculture_sector`)

A specialized macroeconomic intelligence agent for India's farm output, crop production, mandi arrivals, rural farmgate dynamics, and monsoon progress.

---

## 1. Domain Scope & Core Responsibilities

The **Agriculture Sector Agent** is the **exclusive owner** of upstream farm production, agricultural inputs, farmgate pricing, and climate-agricultural linkages for the Indian economy.

It answers four fundamental macroeconomic questions:
1. **Supply-Side Crop Output:** What are the kharif and rabi sowing progress and official crop production estimates (Foodgrains, Pulses, Oilseeds, Commercial crops)?
2. **Farmgate Pricing & Support:** What are the market mandi arrivals and procurement dynamics relative to Minimum Support Prices (MSP)?
3. **Monsoon & Climate Shocks:** How are southwest and northeast monsoon precipitation deviations and reservoir storage levels impacting agricultural output?
4. **Rural Household Economics:** How are farming household incomes, land holding sizes, and farming input costs evolving?

---

## 2. Core Indicators Owned by this Sector

### 1. Crop Production & Sowing Progress
- **Acreage / Sowing Area (Lakh Hectares)**: Kharif vs Rabi season acreage.
- **Advance Estimates of Crop Production**: Total Foodgrains (Rice, Wheat, Coarse Cereals), Pulses (Tur, Gram), Oilseeds, Sugarcane, Cotton.
- **Yield Trajectories**: Productivity (kg/hectare) across major agro-climatic zones.

### 2. Mandi Arrivals & Procurement
- **Mandi Wholesale Arrivals (Tonnes / Quintals)**: Daily wholesale arrivals across APMC mandis.
- **Farmgate Wholesale Prices**: Real-time wholesale mandi prices (Agmarknet).
- **Minimum Support Price (MSP)**: Announced floor prices per quintal.
- **Central Pool Foodgrain Stocks**: Rice and wheat buffer stocks in FCI godowns.

### 3. Monsoon & Reservoir Dynamics
- **Monsoon Rainfall Departure (% deviation from LPA - Long Period Average)**: Sub-divisional and All-India rainfall tracking.
- **Live Reservoir Storage (% of total capacity)**: Water availability across CWC (Central Water Commission) monitored reservoirs.

### 4. Structural Farm Economics (MoSPI NSS 77th Round)
- **Average Monthly Farm Household Income** (Rs. per agricultural household).
- **Operational Land Holdings**: Household distribution across marginal (<1 ha), small (1-2 ha), medium, and large holdings.
- **Input Utilization**: Seed purchase, fertilizer usage, and crop insurance coverage.

---

## 3. Official Indian Data Sources

All empirical data is retrieved from official government publishers and MCP servers.

### 1. MoSPI eSankhyiki MCP Server (`https://mcp.mospi.gov.in/`)

| Dataset Key | Module / Indicator | Parameters | Official Source |
| :--- | :--- | :--- | :--- |
| **`NSS77`** | `module="land_livestock"` | Indicator 16: Size class of land possessed<br>Indicator 24: Average monthly farm household income<br>Indicator 22: Farm inputs & seed utilization | NSO, MoSPI |

### 2. Ministry of Agriculture & Farmers' Welfare (DAC&FW) & Agmarknet

| Domain | Source Authority | Frequency | Indicators |
| :--- | :--- | :--- | :--- |
| **Mandi Prices & Arrivals** | Agmarknet (Directorate of Marketing & Inspection) | Daily | Modal price, Min/Max price, Arrivals across APMC mandis |
| **Crop Estimates** | Directorate of Economics & Statistics (DES) | Quarterly / Seasonal | 1st, 2nd, 3rd, 4th Advance Estimates of production |
| **Monsoon Departure** | India Meteorological Department (IMD) | Weekly / Seasonal | Rainfall % departure from normal (LPA) |

---

## 4. Single Source of Truth & Boundary Rules

| Domain | `agriculture_sector` OWNS | Other Sectors OWN (DO NOT FETCH HERE) | Interaction Rule |
| :--- | :--- | :--- | :--- |
| **Retail Food Inflation** | Farmgate wholesale mandi arrivals and MSP floor | **`prices_sector` owns:** Consumer Food Price Index (CFPI), Retail item inflation | Agriculture provides early supply shock signals to Prices via A2A; Prices measures the consumer impact. |
| **Agricultural Bank Credit** | Farm household income and input capital demand | **`finance_sector` owns:** Commercial bank credit deployed to Agriculture | Finance tracks bank loans disbursed to agriculture; Agriculture tracks actual crop physical production. |
| **National Output & Value Added** | Physical crop yields and acreage | **`real_sector` owns:** Agriculture & Allied Activities GVA (National Accounts) | Real Sector converts physical farm output and prices into national GVA. |
| **Fertilizer & Farm Subsidies** | Input cost indicators and seed purchases | **`fiscal_sector` owns:** Central budget food and fertilizer subsidy outlays | Fiscal monitors fiscal subsidy bill; Agriculture monitors farmgate input affordability. |

---

## 5. FastMCP Tool Interface

Exposed by `agriculture_sector/mcp_server.py`:

1. `get_crop_production_estimates(crop_year: str = "latest", season: str = "kharif")`
   - Returns production advance estimates and acreage for major foodgrains and pulses.
2. `get_mandi_prices_and_arrivals(commodity: str, lookback_days: int = 30)`
   - Returns modal wholesale mandi prices and arrivals across APMC mandis.
3. `get_monsoon_progress()`
   - Returns cumulative rainfall % departure from LPA and reservoir storage levels.
4. `get_farm_household_structure()`
   - Queries MoSPI `NSS77` for farm household income and operational land holding distribution.

---

## 6. Strict Citation & "No Source, No Answer" Policy

- **No Source, No Answer:** Do not generate any crop yield, production volume, or mandi price without explicitly citing the official source.
- **Zero Hallucination:** Never hardcode dummy or mock percentages. If an indicator cannot be fetched from official sources or DuckDB, return `status: "unavailable"`.

### Citation Metadata Schema
```json
{
  "source_agent": "agriculture_sector",
  "source_authority": "Ministry of Agriculture & Farmers Welfare / MoSPI",
  "document_title": "Advance Estimates of Production of Major Crops",
  "indicator_id": "in.macro.agri.foodgrains_production_total",
  "observation_period": "2024-25",
  "value": 332.3,
  "unit": "Million Tonnes",
  "url": "https://agricoop.nic.in"
}
```

---

## 7. A2A Collaboration Protocols

- **Outbound (Provides via A2A):**
  - To `prices_sector`: Farmgate supply shocks, mandi arrivals, and MSP hikes for food inflation forecasting.
  - To `real_sector`: Crop production volumes for Agricultural GVA computation.
  - To `external_sector`: Exportable surplus or import dependency (e.g. pulses, edible oils).
- **Inbound (Consumes via A2A):**
  - From `finance_sector`: Priority sector agricultural credit flow and Kisan Credit Card (KCC) disbursements.
  - From `prices_sector`: Consumer food price pressures to identify farm-to-retail margin widening.
