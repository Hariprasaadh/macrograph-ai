# Developer 1 — Core Platform, Data Ingestion & Orchestration Lead

## Mission Summary
You are responsible for the **Core Platform & Central Orchestration Layer**. Your job is to:
1. Ensure DuckDB data integrity with composite unique constraints and upsert mechanics.
2. Build the standardized live API base client and error schema (`LiveAPIErrorResponse`).
3. Wire all 8 domain executors into the central `AgentRegistry`.
4. Update the LangGraph multi-agent orchestrator to route across all 8 sectors independently.
5. Mount all domain sub-applications into the unified FastAPI gateway.
6. Author integration tests proving full 8-sector discovery and routing.

---

## Assigned Files & Directory Scope
```
backend/
├── core/
│   ├── database/
│   │   └── macro_store.py              # [MODIFY] Add unique index & upsert_canonical_observation()
│   ├── ingestion/
│   │   └── live_client_base.py         # [NEW] LiveAPIErrorResponse + Tenacity retry client base
│   └── orchestrator/
│       ├── registry_bootstrap.py       # [MODIFY] Register all 8 domain executors
│       └── graph.py                    # [MODIFY] Decouple sector_agent_map to all 8 sectors
├── main.py                             # [MODIFY] Mount all 8 sector sub-apps
└── tests/
    ├── test_data_deduplication.py      # [NEW] Tests for upsert & index integrity
    └── test_orchestrator_8_sectors.py  # [NEW] Tests for 8-agent discovery & routing
```

---

## Step-by-Step Action Items

### Task 1.1: DuckDB Deduplication & Key Constraints
**Target File**: `backend/core/database/macro_store.py`
1. In `_init_schema()`, add a unique composite index to prevent duplicate observations:
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS idx_canonical_obs_unique 
   ON canonical_observations (indicator_id, observation_period);
   ```
2. Implement `upsert_canonical_observation(self, obs: CanonicalObservation) -> None`:
   ```python
   def upsert_canonical_observation(self, obs: CanonicalObservation) -> None:
       """Inserts or updates a canonical observation using composite key (indicator_id, observation_period)."""
       query = """
           INSERT INTO canonical_observations (
               observation_id, indicator_id, observation_period, value, unit,
               release_timestamp, retrieved_timestamp, revision_status, data_status,
               confidence, z_score, percentile_rank, provenance_hash, metadata_json
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (indicator_id, observation_period) DO UPDATE SET
               value = EXCLUDED.value,
               revision_status = EXCLUDED.revision_status,
               retrieved_timestamp = EXCLUDED.retrieved_timestamp,
               data_status = EXCLUDED.data_status,
               provenance_hash = EXCLUDED.provenance_hash,
               metadata_json = EXCLUDED.metadata_json;
       """
       with self.get_connection() as con:
           con.execute(query, [
               obs.observation_id, obs.indicator_id, obs.observation_period, obs.value, obs.unit,
               obs.release_timestamp, obs.retrieved_timestamp, obs.revision_status.value, obs.data_status.value,
               obs.confidence, obs.z_score, obs.percentile_rank, obs.provenance_hash, json.dumps(obs.metadata)
           ])
   ```

### Task 1.2: Standardized Live API Error Model & Base Client
**Target File**: `backend/core/ingestion/live_client_base.py`
1. Create `LiveAPIErrorResponse`:
   ```python
   from datetime import datetime, timezone
   from pydantic import BaseModel, Field
   from core.data.schema import SectorEnum

   class LiveAPIErrorResponse(BaseModel):
       status: str = "error"
       error_code: str = Field(..., description="E.g. LIVE_API_TIMEOUT, UPSTREAM_HTTP_502")
       domain_sector: SectorEnum
       target_indicator: str
       source_authority: str
       endpoint_attempted: str
       http_status_code: int
       failure_reason: str
       retry_attempted: int = 3
       timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
   ```
2. Implement a `BaseLiveClient` class configured with `tenacity` retries (3 attempts, exponential backoff: 1s, 2s, 4s).

### Task 1.3: Update Central A2A Registry Bootstrap
**Target File**: `backend/core/orchestrator/registry_bootstrap.py`
Register all 8 domain executors:
```python
from real_sector.agents.executor import RealSectorAgentExecutor
from finance_sector.agents.executor import FinanceSectorAgentExecutor
from capital_market_sector.agents.executor import CapitalMarketsAgentExecutor
from prices_sector.agents.executor import PricesInflationAgentExecutor
from monetary_sector.agents.executor import MonetaryBankingAgentExecutor
from labour_sector.agents.executor import LabourEmploymentAgentExecutor
from agriculture_sector.agents.executor import AgricultureRuralAgentExecutor
from fiscal_sector.agents.executor import FiscalSectorAgentExecutor
from external_sector.agents.executor import ExternalSectorAgentExecutor

def bootstrap_agent_registry() -> None:
    executors = [
        RealSectorAgentExecutor,
        FinanceSectorAgentExecutor,
        CapitalMarketsAgentExecutor,
        PricesInflationAgentExecutor,
        MonetaryBankingAgentExecutor,
        LabourEmploymentAgentExecutor,
        AgricultureRuralAgentExecutor,
        FiscalSectorAgentExecutor,
        ExternalSectorAgentExecutor,
    ]
    for executor_cls in executors:
        agent_registry.register(executor_cls.get_agent_card(), executor_cls())
```

### Task 1.4: Update LangGraph Orchestrator Sector Routing
**Target File**: `backend/core/orchestrator/graph.py`
In `parallel_a2a_execute_node`, decouple the `sector_agent_map` so all 8 sectors route directly:
```python
sector_agent_map = {
    SectorEnum.REAL_ECONOMY.value: "Real Sector Macroeconomic Agent",
    SectorEnum.PRICES_INFLATION.value: "Prices & Inflation Macroeconomic Agent",
    SectorEnum.MONETARY_BANKING.value: "Monetary & Banking Macroeconomic Agent",
    SectorEnum.FISCAL.value: "Fiscal Sector Macroeconomic Agent",
    SectorEnum.EXTERNAL.value: "External Sector Macroeconomic Agent",
    SectorEnum.CAPITAL_MARKETS.value: "Capital Markets Macroeconomic Agent",
    SectorEnum.AGRICULTURE_RURAL.value: "Agriculture & Rural Macroeconomic Agent",
    SectorEnum.LABOUR_EMPLOYMENT.value: "Labour & Employment Macroeconomic Agent",
}
```

### Task 1.5: Mount All Domain Sub-Apps in Unified Gateway
**Target File**: `backend/main.py`
Mount all 8 sub-apps:
```python
app.mount("/real-sector", real_app)
app.mount("/finance-sector", finance_app)
app.mount("/capital-markets", capital_app)
app.mount("/prices-sector", prices_app)
app.mount("/monetary-sector", monetary_app)
app.mount("/labour-sector", labour_app)
app.mount("/agriculture-sector", agriculture_app)
app.mount("/fiscal-sector", fiscal_app)
app.mount("/external-sector", external_app)
```

---

## Verification & Test Commands
Run your specific test files:
```powershell
.venv\Scripts\pytest backend/tests/test_data_deduplication.py -v
.venv\Scripts\pytest backend/tests/test_orchestrator_8_sectors.py -v
```
Verify all 27 original regression tests still pass:
```powershell
.venv\Scripts\pytest backend/tests -v
```

## Definition of Done (DoD)
- [ ] `GET /a2a/registry` returns exactly 8 registered `AgentCard` objects.
- [ ] `upsert_canonical_observation()` prevents duplicate rows when inserting the same indicator and period twice.
- [ ] LangGraph orchestrator correctly dispatches tasks to the dedicated domain agents for each sector.
- [ ] All 27 regression tests + your new unit tests pass with zero warnings/errors.
