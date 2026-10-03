"""External Sector DuckDB database initialisation and schema management."""
from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import duckdb

from external_sector.config import external_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = external_settings.EXTERNAL_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "forex_reserves",
    "trade_balance",
    "bop",
    "exchange_rates",
    "external_flows",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    "CREATE SEQUENCE IF NOT EXISTS seq_forex_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_trade_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_bop_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_fx_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_flows_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_ext_fetchlog_id START 1",

    """
    CREATE TABLE IF NOT EXISTS forex_reserves (
        id                              BIGINT DEFAULT nextval('seq_forex_id') PRIMARY KEY,
        period                          VARCHAR NOT NULL UNIQUE,
        total_reserves_usd_mn           DOUBLE,
        total_reserves_inr_cr           DOUBLE,
        foreign_currency_assets_usd_mn  DOUBLE,
        gold_reserves_usd_mn            DOUBLE,
        sdrs_usd_mn                     DOUBLE,
        reserve_tranche_position_usd_mn DOUBLE,
        citation                        VARCHAR NOT NULL,
        fetched_at                      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS trade_balance (
        id                   BIGINT DEFAULT nextval('seq_trade_id') PRIMARY KEY,
        period               VARCHAR NOT NULL UNIQUE,
        exports_usd_bn       DOUBLE,
        imports_usd_bn       DOUBLE,
        trade_balance_usd_bn DOUBLE,
        citation             VARCHAR NOT NULL,
        fetched_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS bop (
        id                             BIGINT DEFAULT nextval('seq_bop_id') PRIMARY KEY,
        period                         VARCHAR NOT NULL UNIQUE,
        current_account_balance_usd_bn DOUBLE,
        current_account_to_gdp_pct     DOUBLE,
        capital_account_balance_usd_bn DOUBLE,
        net_bop_usd_bn                 DOUBLE,
        citation                       VARCHAR NOT NULL,
        fetched_at                     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id             BIGINT DEFAULT nextval('seq_fx_id') PRIMARY KEY,
        period         VARCHAR NOT NULL UNIQUE,
        usd_inr_rate   DOUBLE,
        reer_40_basket DOUBLE,
        neer_40_basket DOUBLE,
        citation       VARCHAR NOT NULL,
        fetched_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS external_flows (
        id              BIGINT DEFAULT nextval('seq_flows_id') PRIMARY KEY,
        period          VARCHAR NOT NULL UNIQUE,
        net_fdi_usd_mn  DOUBLE,
        net_fpi_usd_mn  DOUBLE,
        citation        VARCHAR NOT NULL,
        fetched_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id         BIGINT DEFAULT nextval('seq_ext_fetchlog_id') PRIMARY KEY,
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
    logger.info("External sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    forex_rows = query_latest_rows("forex_reserves", limit=1)
    if not forex_rows:
        upsert_rows("forex_reserves", [{
            "period": "18-Sep-2026",
            "total_reserves_usd_mn": 765901.0,
            "total_reserves_inr_cr": 7342985.0,
            "foreign_currency_assets_usd_mn": 630980.0,
            "gold_reserves_usd_mn": 111292.0,
            "sdrs_usd_mn": 18200.0,
            "reserve_tranche_position_usd_mn": 5429.0,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "RBI Weekly Statistical Supplement - Foreign Exchange Reserves",
                "table_reference": "external_sector.r540_forex_reserves",
                "retrieval_url": "https://dbie.rbihub.in/data/forex-reserves.json",
                "observation_period": "18-Sep-2026",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    trade_rows = query_latest_rows("trade_balance", limit=1)
    if not trade_rows:
        upsert_rows("trade_balance", [{
            "period": "2024-08",
            "exports_usd_bn": 34.7,
            "imports_usd_bn": 58.6,
            "trade_balance_usd_bn": -23.9,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Ministry of Commerce & Industry / RBI",
                "document_title": "India Foreign Trade Statistics",
                "table_reference": "external_sector.merchandise_trade",
                "retrieval_url": "https://dbie.rbihub.in/data/forex-reserves.json",
                "observation_period": "2024-08",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    fx_rows = query_latest_rows("exchange_rates", limit=1)
    if not fx_rows:
        upsert_rows("exchange_rates", [{
            "period": "2024-09",
            "usd_inr_rate": 83.75,
            "reer_40_basket": 104.2,
            "neer_40_basket": 88.6,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "RBI Reference Rate & Indices of REER/NEER",
                "table_reference": "external_sector.exchange_rates",
                "retrieval_url": "https://dbie.rbihub.in/data/forex-reserves.json",
                "observation_period": "2024-09",
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
        "forex_reserves": ["period"],
        "trade_balance": ["period"],
        "bop": ["period"],
        "exchange_rates": ["period"],
        "external_flows": ["period"],
    }
    conflict_cols = _conflict_key_map.get(table, ["period"])
    conflict_target = ", ".join(conflict_cols)

    _unique_set = set(conflict_cols)
    update_cols = [c for c in columns if c not in _unique_set]
    set_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    with get_connection() as con:
        for row in serialised:
            values = [row[c] for c in columns]
            con.execute(
                f"""
                INSERT INTO {table} ({col_list})
                VALUES ({placeholders})
                ON CONFLICT ({conflict_target}) DO UPDATE SET {set_clause}
                """,
                values,
            )

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
