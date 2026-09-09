---
name: canonical-data-ingestion
description: Procedures and validation standards for ingesting official macroeconomic series into the DuckDB Canonical Data Layer with SHA-256 provenance hashing.
---

# Canonical Data Ingestion Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoding observation values, dates, or estimates into codebase files or ingestion scripts is strictly prohibited.
- **Live API Ingestion**: Ingestion routines must execute against authenticated, verified live official APIs (MoSPI, RBI DBIE, SEBI, AMFI, DPIIT, Yahoo Finance).
- **Explicit Error Handling & Fail-Fast Policy**: If an external API is down, returns invalid payload schemas, or fails network calls, the ingestion engine **must raise an explicit ingestion error** (`{"status": "error", "error_code": "LIVE_INGESTION_FAILURE", "message": "Failed to ingest live series from <endpoint>: <details>"}`). It must **never** write dummy or hardcoded records to DuckDB.

## Domain Scope
Manages the ingestion, validation, and storage of official Indian macroeconomic time-series data:
1. **Source Authority Attribution**: Verifies official feeds from MoSPI, RBI DBIE, SEBI, AMFI, Office of Economic Adviser, and EIA/Markets.
2. **Canonical Transformation**: Maps heterogeneous source formats into standardized `CanonicalObservation` objects.
3. **Cryptographic Provenance Hashing**: Computes SHA-256 digests over `indicator_id:observation_period:value:unit:data_status` for auditability.
4. **Embedded DuckDB Persistence**: Ingests records into `macro_store.duckdb` while computing rolling Z-scores and percentile ranks.

## Standard Ingestion Pattern
```python
from core.data.schema import CanonicalObservation, DataStatusEnum, RevisionStatusEnum
from core.database.macro_store import macro_store

# 1. Instantiate Canonical Observation from verified live API payload
obs = CanonicalObservation(
    indicator_id="in.macro.prices.cpi_headline",
    observation_period="2025-01-01",
    value=4.26,
    unit="% YoY",
    data_status=DataStatusEnum.LIVE,
    revision_status=RevisionStatusEnum.FINAL,
    confidence=1.0,
    metadata={"source": "MoSPI Press Release API", "api_status": 200}
)

# 2. Persist to DuckDB Canonical Store
macro_store.insert_canonical_observation(obs)

# 3. Retrieve latest verified observation
latest = macro_store.get_latest_canonical_observation("in.macro.prices.cpi_headline")
```

## Data Quality Invariants
- Never insert null or negative values for non-negative indicators (GDP levels, price indices, yields).
- All observation timestamps must be ISO 8601 UTC.
- Every observation must link to an existing `CanonicalIndicator` entry in the ontology.
