"""Real Sector DuckDB database initialisation and schema management.

Owns the sector-dedicated DuckDB file (`real_sector.duckdb`).
Includes DDL, thread-safe connection pooling, baseline seeding, and JOIN operations
"""
from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import duckdb

from real_sector.config import real_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = real_settings.REAL_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "iip_sectoral",
    "iip_use_based",
    "core_industries",
    "manufacturing_gva",
    "market_context",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    # Sequences
    "CREATE SEQUENCE IF NOT EXISTS seq_iip_sec_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_iip_use_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_ici_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_gva_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_market_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_real_fetchlog_id START 1",

    # Table 1: MoSPI IIP Sectoral
    """
    CREATE TABLE IF NOT EXISTS iip_sectoral (
        id                     BIGINT DEFAULT nextval('seq_iip_sec_id') PRIMARY KEY,
        period                 VARCHAR NOT NULL UNIQUE,
        general_iip            DOUBLE,
        general_iip_yoy_pct    DOUBLE,
        mining_iip             DOUBLE,
        mining_yoy_pct         DOUBLE,
        manufacturing_iip      DOUBLE,
        manufacturing_yoy_pct  DOUBLE,
        electricity_iip        DOUBLE,
        electricity_yoy_pct    DOUBLE,
        citation               VARCHAR NOT NULL,
        fetched_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Table 2: MoSPI IIP Use-Based
    """
    CREATE TABLE IF NOT EXISTS iip_use_based (
        id                             BIGINT DEFAULT nextval('seq_iip_use_id') PRIMARY KEY,
        period                         VARCHAR NOT NULL UNIQUE,
        primary_goods_yoy_pct          DOUBLE,
        capital_goods_yoy_pct          DOUBLE,
        intermediate_goods_yoy_pct     DOUBLE,
        infrastructure_goods_yoy_pct   DOUBLE,
        consumer_durables_yoy_pct      DOUBLE,
        consumer_non_durables_yoy_pct  DOUBLE,
        citation                       VARCHAR NOT NULL,
        fetched_at                     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Table 3: DPIIT Eight Core Industries (ICI)
    """
    CREATE TABLE IF NOT EXISTS core_industries (
        id                        BIGINT DEFAULT nextval('seq_ici_id') PRIMARY KEY,
        period                    VARCHAR NOT NULL UNIQUE,
        overall_ici_yoy_pct       DOUBLE,
        coal_yoy_pct              DOUBLE,
        crude_oil_yoy_pct         DOUBLE,
        natural_gas_yoy_pct       DOUBLE,
        refinery_products_yoy_pct DOUBLE,
        fertilizers_yoy_pct       DOUBLE,
        steel_yoy_pct             DOUBLE,
        cement_yoy_pct            DOUBLE,
        electricity_yoy_pct       DOUBLE,
        citation                  VARCHAR NOT NULL,
        fetched_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Table 4: RBI DBIE Manufacturing GVA
    """
    CREATE TABLE IF NOT EXISTS manufacturing_gva (
        id                             BIGINT DEFAULT nextval('seq_gva_id') PRIMARY KEY,
        period                         VARCHAR NOT NULL UNIQUE,
        manufacturing_gva_real_yoy_pct DOUBLE,
        manufacturing_gva_cr           DOUBLE,
        manufacturing_share_in_gva_pct DOUBLE,
        citation                       VARCHAR NOT NULL,
        fetched_at                     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,


    # Table 6: Market Context (Listed Bellwethers)
    """
    CREATE TABLE IF NOT EXISTS market_context (
        id                      BIGINT DEFAULT nextval('seq_market_id') PRIMARY KEY,
        period                  VARCHAR NOT NULL UNIQUE,
        nifty_infra_change_pct  DOUBLE,
        nifty_metal_change_pct  DOUBLE,
        bellwethers_json        VARCHAR,
        citation                VARCHAR NOT NULL,
        fetched_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Table 7: Fetch Log
    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id           BIGINT DEFAULT nextval('seq_real_fetchlog_id') PRIMARY KEY,
        tool_name    VARCHAR NOT NULL,
        status       VARCHAR NOT NULL,
        rows_written INTEGER,
        error_msg    VARCHAR,
        logged_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


@contextmanager
def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Open a DuckDB connection acquiring _DB_LOCK for Windows file-lock safety."""
    _ensure_data_dir()
    with _DB_LOCK:
        con = duckdb.connect(str(_DB_PATH))
        try:
            yield con
        finally:
            con.close()


def initialise_schema(seed_baseline: bool = False) -> None:
    """Create all tables and indices if they do not yet exist."""
    _ensure_data_dir()
    with get_connection() as con:
        for stmt in _DDL_STATEMENTS:
            con.execute(stmt.strip())
    logger.info("Real sector DuckDB schema initialised at %s", _DB_PATH)


def seed_canonical_baseline() -> None:
    """No-op: All data must be fetched dynamically from official MCP servers."""
    pass



def upsert_rows(table: str, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into table using ON CONFLICT (period) DO UPDATE."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table!r}")

    if not rows:
        return 0

    serialised: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, (dict, list)):
                r[k] = json.dumps(v)
            elif isinstance(v, datetime):
                r[k] = v.isoformat()
        serialised.append(r)

    columns = [c for c in serialised[0].keys() if c != "id"]
    placeholders = ", ".join(["?" for _ in columns])
    col_list = ", ".join(columns)
    update_cols = [c for c in columns if c != "period"]
    set_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    with get_connection() as con:
        for row in serialised:
            values = [row[c] for c in columns]
            con.execute(
                f"""
                INSERT INTO {table} ({col_list})
                VALUES ({placeholders})
                ON CONFLICT (period) DO UPDATE SET {set_clause}
                """,
                values,
            )
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


def query_latest_rows(table: str, limit: int) -> list[dict[str, Any]]:
    """Return the most recently fetched rows from a cache table."""
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
        if "bellwethers_json" in d and isinstance(d["bellwethers_json"], str):
            try:
                d["bellwethers"] = json.loads(d["bellwethers_json"])
            except json.JSONDecodeError:
                d["bellwethers"] = []
        rows.append(d)
    return rows


def query_joined_real_indicators() -> list[dict[str, Any]]:
    """JOIN all real sector indicator tables by date/period in DuckDB (Step 5)."""
    with get_connection() as con:
        # Cross join / full outer coalesced join across monthly & quarterly series
        query = """
        SELECT 
            COALESCE(s.period, u.period, c.period) AS period,
            s.manufacturing_yoy_pct AS manufacturing_iip_yoy_pct,
            u.capital_goods_yoy_pct AS capital_goods_iip_yoy_pct,
            u.intermediate_goods_yoy_pct AS intermediate_goods_yoy_pct,
            u.consumer_durables_yoy_pct AS consumer_durables_yoy_pct,
            c.steel_yoy_pct AS core_steel_yoy_pct,
            c.cement_yoy_pct AS core_cement_yoy_pct,
            c.electricity_yoy_pct AS core_electricity_yoy_pct,
            c.coal_yoy_pct AS core_coal_yoy_pct,
            c.overall_ici_yoy_pct AS overall_ici_yoy_pct,
            g.manufacturing_gva_real_yoy_pct AS manufacturing_gva_yoy_pct,
            COALESCE(s.citation, c.citation) AS citation
        FROM iip_sectoral s
        FULL OUTER JOIN iip_use_based u ON s.period = u.period
        FULL OUTER JOIN core_industries c ON s.period = c.period
        LEFT JOIN (
            SELECT * FROM manufacturing_gva ORDER BY fetched_at DESC LIMIT 1
        ) g ON 1=1
        ORDER BY period DESC
        LIMIT 12
        """
        result = con.execute(query).fetchall()
        columns = [desc[0] for desc in con.description]

    rows = []
    for row in result:
        d = dict(zip(columns, row))
        if "citation" in d and isinstance(d["citation"], str):
            try:
                d["citation"] = json.loads(d["citation"])
            except json.JSONDecodeError:
                pass
        rows.append(d)
    return rows
