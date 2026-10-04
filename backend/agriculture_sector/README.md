# Agriculture Agent

The Agriculture Agent is Macrograph-AI's specialist for Indian crop output, agricultural markets, MSP, agriculture-relevant weather, inputs, and agriculture schemes.

Its architecture is deliberately split:

```text
User or peer agent
        |
        v
Agriculture reasoning / A2A
        |
        v
Agriculture FastMCP (19 logical tools)
        |
        v
Agmarknet | MoSPI eSankhyiki | weather_mcp | Data.gov.in
```

A2A carries findings. MCP carries data. The reasoning layer does not call external APIs or source clients.

## Domain ownership

Agriculture owns:

- Crop production, crop area, crop yield, state comparison, and production trends.
- Mandi modal/minimum/maximum prices, arrivals, trends, and market comparison.
- MSP observations, MSP history, and compatible mandi-price/MSP gaps.
- Rainfall observations, sourced rainfall anomalies, official monsoon status, and weather history.
- Fertilizer consumption, irrigation area, and agriculture schemes.
- Supply-side agriculture diagnosis based on the evidence above.

Agriculture does not own CPI, WPI, GDP/GVA, repo rates, bank credit, equity indices, trade balances, or broad fiscal indicators. Those remain with their sector agents.

## Agent and A2A interface

Discovery:

```http
GET /agriculture-sector/.well-known/agent.json
```

Task execution:

```http
POST /agriculture-sector/a2a/tasks
Content-Type: application/json

{
  "query": "Investigate agricultural supply conditions behind onion prices",
  "parameters": {
    "commodity": "onion",
    "state": "Maharashtra"
  }
}
```

The JSON artifact contains:

- `agent`
- `status`
- `findings`
- `citations`
- `errors`
- `analysis`

Each finding has `agent`, `indicator`, `finding`, `evidence`, `source`, `status`, and `confidence`. A completed A2A task can still contain an Agriculture result status of `unavailable`; this means reasoning completed but no verified observation was available.

## MCP interface

The single server is defined in `mcp_server.py` and is mounted at:

```text
/agriculture-sector/mcp
```

Tool discovery and a convenient HTTP data route are also available:

```http
GET  /agriculture-sector/tools
POST /agriculture-sector/data/{tool}
```

The 19 logical tools are:

### Production

- `get_crop_production`
- `get_crop_yield`
- `get_crop_area`
- `get_production_trend`
- `get_state_crop_production`

### Markets

- `get_mandi_price`
- `get_mandi_price_trend`
- `compare_mandi_prices`
- `get_market_arrivals`

### MSP

- `get_msp`
- `get_msp_history`
- `get_msp_gap`

### Weather

- `get_rainfall`
- `get_rainfall_anomaly`
- `get_monsoon_status`
- `get_weather_history`
- `get_current_weather`
- `get_weather_forecast`
- `get_historical_weather`
- `get_agriculture_weather`

Weather requests use the existing Indian Weather MCP backed by Open-Meteo. Relative
periods such as `yesterday`, `last week`, and `last month` are resolved in
`Asia/Kolkata` before the MCP call. Historical results include daily temperature,
precipitation, wind, and ET0 observations where the provider returns them. State
queries use one labeled representative coordinate and are not presented as
state-wide aggregates.

### Inputs and policy

- `get_fertilizer_consumption`
- `get_irrigation_area`
- `get_agriculture_scheme`

All tools accept a typed `AgricultureQuery`. Unsupported or unconfigured operations return `AgricultureResult(status="unavailable")` with structured source errors.

## Data sources

### MoSPI eSankhyiki

The default verified endpoint is `https://mcp.mospi.gov.in/`.

The implementation follows the required sequence:

```text
list_datasets -> get_indicators -> get_metadata -> get_data
```

Current built-in verified mappings use ENVSTATS:

| Operation | Indicator |
|---|---:|
| Crop production | 51 |
| Crop area | 50 |
| Irrigation | 44 |
| Fertilizer consumption | 55 |

### FAOSTAT crop production

Crop-production requests prefer the public FAOSTAT MCP at
`https://faostat.caseyjhand.com/mcp`. The adapter resolves the QCL area, item,
and Production element through FAOSTAT before querying observations, then keeps
the returned year, unit, and data-quality flag in the common provenance model.
MoSPI and configured Data.gov.in mappings remain fallbacks when FAOSTAT cannot
answer. This integration is intentionally crop-only; DES is not configured or
queried by the Agriculture MCP.

User names such as `wheat` are resolved to the numeric codes returned by metadata. Provider-side filters are not trusted: returned rows are filtered again against the user scope.

### Agmarknet

The supplied ready-made server is `Krishna-Baldwa/agmarket-mcp`. Macrograph uses its CEDA branch for historical prices. The main branch's default sample mode is rejected.

Install it into the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install "agmarknet-mcp @ git+https://github.com/Krishna-Baldwa/agmarket-mcp.git@ad4e9b5c38f0fb45565c6ccf4c3ad706371fd891"
```

Set `CEDA_API_KEY` in `backend/.env`. The backend launches the separate server over stdio and calls a structured MCP bridge registered in that subprocess. CEDA's historical update lag is recorded as `source_snapshot`; the agent never presents it as today's price. `DATA_GOV_IN_API_KEY` remains an optional fallback for the main branch. No sample or mock prices are accepted.

### weather_mcp

The supplied README's repository URL is a placeholder. The matching source repository is `AnkurRam2002/Indian-Weather-MCP-Server`. It uses Open-Meteo and Nominatim; it is not an official IMD source.

Local setup:

```powershell
git clone https://github.com/AnkurRam2002/Indian-Weather-MCP-Server.git .mcp-sources/Indian-Weather-MCP-Server
Set-Location .mcp-sources/Indian-Weather-MCP-Server
npm ci
npm run build
```

The adapter invokes the server over stdio. It parses only dated precipitation observations from the historical tool. Seasonal heuristics from that server are rejected as official monsoon status. Every weather citation says Open-Meteo, includes the city/grid scope, and explicitly says it is not IMD station rainfall.

### Data.gov.in

Data.gov.in is the broad official fallback for MSP, crop data, inputs, irrigation, and schemes. Resource mappings must identify an exact resource UUID, fields, units, frequency, and source URL. Unmapped datasets return unavailable rather than guessed values.

Use `AGRICULTURE_OGD_RESOURCES` or a source override in `AGRICULTURE_MCP_SOURCES`. Credentials belong only in `backend/.env`, never source control.

## Configuration

Supported settings are in `core/config.py` and documented in `backend/.env.example`:

- `AGRICULTURE_USE_READYMADE_SOURCES`
- `AGRICULTURE_MOSPI_URL`
- `AGRICULTURE_WEATHER_COMMAND`
- `AGRICULTURE_WEATHER_SCRIPT`
- `AGRICULTURE_MCP_TIMEOUT`
- `DATA_GOV_IN_API_KEY`
- `AGRICULTURE_MCP_SOURCES`
- `AGRICULTURE_OGD_RESOURCES`

Configured MCP schemas are discovered with `list_tools` before invocation. Arguments are validated against the actual upstream tool schema.

## Provenance and citations

Every quantitative observation includes:

- Source agent and source authority.
- Source category and retrieval URL.
- Dataset and exact dataset/table reference.
- Agriculture MCP tool and upstream MCP tool.
- Resolved source filters.
- Indicator, value, unit, frequency, and observation period.
- Data vintage when supplied.
- Time retrieved.
- Retrieval status.
- A deterministic provenance hash.

User-facing reports use numbered references. The evidence table and source cards use the same citation IDs, so the number in the answer can be traced to one exact observation.

`retrieved_live` means the source was queried during the request. It does not mean the observation period is current; the period is always displayed separately.

## Analytics

DuckDB computes interval changes only within an exact series identity: indicator kind, crop/commodity, geography, market, variety, season, unit, frequency, dataset, and source.

The agent supports:

- Year-over-year and month-over-month labels only when periods are exactly adjacent.
- Generic interval change for other valid adjacent records.
- State and market rankings only within comparable periods and units.
- MSP gaps only for compatible crop, variety, season, geography, unit, and effective period.
- Rainfall anomaly only when the source supplies a nonzero normal, baseline period, normal authority, and normal URL.

Relationships are described as associated, consistent, or co-moving. Correlation is not presented as causation.

## Error handling

The source contract distinguishes:

- `not_configured`
- `unsupported`
- `timeout`
- `source_error`
- `missing_data`
- `invalid_data`

If all sources fail, no number is returned. A partial result preserves successful observations and lists every failed fallback. Mock, sample, demo, synthetic, and explicitly estimated responses are rejected.

## Example queries

- How has wheat production changed?
- Which states produce the most rice?
- What is the current MSP for wheat?
- Are mandi prices above MSP?
- How have onion prices changed?
- Was rainfall deficient in Maharashtra?
- Show historical rainfall in Mumbai for the last 7 days.
- How does rainfall compare with crop production?
- Why might agricultural supply be weakening?

City-level weather queries should name a city or supply `parameters.city`. MSP and mandi requests require the corresponding official source configuration.

## Testing

Run the Agriculture contract, parser, routing, failure, A2A, gateway, and provenance tests:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/agriculture_sector/test_agriculture.py -q
```

Run the existing backend regression suites:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests backend/finance_sector/tests backend/real_sector/tests -q --import-mode=importlib
```

All test economic values are explicitly fictional fixtures. Tests never present fixtures as real observations.

## Integration with other agents

The central gateway mounts the Agriculture FastAPI app and MCP transport. The shared registry exposes `Agriculture Agent`; the orchestrator maps Agriculture/Rural tasks to it rather than to Real Sector.

Typical reasoning partners are:

- Prices Agent for food-price supply conditions.
- Real Sector Agent for physical agriculture signals versus Agriculture GVA.
- External Sector Agent for crop trade implications.
- Fiscal Agent for agriculture policy and subsidy implications.

Raw data remains behind Agriculture MCP. Peer agents receive cited findings through A2A.
