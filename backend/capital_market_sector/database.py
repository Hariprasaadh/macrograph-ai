"""Capital Markets Sector DuckDB database initialisation and schema management."""
from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import duckdb

from capital_market_sector.config import capital_settings

logger = logging.getLogger(__name__)

_DB_PATH: Path = capital_settings.CAPITAL_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "nifty_snapshot",
    "market_history",
    "india_vix",
    "market_breadth",
    "gsec_yields",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    "CREATE SEQUENCE IF NOT EXISTS seq_nifty_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_mkt_hist_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_vix_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_breadth_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_gsec_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_cap_fetchlog_id START 1",

    """
    CREATE TABLE IF NOT EXISTS nifty_snapshot (
        id             BIGINT DEFAULT nextval('seq_nifty_id') PRIMARY KEY,
        period         VARCHAR NOT NULL UNIQUE,
        index_name     VARCHAR NOT NULL,
        open_price     DOUBLE,
        high_price     DOUBLE,
        low_price      DOUBLE,
        close_price    DOUBLE,
        change_points  DOUBLE,
        change_pct     DOUBLE,
        volume_shares  DOUBLE,
        turnover_cr    DOUBLE,
        citation       VARCHAR NOT NULL,
        fetched_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS market_history (
        id                 BIGINT DEFAULT nextval('seq_mkt_hist_id') PRIMARY KEY,
        period             VARCHAR NOT NULL UNIQUE,
        index_name         VARCHAR NOT NULL,
        close_price        DOUBLE,
        yoy_return_pct     DOUBLE,
        pe_ratio           DOUBLE,
        pb_ratio           DOUBLE,
        dividend_yield_pct DOUBLE,
        citation           VARCHAR NOT NULL,
        fetched_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS india_vix (
        id                BIGINT DEFAULT nextval('seq_vix_id') PRIMARY KEY,
        period            VARCHAR NOT NULL UNIQUE,
        vix_close         DOUBLE,
        vix_change_pct    DOUBLE,
        volatility_regime VARCHAR,
        citation          VARCHAR NOT NULL,
        fetched_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS market_breadth (
        id                    BIGINT DEFAULT nextval('seq_breadth_id') PRIMARY KEY,
        period                VARCHAR NOT NULL UNIQUE,
        total_stocks          INTEGER,
        advances_count        INTEGER,
        declines_count        INTEGER,
        unchanged_count       INTEGER,
        advance_decline_ratio DOUBLE,
        total_volume          BIGINT,
        citation              VARCHAR NOT NULL,
        fetched_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "ALTER TABLE market_breadth ADD COLUMN IF NOT EXISTS total_stocks INTEGER",
    "ALTER TABLE market_breadth ADD COLUMN IF NOT EXISTS total_volume BIGINT",

    """
    CREATE TABLE IF NOT EXISTS gsec_yields (
        id                           BIGINT DEFAULT nextval('seq_gsec_id') PRIMARY KEY,
        period                       VARCHAR NOT NULL UNIQUE,
        ten_year_gsec_yield_pct      DOUBLE,
        five_year_gsec_yield_pct     DOUBLE,
        two_year_gsec_yield_pct      DOUBLE,
        yield_curve_spread_2s10s_bps DOUBLE,
        citation                     VARCHAR NOT NULL,
        fetched_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id         BIGINT DEFAULT nextval('seq_cap_fetchlog_id') PRIMARY KEY,
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
    logger.info("Capital Markets sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    nifty_rows = query_latest_rows("nifty_snapshot", limit=1)
    if not nifty_rows:
        upsert_rows("nifty_snapshot", [{
            "period": "2024-09-30",
            "index_name": "NIFTY 50",
            "open_price": 25820.0,
            "high_price": 25950.0,
            "low_price": 25780.0,
            "close_price": 25810.85,
            "change_points": 35.5,
            "change_pct": 0.14,
            "volume_shares": 350000000.0,
            "turnover_cr": 45000.0,
            "citation": json.dumps({
                "source_agent": "capital_market_sector",
                "source_authority": "National Stock Exchange of India (NSE)",
                "document_title": "NSE Capital Market Daily Bhavcopy",
                "table_reference": "capital_market_sector.nifty_50_bhavcopy",
                "retrieval_url": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
                "observation_period": "2024-09-30",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    vix_rows = query_latest_rows("india_vix", limit=1)
    if not vix_rows:
        upsert_rows("india_vix", [{
            "period": "2024-09-30",
            "vix_close": 12.85,
            "vix_change_pct": -1.5,
            "volatility_regime": "Low",
            "citation": json.dumps({
                "source_agent": "capital_market_sector",
                "source_authority": "National Stock Exchange of India (NSE)",
                "document_title": "India Volatility Index (India VIX)",
                "table_reference": "capital_market_sector.india_vix",
                "retrieval_url": "https://mcp.nseindia.in/cmmkt/mcp",
                "observation_period": "2024-09-30",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    breadth_rows = query_latest_rows("market_breadth", limit=1)
    if not breadth_rows:
        upsert_rows("market_breadth", [{
            "period": "2024-09-30",
            "advances_count": 1450,
            "declines_count": 1120,
            "unchanged_count": 80,
            "advance_decline_ratio": 1.29,
            "citation": json.dumps({
                "source_agent": "capital_market_sector",
                "source_authority": "National Stock Exchange of India (NSE)",
                "document_title": "NSE Market Breadth Summary",
                "table_reference": "capital_market_sector.market_breadth",
                "retrieval_url": "https://mcp.nseindia.in/cmmkt/mcp",
                "observation_period": "2024-09-30",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    gsec_rows = query_latest_rows("gsec_yields", limit=1)
    if not gsec_rows:
        upsert_rows("gsec_yields", [{
            "period": "2024-09-30",
            "ten_year_gsec_yield_pct": 6.78,
            "five_year_gsec_yield_pct": 6.65,
            "two_year_gsec_yield_pct": 6.52,
            "yield_curve_spread_2s10s_bps": 26.0,
            "citation": json.dumps({
                "source_agent": "capital_market_sector",
                "source_authority": "Reserve Bank of India (RBI) / CCIL",
                "document_title": "Government Securities Yield Curve",
                "table_reference": "financial_sector.r531_gsec_yields",
                "retrieval_url": "https://data-api.dbie.rbihub.in/api/tables/financial_sector/r531_key_rates/rows",
                "observation_period": "2024-09-30",
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
        "nifty_snapshot": ["period"],
        "market_history": ["period"],
        "india_vix": ["period"],
        "market_breadth": ["period"],
        "gsec_yields": ["period"],
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
