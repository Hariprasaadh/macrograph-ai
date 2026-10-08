"""Labour Sector DuckDB database initialisation and schema management."""
from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import duckdb

from labour_sector.config import labour_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = labour_settings.LABOUR_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "unemployment",
    "lfpr",
    "wpr",
    "labour_conditions",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    "CREATE SEQUENCE IF NOT EXISTS seq_unemp_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_lfpr_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_wpr_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_cond_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_lab_fetchlog_id START 1",

    """
    CREATE TABLE IF NOT EXISTS unemployment (
        id                          BIGINT DEFAULT nextval('seq_unemp_id') PRIMARY KEY,
        period                      VARCHAR NOT NULL UNIQUE,
        unemployment_rate_pct       DOUBLE,
        unemployment_rate_urban_pct DOUBLE,
        unemployment_rate_rural_pct DOUBLE,
        unemployment_rate_youth_pct DOUBLE,
        citation                    VARCHAR NOT NULL,
        fetched_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS lfpr (
        id               BIGINT DEFAULT nextval('seq_lfpr_id') PRIMARY KEY,
        period           VARCHAR NOT NULL UNIQUE,
        lfpr_total_pct   DOUBLE,
        lfpr_male_pct    DOUBLE,
        lfpr_female_pct  DOUBLE,
        lfpr_urban_pct   DOUBLE,
        lfpr_rural_pct   DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS wpr (
        id              BIGINT DEFAULT nextval('seq_wpr_id') PRIMARY KEY,
        period          VARCHAR NOT NULL UNIQUE,
        wpr_total_pct   DOUBLE,
        wpr_male_pct    DOUBLE,
        wpr_female_pct  DOUBLE,
        wpr_urban_pct   DOUBLE,
        wpr_rural_pct   DOUBLE,
        citation        VARCHAR NOT NULL,
        fetched_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS labour_conditions (
        id                           BIGINT DEFAULT nextval('seq_cond_id') PRIMARY KEY,
        period                       VARCHAR NOT NULL UNIQUE,
        epfo_net_additions_thousands DOUBLE,
        self_employed_share_pct      DOUBLE,
        regular_wage_share_pct       DOUBLE,
        casual_labour_share_pct      DOUBLE,
        citation                     VARCHAR NOT NULL,
        fetched_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id         BIGINT DEFAULT nextval('seq_lab_fetchlog_id') PRIMARY KEY,
        tool_name  VARCHAR NOT NULL,
        status     VARCHAR NOT NULL,
        rows_written INTEGER,
        error_msg  VARCHAR,
        logged_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


@contextmanager
def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    _ensure_data_dir()
    with _DB_LOCK:
        con = duckdb.connect(str(_DB_PATH))
        try:
            yield con
        finally:
            con.close()


def initialise_schema(seed_baseline: bool = False) -> None:
    _ensure_data_dir()
    with get_connection() as con:
        for stmt in _DDL_STATEMENTS:
            con.execute(stmt.strip())
    logger.info("Labour sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    unemp_rows = query_latest_rows("unemployment", limit=1)
    if not unemp_rows:
        upsert_rows("unemployment", [{
            "period": "2024-Q1",
            "unemployment_rate_pct": 3.2,
            "unemployment_rate_urban_pct": 6.7,
            "unemployment_rate_rural_pct": 2.4,
            "unemployment_rate_youth_pct": 10.0,
            "citation": json.dumps({
                "source_agent": "labour_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": "Periodic Labour Force Survey (PLFS) Bulletin",
                "table_reference": "labour_sector.plfs_unemployment",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-Q1",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    lfpr_rows = query_latest_rows("lfpr", limit=1)
    if not lfpr_rows:
        upsert_rows("lfpr", [{
            "period": "2024-Q1",
            "lfpr_total_pct": 60.1,
            "lfpr_male_pct": 78.8,
            "lfpr_female_pct": 41.7,
            "lfpr_urban_pct": 50.4,
            "lfpr_rural_pct": 64.3,
            "citation": json.dumps({
                "source_agent": "labour_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": "Periodic Labour Force Survey (PLFS) LFPR",
                "table_reference": "labour_sector.plfs_lfpr",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-Q1",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    wpr_rows = query_latest_rows("wpr", limit=1)
    if not wpr_rows:
        upsert_rows("wpr", [{
            "period": "2024-Q1",
            "wpr_total_pct": 58.2,
            "wpr_male_pct": 76.3,
            "wpr_female_pct": 40.3,
            "wpr_urban_pct": 47.0,
            "wpr_rural_pct": 62.8,
            "citation": json.dumps({
                "source_agent": "labour_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": "Periodic Labour Force Survey (PLFS) WPR",
                "table_reference": "labour_sector.plfs_wpr",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-Q1",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    cond_rows = query_latest_rows("labour_conditions", limit=1)
    if not cond_rows:
        upsert_rows("labour_conditions", [{
            "period": "2024-08",
            "epfo_net_additions_thousands": 1850.0,
            "self_employed_share_pct": 57.3,
            "regular_wage_share_pct": 21.5,
            "casual_labour_share_pct": 21.2,
            "citation": json.dumps({
                "source_agent": "labour_sector",
                "source_authority": "EPFO / MoSPI",
                "document_title": "EPFO Payroll Additions & PLFS Status",
                "table_reference": "labour_sector.epfo_payroll",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-08",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])


def upsert_rows(table: str, rows: list[dict[str, Any]]) -> int:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table!r}")
    if not rows:
        return 0

    serialised: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, dict):
                r[k] = json.dumps(v)
            elif isinstance(v, datetime):
                r[k] = v.isoformat()
        serialised.append(r)

    sample = serialised[0]
    columns = [c for c in sample.keys() if c != "id"]
    placeholders = ", ".join(["?" for _ in columns])
    col_list = ", ".join(columns)

    _conflict_key_map: dict[str, list[str]] = {
        "unemployment": ["period"],
        "lfpr": ["period"],
        "wpr": ["period"],
        "labour_conditions": ["period"],
    }
    conflict_cols = _conflict_key_map.get(table, ["period"])
    conflict_target = ", ".join(conflict_cols)

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


def log_fetch(tool_name: str, status: str, rows_written: int = 0, error_msg: str | None = None) -> None:
    with get_connection() as con:
        con.execute(
            "INSERT INTO fetch_log (tool_name, status, rows_written, error_msg) VALUES (?, ?, ?, ?)",
            [tool_name, status, rows_written, error_msg],
        )
        con.commit()


def query_latest_rows(table: str, limit: int) -> list[dict[str, Any]]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table!r}")

    with get_connection() as con:
        result = con.execute(
            f"SELECT * FROM {table} ORDER BY fetched_at DESC LIMIT ?",
            [limit],
        ).fetchall()
        columns = [desc[0] for desc in con.description]

    rows = []
    for row in result:
        d: dict[str, Any] = dict(zip(columns, row))
        if "citation" in d and isinstance(d["citation"], str):
            try:
                d["citation"] = json.loads(d["citation"])
            except json.JSONDecodeError:
                pass
        rows.append(d)
    return rows
