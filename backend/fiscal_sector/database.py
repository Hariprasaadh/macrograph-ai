"""Fiscal Sector DuckDB database initialisation and schema management.

This module owns the sector-dedicated DuckDB file.
No other sector may import from or write to this database.

Schema design:
  - One table per data pillar (Union accounts, Sovereign debt, GST, MoSPI tax aggregates).
  - Mandatory JSON citation column on every table.
  - Parameterized queries with '?' placeholders exclusively.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import duckdb

from fiscal_sector.config import fiscal_settings
from fiscal_sector.seeds import seed_verified_baseline

logger = logging.getLogger(__name__)

_DB_PATH: Path = fiscal_settings.FISCAL_DB_PATH
_DB_LOCK: threading.Lock = threading.Lock()

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "union_fiscal_deficit",
    "general_govt_debt",
    "gst_collections",
    "mospi_tax_aggregates",
    "fetch_log",
})


def _ensure_data_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


_DDL_STATEMENTS: list[str] = [
    # Sequences
    "CREATE SEQUENCE IF NOT EXISTS seq_fiscal_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_debt_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_gst_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_mospi_tax_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_fiscal_log_id START 1",

    # Pillar 1: Union Accounts & Fiscal Deficit (CGA & Union Budget)
    """
    CREATE TABLE IF NOT EXISTS union_fiscal_deficit (
        id                           BIGINT DEFAULT nextval('seq_fiscal_id') PRIMARY KEY,
        period                       VARCHAR NOT NULL UNIQUE,
        revenue_receipts_cr          DOUBLE NOT NULL,
        tax_revenue_net_cr           DOUBLE NOT NULL,
        non_tax_revenue_cr           DOUBLE NOT NULL,
        non_debt_capital_receipts_cr DOUBLE NOT NULL DEFAULT 0.0,
        total_receipts_cr            DOUBLE NOT NULL,
        total_expenditure_cr         DOUBLE NOT NULL,
        revenue_expenditure_cr       DOUBLE NOT NULL,
        capital_expenditure_cr       DOUBLE NOT NULL,
        fiscal_deficit_cr            DOUBLE NOT NULL,
        fiscal_deficit_gdp_pct       DOUBLE,
        revenue_deficit_cr           DOUBLE,
        primary_deficit_cr           DOUBLE,
        citation                     VARCHAR NOT NULL,
        fetched_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Pillar 2: Sovereign Debt & International Balance (IMF WEO)
    """
    CREATE TABLE IF NOT EXISTS general_govt_debt (
        id                              BIGINT DEFAULT nextval('seq_debt_id') PRIMARY KEY,
        period                          VARCHAR NOT NULL UNIQUE,
        general_govt_gross_debt_gdp_pct DOUBLE NOT NULL,
        net_lending_borrowing_gdp_pct   DOUBLE NOT NULL,
        revenue_gdp_pct                 DOUBLE,
        expenditure_gdp_pct             DOUBLE,
        citation                        VARCHAR NOT NULL,
        fetched_at                      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Pillar 3: Goods & Services Tax (GST Collections)
    """
    CREATE TABLE IF NOT EXISTS gst_collections (
        id             BIGINT DEFAULT nextval('seq_gst_id') PRIMARY KEY,
        period         VARCHAR NOT NULL UNIQUE,
        gross_gst_cr   DOUBLE NOT NULL,
        cgst_cr        DOUBLE,
        sgst_cr        DOUBLE,
        igst_cr        DOUBLE,
        cess_cr        DOUBLE,
        yoy_growth_pct DOUBLE,
        citation       VARCHAR NOT NULL,
        fetched_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Pillar 4: MoSPI Product Taxes & Government Consumption (NAS)
    """
    CREATE TABLE IF NOT EXISTS mospi_tax_aggregates (
        id                BIGINT DEFAULT nextval('seq_mospi_tax_id') PRIMARY KEY,
        year              VARCHAR NOT NULL,
        indicator         VARCHAR NOT NULL,
        current_price_cr  DOUBLE NOT NULL,
        constant_price_cr DOUBLE,
        frequency         VARCHAR NOT NULL DEFAULT 'Annual',
        revision          VARCHAR,
        citation          VARCHAR NOT NULL,
        fetched_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (year, indicator)
    )
    """,

    # Fetch logging
    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id           BIGINT DEFAULT nextval('seq_fiscal_log_id') PRIMARY KEY,
        tool_name    VARCHAR NOT NULL,
        status       VARCHAR NOT NULL,
        rows_written INTEGER NOT NULL DEFAULT 0,
        error_msg    VARCHAR,
        fetched_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


@contextmanager
def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a thread-safe connection to the fiscal sector DuckDB."""
    _ensure_data_dir()
    with _DB_LOCK:
        conn = duckdb.connect(str(_DB_PATH))
        try:
            yield conn
        finally:
            conn.close()


def initialise_schema(seed_baseline: bool = True) -> None:
    """Create all tables and sequences if not already present."""
    with get_connection() as conn:
        for stmt in _DDL_STATEMENTS:
            conn.execute(stmt)
        if seed_baseline:
            seed_verified_baseline(conn)
    logger.info("Fiscal sector DuckDB initialised at %s", _DB_PATH)


def upsert_rows(table: str, rows: list[dict[str, Any]]) -> int:
    """Insert or replace rows in the specified table. Parameterized strictly."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not in _ALLOWED_TABLES")
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_str = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))

    if table == "union_fiscal_deficit":
        conflict_col = "period"
    elif table == "general_govt_debt":
        conflict_col = "period"
    elif table == "gst_collections":
        conflict_col = "period"
    elif table == "mospi_tax_aggregates":
        conflict_col = "year, indicator"
    else:
        conflict_col = "id"

    update_cols = [c for c in columns if c not in ("id", "period", "year", "indicator")]
    update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols]) if update_cols else "fetched_at = CURRENT_TIMESTAMP"

    sql = f"""
    INSERT INTO {table} ({col_str})
    VALUES ({placeholders})
    ON CONFLICT ({conflict_col}) DO UPDATE SET {update_str}
    """

    with get_connection() as conn:
        for r in rows:
            values = [r[c] for c in columns]
            conn.execute(sql, values)

    return len(rows)


def log_fetch(tool_name: str, status: str, rows_written: int = 0, error_msg: str | None = None) -> None:
    """Log data fetch status to fetch_log table."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO fetch_log (tool_name, status, rows_written, error_msg) VALUES (?, ?, ?, ?)",
                [tool_name, status, rows_written, error_msg]
            )
    except Exception as exc:
        logger.warning("Failed to log fetch in DuckDB: %s", exc)


def query_fiscal_deficit(lookback_records: int = 5) -> list[dict[str, Any]]:
    """Return the most recent Union fiscal deficit records."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT period, revenue_receipts_cr, tax_revenue_net_cr, non_tax_revenue_cr,
                   non_debt_capital_receipts_cr, total_receipts_cr, total_expenditure_cr,
                   revenue_expenditure_cr, capital_expenditure_cr, fiscal_deficit_cr,
                   fiscal_deficit_gdp_pct, revenue_deficit_cr, primary_deficit_cr,
                   citation, fetched_at
            FROM union_fiscal_deficit
            ORDER BY id DESC
            LIMIT ?
            """,
            [lookback_records]
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def query_general_govt_debt(lookback_records: int = 10) -> list[dict[str, Any]]:
    """Return sovereign debt records."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT period, general_govt_gross_debt_gdp_pct, net_lending_borrowing_gdp_pct,
                   revenue_gdp_pct, expenditure_gdp_pct, citation, fetched_at
            FROM general_govt_debt
            ORDER BY period ASC
            LIMIT ?
            """,
            [lookback_records]
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def query_gst_collections(lookback_months: int = 12) -> list[dict[str, Any]]:
    """Return GST collections."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT period, gross_gst_cr, cgst_cr, sgst_cr, igst_cr, cess_cr,
                   yoy_growth_pct, citation, fetched_at
            FROM gst_collections
            ORDER BY period DESC
            LIMIT ?
            """,
            [lookback_months]
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def query_mospi_tax_aggregates(lookback_records: int = 5) -> list[dict[str, Any]]:
    """Return MoSPI product taxes and aggregates."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT year, indicator, current_price_cr, constant_price_cr, frequency,
                   revision, citation, fetched_at
            FROM mospi_tax_aggregates
            ORDER BY year DESC
            LIMIT ?
            """,
            [lookback_records]
        )
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
