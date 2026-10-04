"""Capital Markets Sector DuckDB database initialisation and schema management.

Maintains tables for all 10 domain responsibilities with strict parameterized SQL.
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

from capital_market_sector.config import capital_settings
from capital_market_sector.database_seed import get_canonical_baseline_rows

logger = logging.getLogger(__name__)

_DB_PATH: Path = capital_settings.CAPITAL_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "nifty_snapshot",
    "market_history",
    "india_vix",
    "market_breadth",
    "gsec_yields",
    "mutual_fund_flows",
    "fpi_flows",
    "corporate_earnings",
    "sectoral_performance",
    "primary_market_ipos",
    "investor_participation",
    "market_economy_linkages",
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
    "CREATE SEQUENCE IF NOT EXISTS seq_mf_flows_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_fpi_flows_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_corp_earn_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_sector_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_ipo_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_investor_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_linkage_id START 1",
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
    CREATE TABLE IF NOT EXISTS mutual_fund_flows (
        id                   BIGINT DEFAULT nextval('seq_mf_flows_id') PRIMARY KEY,
        period               VARCHAR NOT NULL UNIQUE,
        equity_inflows_cr    DOUBLE,
        sip_inflow_cr        DOUBLE,
        total_mf_aum_lakh_cr DOUBLE,
        net_inflow_cr        DOUBLE,
        citation             VARCHAR NOT NULL,
        fetched_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fpi_flows (
        id                        BIGINT DEFAULT nextval('seq_fpi_flows_id') PRIMARY KEY,
        period                    VARCHAR NOT NULL UNIQUE,
        fpi_gross_purchases_cr    DOUBLE,
        fpi_gross_sales_cr        DOUBLE,
        fpi_net_investment_cr     DOUBLE,
        fpi_net_investment_usd_mn DOUBLE,
        dii_net_investment_cr     DOUBLE,
        citation                  VARCHAR NOT NULL,
        fetched_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS corporate_earnings (
        id                 BIGINT DEFAULT nextval('seq_corp_earn_id') PRIMARY KEY,
        period             VARCHAR NOT NULL UNIQUE,
        index_name         VARCHAR NOT NULL,
        ttm_eps            DOUBLE,
        pe_ratio           DOUBLE,
        pb_ratio           DOUBLE,
        dividend_yield_pct DOUBLE,
        pat_growth_yoy_pct DOUBLE,
        citation           VARCHAR NOT NULL,
        fetched_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS sectoral_performance (
        id                    BIGINT DEFAULT nextval('seq_sector_id') PRIMARY KEY,
        period                VARCHAR NOT NULL UNIQUE,
        nifty_50_change_pct   DOUBLE,
        nifty_bank_change_pct DOUBLE,
        nifty_it_change_pct   DOUBLE,
        nifty_auto_change_pct DOUBLE,
        nifty_pharma_change_pct DOUBLE,
        nifty_fmcg_change_pct DOUBLE,
        leading_sector        VARCHAR,
        lagging_sector        VARCHAR,
        citation              VARCHAR NOT NULL,
        fetched_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS primary_market_ipos (
        id                     BIGINT DEFAULT nextval('seq_ipo_id') PRIMARY KEY,
        period                 VARCHAR NOT NULL UNIQUE,
        ipo_count              INTEGER,
        ipo_proceeds_cr        DOUBLE,
        qip_proceeds_cr        DOUBLE,
        rights_proceeds_cr     DOUBLE,
        total_equity_raised_cr DOUBLE,
        citation               VARCHAR NOT NULL,
        fetched_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS investor_participation (
        id                           BIGINT DEFAULT nextval('seq_investor_id') PRIMARY KEY,
        period                       VARCHAR NOT NULL UNIQUE,
        total_demat_accounts_cr      DOUBLE,
        monthly_demat_additions_lakh DOUBLE,
        retail_turnover_share_pct    DOUBLE,
        institutional_holding_pct    DOUBLE,
        citation                     VARCHAR NOT NULL,
        fetched_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS market_economy_linkages (
        id                       BIGINT DEFAULT nextval('seq_linkage_id') PRIMARY KEY,
        period                   VARCHAR NOT NULL UNIQUE,
        nifty_earnings_yield_pct DOUBLE,
        ten_year_gsec_yield_pct  DOUBLE,
        equity_risk_premium_bps  DOUBLE,
        market_cap_to_gdp_pct    DOUBLE,
        linkage_regime           VARCHAR,
        citation                 VARCHAR NOT NULL,
        fetched_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id           BIGINT DEFAULT nextval('seq_cap_fetchlog_id') PRIMARY KEY,
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
    baseline_tables = get_canonical_baseline_rows()
    for table_name, rows in baseline_tables.items():
        existing = query_latest_rows(table_name, limit=1)
        if not existing:
            upsert_rows(table_name, rows)


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

    conflict_cols = ["period"]
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
