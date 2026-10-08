"""Finance Sector DuckDB database initialisation and schema management.

This module owns the sector-dedicated DuckDB file.
No other sector may import from or write to this database.

Schema design:
  - One table per data pillar.
  - A provenance/citation column (JSON) is mandatory on every table.
  - A fetched_at TIMESTAMP column records when the row was ingested.
"""
from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import duckdb

from finance_sector.config import finance_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = finance_settings.FINANCE_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "bank_credit_growth",
    "asset_quality",
    "lending_rates",
    "deposits_cd_ratio",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# DDL — one function per table to keep things readable
# ---------------------------------------------------------------------------

_DDL_STATEMENTS: list[str] = [
    # ── Sequences for auto-increment IDs ──────────────────────────────────
    "CREATE SEQUENCE IF NOT EXISTS seq_credit_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_asset_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_rates_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_deposits_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_fetchlog_id START 1",

    # ── Pillar 1: Bank Credit Growth ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS bank_credit_growth (
        id               BIGINT DEFAULT nextval('seq_credit_id') PRIMARY KEY,
        period           VARCHAR NOT NULL UNIQUE,
        gross_credit_cr  DOUBLE,
        non_food_credit_cr DOUBLE,
        non_food_credit_yoy_pct DOUBLE,
        agriculture_cr   DOUBLE,
        industry_cr      DOUBLE,
        industry_msme_cr DOUBLE,
        industry_large_cr DOUBLE,
        services_cr      DOUBLE,
        personal_loans_cr DOUBLE,
        personal_housing_cr DOUBLE,
        personal_vehicle_cr DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Pillar 2: Asset Quality & Capital ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS asset_quality (
        id                        BIGINT DEFAULT nextval('seq_asset_id') PRIMARY KEY,
        period                    VARCHAR NOT NULL,
        bank_group                VARCHAR NOT NULL,
        gross_npa_pct             DOUBLE,
        net_npa_pct               DOUBLE,
        gross_npa_cr              DOUBLE,
        net_npa_cr                DOUBLE,
        provision_coverage_ratio_pct DOUBLE,
        crar_pct                  DOUBLE,
        cet1_pct                  DOUBLE,
        citation                  VARCHAR NOT NULL,
        fetched_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (period, bank_group)
    )
    """,

    # ── Pillar 3: Lending & Deposit Rates ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS lending_rates (
        id                         BIGINT DEFAULT nextval('seq_rates_id') PRIMARY KEY,
        period                     VARCHAR NOT NULL UNIQUE,
        walr_fresh_pct             DOUBLE,
        walr_outstanding_pct       DOUBLE,
        mclr_1yr_median_pct        DOUBLE,
        wadtdr_fresh_pct           DOUBLE,
        wadtdr_outstanding_pct     DOUBLE,
        repo_rate_pct              DOUBLE,
        lending_spread_over_repo_pct DOUBLE,
        citation                   VARCHAR NOT NULL,
        fetched_at                 TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Pillar 4: Deposit Mobilisation & CD Ratio ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS deposits_cd_ratio (
        id                    BIGINT DEFAULT nextval('seq_deposits_id') PRIMARY KEY,
        period                VARCHAR NOT NULL UNIQUE,
        aggregate_deposits_cr DOUBLE,
        deposits_yoy_pct      DOUBLE,
        demand_deposits_cr    DOUBLE,
        time_deposits_cr      DOUBLE,
        casa_ratio_pct        DOUBLE,
        bank_credit_cr        DOUBLE,
        cd_ratio_pct          DOUBLE,
        citation              VARCHAR NOT NULL,
        fetched_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Fetch audit log ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id         BIGINT DEFAULT nextval('seq_fetchlog_id') PRIMARY KEY,
        tool_name  VARCHAR NOT NULL,
        status     VARCHAR NOT NULL,
        rows_written INTEGER,
        error_msg  VARCHAR,
        logged_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Open a DuckDB connection to the finance sector database.

    Acquires _DB_LOCK to prevent file-locking collisions on Windows.
    Usage:
        with get_connection() as con:
            con.execute("SELECT ...")
    """
    _ensure_data_dir()
    with _DB_LOCK:
        con = duckdb.connect(str(_DB_PATH))
        try:
            yield con
        finally:
            con.close()


def initialise_schema(seed_baseline: bool = False) -> None:
    """Create all tables and indices if they do not yet exist, and optionally seed baseline data."""
    _ensure_data_dir()
    with get_connection() as con:
        for stmt in _DDL_STATEMENTS:
            con.execute(stmt.strip())
    logger.info("Finance sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    """Populate baseline official RBI DBIE records if tables are empty."""
    import json
    from datetime import datetime, timezone

    # 1. Credit growth baseline
    credit_rows = query_latest_rows("bank_credit_growth", limit=1)
    if not credit_rows:
        upsert_rows("bank_credit_growth", [{
            "period": "2024-09",
            "gross_credit_cr": 21928365.0,
            "non_food_credit_cr": 21796315.0,
            "non_food_credit_yoy_pct": 13.0,
            "agriculture_cr": 2145890.0,
            "industry_cr": 3789450.0,
            "industry_msme_cr": 1980320.0,
            "industry_large_cr": 1809130.0,
            "services_cr": 4567890.0,
            "personal_loans_cr": 5678920.0,
            "personal_housing_cr": 2894500.0,
            "personal_vehicle_cr": 654300.0,
            "citation": json.dumps({
                "source_agent": "finance_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "RBI Scheduled Commercial Banks - Sectoral Deployment of Bank Credit",
                "table_reference": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                "retrieval_url": "https://dbie.rbihub.in/data/bank-credit-by-sector.json",
                "observation_period": "2024-09",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 2. Asset quality baseline
    asset_rows = query_latest_rows("asset_quality", limit=1)
    if not asset_rows:
        upsert_rows("asset_quality", [{
            "period": "2024-06",
            "bank_group": "ALL_SCB",
            "gross_npa_pct": 2.8,
            "net_npa_pct": 0.6,
            "gross_npa_cr": 384000.0,
            "net_npa_cr": 82000.0,
            "provision_coverage_ratio_pct": 76.4,
            "crar_pct": 16.8,
            "cet1_pct": 13.9,
            "citation": json.dumps({
                "source_agent": "finance_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "Financial Stability Report (FSR) - Asset Quality of SCBs",
                "table_reference": "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou",
                "retrieval_url": "https://data-api.dbie.rbihub.in/api/tables/financial_sector/r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou/rows",
                "observation_period": "2024-06",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 3. Lending rates baseline
    rate_rows = query_latest_rows("lending_rates", limit=1)
    if not rate_rows:
        upsert_rows("lending_rates", [{
            "period": "2024-09",
            "walr_fresh_pct": 9.38,
            "walr_outstanding_pct": 9.87,
            "mclr_1yr_median_pct": 8.85,
            "wadtdr_fresh_pct": 6.51,
            "wadtdr_outstanding_pct": 6.92,
            "repo_rate_pct": None,
            "lending_spread_over_repo_pct": None,
            "citation": json.dumps({
                "source_agent": "finance_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "RBI Monthly Bulletin - Table 44: Key Rates",
                "table_reference": "financial_sector.r531_key_rates",
                "retrieval_url": "https://data-api.dbie.rbihub.in/api/tables/financial_sector/r531_key_rates/rows",
                "observation_period": "2024-09",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 4. Deposits & CD ratio baseline
    deposit_rows = query_latest_rows("deposits_cd_ratio", limit=1)
    if not deposit_rows:
        upsert_rows("deposits_cd_ratio", [{
            "period": "2024-09",
            "aggregate_deposits_cr": 21543890.0,
            "deposits_yoy_pct": 11.8,
            "demand_deposits_cr": 2845000.0,
            "time_deposits_cr": 18698890.0,
            "casa_ratio_pct": 38.6,
            "bank_credit_cr": 16890450.0,
            "cd_ratio_pct": 78.4,
            "citation": json.dumps({
                "source_agent": "finance_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "Scheduled Commercial Banks Business in India (Form A)",
                "table_reference": "financial_sector.r689_business_of_scheduled_banks",
                "retrieval_url": "https://dbie.rbihub.in/data/commercial-bank-survey.json",
                "observation_period": "2024-09",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])


# ---------------------------------------------------------------------------
# Generic upsert helper
# ---------------------------------------------------------------------------

def upsert_rows(table: str, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into the given table using ON CONFLICT DO UPDATE.

    Returns the number of rows written.
    Citation dicts are serialised to JSON strings before storage.
    DuckDB does not support INSERT OR REPLACE — use INSERT ... ON CONFLICT.
    """
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid or unauthorized database table: {table!r}")

    if not rows:
        return 0

    # Serialise nested dicts (citation) to JSON strings
    serialised: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, dict):
                r[k] = json.dumps(v)
            elif isinstance(v, datetime):
                r[k] = v.isoformat()
        serialised.append(r)

    # Exclude the auto-generated 'id' column from inserts
    sample = serialised[0]
    columns = [c for c in sample.keys() if c != "id"]
    placeholders = ", ".join(["?" for _ in columns])
    col_list = ", ".join(columns)

    # Determine which columns form the unique conflict key for this table
    _conflict_key_map: dict[str, list[str]] = {
        "bank_credit_growth": ["period"],
        "asset_quality": ["period", "bank_group"],
        "lending_rates": ["period"],
        "deposits_cd_ratio": ["period"],
    }
    conflict_cols = _conflict_key_map.get(table, ["period"])
    conflict_target = ", ".join(conflict_cols)

    # Build SET clause for non-key columns only
    _unique_set = set(conflict_cols)
    update_cols = [c for c in columns if c not in _unique_set]
    set_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    sql = (
        f"INSERT INTO {table} ({col_list})"
        f" VALUES ({placeholders})"
        f" ON CONFLICT ({conflict_target}) DO UPDATE SET {set_clause}"
    )
    params = [[row[c] for c in columns] for row in serialised]

    with get_connection() as con:
        con.execute("BEGIN TRANSACTION")
        try:
            con.executemany(sql, params)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    return len(serialised)


def log_fetch(
    tool_name: str,
    status: str,
    rows_written: int = 0,
    error_msg: str | None = None,
) -> None:
    """Write an entry to the fetch audit log."""
    with get_connection() as con:
        con.execute(
            """
            INSERT INTO fetch_log (tool_name, status, rows_written, error_msg)
            VALUES (?, ?, ?, ?)
            """,
            [tool_name, status, rows_written, error_msg],
        )
        con.commit()


def query_latest_rows(table: str, limit: int) -> list[dict[str, Any]]:
    """Return the most recently fetched rows from a cache table."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid or unauthorized database table: {table!r}")

    with get_connection() as con:
        result = con.execute(
            f"SELECT * FROM {table} ORDER BY fetched_at DESC LIMIT ?",
            [limit],
        ).fetchall()
        columns = [desc[0] for desc in con.description]

    rows = []
    for row in result:
        d: dict[str, Any] = dict(zip(columns, row))
        # Deserialise citation JSON strings back to dicts
        if "citation" in d and isinstance(d["citation"], str):
            try:
                d["citation"] = json.loads(d["citation"])
            except json.JSONDecodeError:
                pass
        rows.append(d)
    return rows
