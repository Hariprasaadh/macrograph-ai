# Real Sector Agent — Complete Implementation File

## Goal
Implement a beginner-friendly but placement-worthy Real Sector system that covers:
- Agriculture
- Industry
- National Income
- Prices & Wages

The module should answer macro questions like:
- Why is food inflation increasing?
- Compare inflation with last year.
- Is industry slowing down?
- What is driving GDP?
- How has agriculture changed?

This real-sector structure matches the project plan’s split into agriculture, industrial statistics, national income, and prices/wages. The plan also uses FastAPI, PostgreSQL, Neo4j, Qdrant, LangGraph, Pydantic, MCP, Redis, SHAP, and Docker Compose. fileciteturn1file0L7-L17 fileciteturn1file0L155-L169

---

## 1) Project Stack

### Core stack for Version 1
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

### Later-stage stack
- Neo4j for causal links
- LangGraph for orchestration
- Qdrant for policy-document RAG
- Redis for caching
- SHAP for explainability

---

## 2) Folder Structure

```text
backend/
└── Real Sector/
    ├── Data/
    │   ├── Agri/
    │   ├── Income/
    │   ├── Ind/
    │   └── Prices/
    │
    ├── collectors/
    │   ├── agriculture/
    │   ├── industry/
    │   ├── national_income/
    │   └── prices/
    │
    ├── preprocess/
    │   ├── agriculture_cleaner.py
    │   ├── industry_cleaner.py
    │   ├── income_cleaner.py
    │   ├── prices_cleaner.py
    │   └── common.py
    │
    ├── database/
    │   ├── db.py
    │   ├── models.py
    │   ├── schema.sql
    │   └── insert_data.py
    │
    ├── features/
    │   ├── agriculture_features.py
    │   ├── industry_features.py
    │   ├── income_features.py
    │   ├── prices_features.py
    │   └── utils.py
    │
    ├── agents/
    │   ├── agriculture_agent.py
    │   ├── industry_agent.py
    │   ├── national_income_agent.py
    │   ├── prices_agent.py
    │   ├── real_sector_agent.py
    │   ├── router.py
    │   └── response_models.py
    │
    ├── services/
    │   ├── agriculture_service.py
    │   ├── industry_service.py
    │   ├── income_service.py
    │   ├── prices_service.py
    │   └── analytics_service.py
    │
    ├── api/
    │   ├── agriculture_routes.py
    │   ├── industry_routes.py
    │   ├── income_routes.py
    │   ├── prices_routes.py
    │   ├── real_sector_routes.py
    │   └── health.py
    │
    ├── graph/
    │   ├── neo4j_service.py
    │   ├── build_graph.py
    │   └── graph_queries.py
    │
    ├── llm/
    │   ├── prompt_templates.py
    │   ├── summarizer.py
    │   └── explanation.py
    │
    ├── tests/
    │   ├── test_collectors.py
    │   ├── test_preprocessing.py
    │   ├── test_features.py
    │   ├── test_agents.py
    │   └── test_api.py
    │
    └── docker/
        ├── Dockerfile
        └── docker-compose.yml
```

---

## 3) Database First

Create PostgreSQL tables first. Use one common schema for all tables.

### Common columns
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

### Tables to create

#### Agriculture
- agri_production
- agri_yield
- agri_prices
- agri_msp
- agri_rainfall

#### Industry
- industry_iip
- industry_core
- industry_manufacturing
- industry_mining
- industry_electricity

#### National Income
- gdp_quarterly
- gva_sectorwise
- capital_formation
- gdp_components

#### Prices & Wages
- cpi_combined
- wpi_monthly
- food_cpi
- fuel_cpi
- wage_rates
- house_price_index

---

## 4) Data Frequency Rules

Use these frequencies:

### Agriculture
- agri_production: yearly
- agri_yield: yearly
- agri_prices: daily
- agri_msp: yearly
- agri_rainfall: daily, then aggregate monthly

### Industry
- industry_iip: monthly
- industry_core: monthly
- industry_manufacturing: monthly
- industry_mining: monthly
- industry_electricity: monthly

### National Income
- gdp_quarterly: quarterly
- gva_sectorwise: quarterly or annual depending on source
- capital_formation: quarterly
- gdp_components: quarterly

### Prices & Wages
- cpi_combined: monthly
- wpi_monthly: monthly
- food_cpi: monthly
- fuel_cpi: monthly
- wage_rates: monthly if available, otherwise yearly
- house_price_index: quarterly

---

## 5) Collectors

Create one collector per source area.

### Collector folders
- collectors/agriculture/
- collectors/industry/
- collectors/national_income/
- collectors/prices/

### Every collector must:
1. download raw data
2. save raw file
3. parse into DataFrame
4. clean columns
5. insert into PostgreSQL

### Collector design rules
- Keep raw files untouched
- Save processed files separately
- Log source, date, status, row count
- Validate schema before insert
- Avoid hardcoding file names

---

## 6) Cleaning and Standardization

For every dataset:
- normalize date formats
- standardize units
- handle missing values
- rename columns into one common schema
- keep raw and cleaned versions separate

### Common cleaning tasks
- convert Excel dates to ISO format
- remove duplicate header rows
- strip whitespace from column names
- cast numeric columns safely
- handle empty cells as nulls
- harmonize state names

---

## 7) Feature Tables

Do not ask AI to compute simple metrics.

Compute the following in Python.

### Agriculture
- price change %
- production growth %
- yield growth %
- rainfall deficit
- seasonality

### Industry
- IIP growth %
- core industry growth %
- 3-month rolling average
- manufacturing/mining/electricity contribution

### National Income
- QoQ GDP growth
- YoY GDP growth
- sector contribution
- capital formation trend

### Prices
- monthly inflation
- annual inflation
- food inflation
- fuel inflation
- core inflation

### Feature output tables
Save them in a separate folder or feature table set:
- feature_agriculture
- feature_industry
- feature_income
- feature_prices

---

## 8) Sub-Agent Design

Each sub-agent must return structured JSON, not free text.

### Agriculture Agent
#### Inputs
- crop prices
- production
- yield
- rainfall
- MSP

#### Outputs
- food inflation risk
- crop health summary
- production trend
- rainfall effect
- price spike alerts

### Industry Agent
#### Inputs
- IIP
- core industries
- manufacturing
- mining
- electricity

#### Outputs
- industrial health
- sector growth
- slowdown alert
- trend summary

### National Income Agent
#### Inputs
- GDP
- GVA
- sector-wise GDP
- capital formation

#### Outputs
- GDP growth summary
- sector contribution
- investment trend
- slowdown signal

### Prices & Wages Agent
#### Inputs
- CPI
- WPI
- food CPI
- fuel CPI
- wage rates
- house price index

#### Outputs
- inflation summary
- food inflation signal
- wage inflation trend
- housing inflation signal

---

## 9) Real Sector Orchestrator

The Real Sector Agent should:
1. read the user query
2. determine which sub-agents are needed
3. run them in parallel if possible
4. merge their structured outputs
5. produce one explanation
6. return a single final JSON response

### Example routing
- “Why is food inflation increasing?”  
  Route to Agriculture + Prices + rainfall data

- “Is industry slowing down?”  
  Route to Industry

- “Compare inflation with last year.”  
  Route to Prices

- “What is driving GDP?”  
  Route to National Income + Industry + Prices

---

## 10) API Endpoints

Recommended endpoints:

- `GET /real-sector/agriculture`
- `GET /real-sector/industry`
- `GET /real-sector/national-income`
- `GET /real-sector/prices`
- `POST /real-sector/ask`
- `POST /real-sector/refresh`

Each endpoint should:
- validate input with Pydantic
- query cleaned tables or feature tables
- return structured JSON
- include source metadata

---

## 11) Causal Graph Later

After the numeric pipeline works, add Neo4j causal links.

### Example causal paths
- rainfall -> crop yield -> crop prices -> food CPI -> headline CPI
- IIP -> industrial output -> GDP growth
- wages -> consumption -> CPI
- capital formation -> GDP growth

---

## 12) RAG Later

Use Qdrant only for:
- policy documents
- methodology docs
- reports
- explanatory text

Do not use Qdrant for the main numeric tables.

---

## 13) LLM Layer Later

Add the LLM only after the data pipeline and feature tables work.

Use the LLM for:
- explanation generation
- natural-language summaries
- answering the user in a readable way

Do not let the LLM compute raw metrics.

---

## 14) Testing Order

Test in this order:
1. data download
2. parsing
3. cleaning
4. DB insert
5. feature calculation
6. each sub-agent
7. orchestrator
8. API responses
9. dashboard rendering

---

## 15) Recommended Build Order

1. CPI ingestion
2. IIP ingestion
3. Quarterly GDP ingestion
4. Crop production ingestion
5. PostgreSQL tables
6. FastAPI endpoints
7. Four sub-agents
8. Real Sector orchestrator
9. Neo4j graph
10. Dashboard
11. LLM explanation last

---

## 16) Delivery Goal

The final Real Sector system should answer:
- Why is food inflation increasing?
- Compare inflation with last year.
- Is industry slowing?
- What is driving GDP?
- How has agriculture changed?