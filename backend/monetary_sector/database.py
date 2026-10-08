"""Monetary Sector DuckDB database initialisation and schema management.

This module owns the monetary sector's dedicated DuckDB file.
No other sector may import from or write to this database.
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

from monetary_sector.config import monetary_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = monetary_settings.MONETARY_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "policy_rates",
    "money_supply",
    "system_liquidity",
    "monetary_stance",
    "fetch_log",
})

# Complete static statements per table: no SQL text is ever assembled from input.
_COUNT_SQL: dict[str, str] = {
    "policy_rates": "SELECT COUNT(*) FROM policy_rates",
    "money_supply": "SELECT COUNT(*) FROM money_supply",
    "system_liquidity": "SELECT COUNT(*) FROM system_liquidity",
    "monetary_stance": "SELECT COUNT(*) FROM monetary_stance",
}
_DELETE_SQL: dict[str, str] = {
    "policy_rates": "DELETE FROM policy_rates",
    "money_supply": "DELETE FROM money_supply",
    "system_liquidity": "DELETE FROM system_liquidity",
    "monetary_stance": "DELETE FROM monetary_stance",
}
_LATEST_ROWS_SQL: dict[str, str] = {
    "policy_rates": "SELECT * FROM policy_rates ORDER BY fetched_at DESC LIMIT ?",
    "money_supply": "SELECT * FROM money_supply ORDER BY fetched_at DESC LIMIT ?",
    "system_liquidity": "SELECT * FROM system_liquidity ORDER BY fetched_at DESC LIMIT ?",
    "monetary_stance": "SELECT * FROM monetary_stance ORDER BY fetched_at DESC LIMIT ?",
    "fetch_log": "SELECT * FROM fetch_log ORDER BY fetched_at DESC LIMIT ?",
}


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    "CREATE SEQUENCE IF NOT EXISTS seq_policy_rates_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_money_supply_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_sys_liquidity_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_mon_stance_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_mon_fetchlog_id START 1",

    """
    CREATE TABLE IF NOT EXISTS policy_rates (
        id                     BIGINT DEFAULT nextval('seq_policy_rates_id') PRIMARY KEY,
        period                 VARCHAR NOT NULL UNIQUE,
        repo_rate_pct          DOUBLE,
        reverse_repo_rate_pct  DOUBLE,
        sdf_rate_pct           DOUBLE,
        msf_rate_pct           DOUBLE,
        bank_rate_pct          DOUBLE,
        crr_pct                DOUBLE,
        slr_pct                DOUBLE,
        corridor_width_bps     DOUBLE,
        stance                 VARCHAR,
        rates_effective_from   VARCHAR,
        citation               VARCHAR NOT NULL,
        fetched_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS money_supply (
        id                      BIGINT DEFAULT nextval('seq_money_supply_id') PRIMARY KEY,
        period                  VARCHAR NOT NULL UNIQUE,
        currency_with_public_cr DOUBLE,
        demand_deposits_cr      DOUBLE,
        other_deposits_rbi_cr   DOUBLE,
        m1_cr                   DOUBLE,
        post_office_savings_cr  DOUBLE,
        m2_cr                   DOUBLE,
        time_deposits_cr        DOUBLE,
        m3_cr                   DOUBLE,
        m3_yoy_pct              DOUBLE,
        citation                VARCHAR NOT NULL,
        fetched_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS system_liquidity (
        id                    BIGINT DEFAULT nextval('seq_sys_liquidity_id') PRIMARY KEY,
        period                VARCHAR NOT NULL UNIQUE,
        net_laf_absorption_cr DOUBLE,
        laf_repo_cr           DOUBLE,
        laf_reverse_repo_cr   DOUBLE,
        msf_operations_cr     DOUBLE,
        liquidity_condition   VARCHAR,
        citation              VARCHAR NOT NULL,
        fetched_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS monetary_stance (
        id                      BIGINT DEFAULT nextval('seq_mon_stance_id') PRIMARY KEY,
        period                  VARCHAR NOT NULL UNIQUE,
        repo_rate_pct           DOUBLE,
        stance_label            VARCHAR,
        real_policy_rate_pct    DOUBLE,
        m3_growth_pct           DOUBLE,
        system_liquidity_status VARCHAR,
        citation                VARCHAR NOT NULL,
        fetched_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id         BIGINT DEFAULT nextval('seq_mon_fetchlog_id') PRIMARY KEY,
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
    if seed_baseline:
        raise ValueError("Monetary baseline seeding is disabled; only sourced observations may be stored.")
    _ensure_data_dir()
    with get_connection() as con:
        for stmt in _DDL_STATEMENTS:
            con.execute(stmt.strip())
        # Safe column migrations for existing tables
        for migration in [
            "ALTER TABLE policy_rates ADD COLUMN IF NOT EXISTS corridor_width_bps DOUBLE",
            "ALTER TABLE policy_rates ADD COLUMN IF NOT EXISTS stance VARCHAR",
            "ALTER TABLE policy_rates ADD COLUMN IF NOT EXISTS rates_effective_from VARCHAR",
        ]:
            try:
                con.execute(migration)
            except duckdb.Error as exc:
                logger.warning("Monetary schema migration skipped (%s): %s", migration, exc)
    logger.info("Monetary sector DuckDB schema initialised at %s", _DB_PATH)


def seed_canonical_baseline() -> None:
    raise ValueError("Monetary baseline seeding is disabled; only sourced observations may be stored.")


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
        "policy_rates": ["period"],
        "money_supply": ["period"],
        "system_liquidity": ["period"],
        "monetary_stance": ["period"],
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


_DATA_TABLES: tuple[str, ...] = (
    "policy_rates",
    "money_supply",
    "system_liquidity",
    "monetary_stance",
)


def clear_cached_tables(tables: list[str] | None = None) -> dict[str, int]:
    """Delete cached rows from the sector data tables (never the fetch_log audit).

    Used to prove the live-or-unavailable path on systems where MCP servers
    are unreachable: with no cache, failed live fetches raise instead of
    serving stale rows. Returns per-table deleted row counts and records the
    clear action itself in fetch_log.
    """
    targets = list(tables) if tables else list(_DATA_TABLES)
    for table in targets:
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"Invalid table: {table!r}")
        if table == "fetch_log":
            raise ValueError("The fetch_log audit table cannot be cleared.")
    cleared: dict[str, int] = {}
    with get_connection() as con:
        for table in targets:
            count = con.execute(_COUNT_SQL[table]).fetchone()
            deleted = int(count[0]) if count else 0
            con.execute(_DELETE_SQL[table])
            cleared[table] = deleted
        con.commit()
    log_fetch("clear_monetary_cache", "cache_cleared", rows_written=sum(cleared.values()))
    return cleared


def query_latest_rows(table: str, limit: int) -> list[dict[str, Any]]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table!r}")

    with get_connection() as con:
        result = con.execute(_LATEST_ROWS_SQL[table], [limit]).fetchall()
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
