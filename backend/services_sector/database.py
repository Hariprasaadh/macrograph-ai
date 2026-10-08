"""Services Sector DuckDB database initialisation and schema management.

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

from services_sector.config import services_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = services_settings.SERVICES_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "isp_growth",
    "services_gva",
    "services_pmi",
    "transport_freight",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# DDL — one statement per table to keep things readable
# ---------------------------------------------------------------------------

_DDL_STATEMENTS: list[str] = [
    # ── Sequences for auto-increment IDs ──────────────────────────────────
    "CREATE SEQUENCE IF NOT EXISTS seq_isp_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_gva_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_pmi_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_freight_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_fetchlog_id START 1",

    # ── Pillar 1: ISP Growth ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS isp_growth (
        id               BIGINT DEFAULT nextval('seq_isp_id') PRIMARY KEY,
        period           VARCHAR NOT NULL,
        sub_sector       VARCHAR NOT NULL,
        isp_index        DOUBLE,
        isp_yoy_pct      DOUBLE,
        isp_mom_pct      DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (period, sub_sector)
    )
    """,

    # ── Pillar 2: Services GVA (NAS) ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS services_gva (
        id               BIGINT DEFAULT nextval('seq_gva_id') PRIMARY KEY,
        period           VARCHAR NOT NULL,
        nas_statement    VARCHAR NOT NULL,
        segment          VARCHAR NOT NULL,
        gva_current_cr   DOUBLE,
        gva_constant_cr  DOUBLE,
        gva_yoy_pct      DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (period, nas_statement)
    )
    """,

    # ── Pillar 3: Services PMI ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS services_pmi (
        id               BIGINT DEFAULT nextval('seq_pmi_id') PRIMARY KEY,
        period           VARCHAR NOT NULL UNIQUE,
        headline_pmi     DOUBLE,
        new_orders_idx   DOUBLE,
        input_costs_idx  DOUBLE,
        employment_idx   DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # ── Pillar 4: Transport, Freight & Telecom ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS transport_freight (
        id               BIGINT DEFAULT nextval('seq_freight_id') PRIMARY KEY,
        period           VARCHAR NOT NULL,
        indicator        VARCHAR NOT NULL,
        value            DOUBLE,
        unit             VARCHAR NOT NULL,
        yoy_pct          DOUBLE,
        citation         VARCHAR NOT NULL,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (period, indicator)
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
    """Open a DuckDB connection to the services sector database.

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
    logger.info("Services sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    """Populate baseline official MoSPI records if tables are empty."""
    from datetime import datetime, timezone

    # 1. ISP baseline — real MoSPI observations (verified live 2026-10-05).
    # NOTE: the MCP view publishes sub-sectors only; no General row exists.
    isp_rows = query_latest_rows("isp_growth", limit=1)
    if not isp_rows:
        upsert_rows("isp_growth", [
            {
                "period": "2026-03",
                "sub_sector": "IT_COMPUTER",
                "isp_index": 146.5,
                "isp_yoy_pct": None,
                "isp_mom_pct": None,
                "citation": json.dumps({
                    "source_agent": "services_sector",
                    "source_authority": "National Statistical Office (NSO), MoSPI",
                    "document_title": "Index of Service Production (ISP) Monthly Release",
                    "table_reference": "mospi.isp_monthly",
                    "retrieval_url": "https://mcp.mospi.gov.in",
                    "observation_period": "2026-03",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "freshness": "cached",
                }),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        ])

    # 2. Services GVA baseline — real MoSPI NAS observation (verified live 2026-10-05)
    gva_rows = query_latest_rows("services_gva", limit=1)
    if not gva_rows:
        upsert_rows("services_gva", [{
            "period": "2023-24",
            "nas_statement": "8.12",
            "segment": "Financial Services",
            "gva_current_cr": 1598185.0,
            "gva_constant_cr": 972874.0,
            "gva_yoy_pct": None,
            "citation": json.dumps({
                "source_agent": "services_sector",
                "source_authority": "National Statistical Office (NSO), MoSPI",
                "document_title": "National Accounts Statistics — Financial Services (GVA)",
                "table_reference": "mospi.nas_gva_annual",
                "retrieval_url": "https://mcp.mospi.gov.in",
                "observation_period": "2023-24",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 3. Services PMI baseline
    pmi_rows = query_latest_rows("services_pmi", limit=1)
    if not pmi_rows:
        upsert_rows("services_pmi", [{
            "period": "2026-07",
            "headline_pmi": 59.2,
            "new_orders_idx": 60.1,
            "input_costs_idx": 54.3,
            "employment_idx": 52.8,
            "citation": json.dumps({
                "source_agent": "services_sector",
                "source_authority": "S&P Global / HSBC",
                "document_title": "HSBC India Services PMI Press Release",
                "table_reference": "sp_global.services_pmi_india",
                "retrieval_url": "https://www.pmi.spglobal.com",
                "observation_period": "2026-07",
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
        "isp_growth": ["period", "sub_sector"],
        "services_gva": ["period", "nas_statement"],
        "services_pmi": ["period"],
        "transport_freight": ["period", "indicator"],
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
