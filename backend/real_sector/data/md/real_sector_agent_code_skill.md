# Real Sector Code Agent Skill File

## Role
You are the code agent responsible for building the Real Sector module of the macroeconomic intelligence platform.

## Objective
Implement a working, beginner-friendly, placement-ready Real Sector system with four sub-agents:
- Agriculture Agent
- Industry Agent
- National Income Agent
- Prices & Wages Agent

Then implement one orchestrator:
- Real Sector Agent

## Required stack
Use:
- Python
- FastAPI
- PostgreSQL
- Pandas
- NumPy
- SQLAlchemy
- psycopg2-binary
- Requests
- BeautifulSoup / lxml
- Pydantic
- Docker Compose

Later only, after the base pipeline works:
- Neo4j
- LangGraph
- Qdrant
- Redis
- SHAP

## Architecture rule
Do not jump directly to LLM code.

Build in this order:
1. tables
2. collectors
3. cleaning
4. feature engineering
5. sub-agents
6. orchestrator
7. API
8. graph
9. RAG
10. LLM explanation

## File structure to create
```text
backend/Real Sector/
├── Data/
├── collectors/
├── preprocess/
├── database/
├── features/
├── agents/
├── services/
├── api/
├── graph/
├── llm/
├── tests/
└── docker/
```

## Database requirements
Create PostgreSQL tables for:
- agri_production
- agri_yield
- agri_prices
- agri_msp
- agri_rainfall
- industry_iip
- industry_core
- industry_manufacturing
- industry_mining
- industry_electricity
- gdp_quarterly
- gva_sectorwise
- capital_formation
- gdp_components
- cpi_combined
- wpi_monthly
- food_cpi
- fuel_cpi
- wage_rates
- house_price_index

## Common columns
Every table should support:
- id
- sector
- subsector
- indicator_name
- date
- region_state
- value
- unit
- frequency
- source
- notes
- created_at
- updated_at

## Collector rules
Every collector must:
- download raw data
- save raw file
- parse into DataFrame
- clean columns
- validate schema
- insert into PostgreSQL

One collector per source area:
- agriculture
- industry
- national_income
- prices

## Cleaning rules
For each dataset:
- normalize date formats
- standardize units
- handle missing values
- rename columns into a common schema
- keep raw and cleaned versions separate

## Feature engineering rules
Compute metrics in Python, not in the LLM.

### Agriculture features
- price change %
- production growth %
- yield growth %
- rainfall deficit
- seasonality

### Industry features
- IIP growth %
- core industry growth %
- 3-month rolling average
- manufacturing/mining/electricity contribution

### National Income features
- QoQ GDP growth
- YoY GDP growth
- sector contribution
- capital formation trend

### Prices features
- monthly inflation
- annual inflation
- food inflation
- fuel inflation
- core inflation

## Agent rules
Each agent must return structured JSON.

### Agriculture Agent
Inputs:
- crop prices
- production
- yield
- rainfall
- MSP

Outputs:
- food inflation risk
- crop health summary
- production trend
- rainfall effect
- price spike alerts

### Industry Agent
Inputs:
- IIP
- core industries
- manufacturing
- mining
- electricity

Outputs:
- industrial health
- sector growth
- slowdown alert
- trend summary

### National Income Agent
Inputs:
- GDP
- GVA
- sector-wise GDP
- capital formation

Outputs:
- GDP growth summary
- sector contribution
- investment trend
- slowdown signal

### Prices & Wages Agent
Inputs:
- CPI
- WPI
- food CPI
- fuel CPI
- wage rates
- house price index

Outputs:
- inflation summary
- food inflation signal
- wage inflation trend
- housing inflation signal

## Orchestrator rules
The Real Sector Agent must:
- identify intent from the user query
- route to the correct sub-agents
- run them in parallel if possible
- merge structured outputs
- produce one final explanation
- keep source and computed-value metadata visible

## Supported use cases
Examples:
- Why is food inflation increasing?
- Compare inflation with last year.
- Is industry slowing down?
- What is driving GDP?
- How has agriculture changed?

## API rules
Create FastAPI endpoints such as:
- `GET /real-sector/agriculture`
- `GET /real-sector/industry`
- `GET /real-sector/national-income`
- `GET /real-sector/prices`
- `POST /real-sector/ask`
- `POST /real-sector/refresh`

Use Pydantic models for all request and response bodies.

## Testing requirements
Create tests for:
- collectors
- preprocessing
- features
- agents
- API endpoints

## Coding style
- modular
- readable
- typed
- easy to debug
- simple first, advanced later

## Hard constraint
Do not implement Neo4j, LangGraph, Qdrant, or the LLM explanation layer until the base data pipeline works.

## Deliverable
Produce:
- source code
- config files
- SQL models
- clean tables
- feature pipelines
- agent modules
- API routes
- tests
- Docker files