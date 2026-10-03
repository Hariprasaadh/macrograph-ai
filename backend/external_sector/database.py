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
    "remittances_invisibles",
    "external_debt",
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
    "CREATE SEQUENCE IF NOT EXISTS seq_remit_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_debt_id START 1",
    "CREATE SEQUENCE IF NOT EXISTS seq_ext_fetchlog_id START 1",
    (
        "CREATE TABLE IF NOT EXISTS forex_reserves ("
        " id BIGINT DEFAULT nextval('seq_forex_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " total_reserves_usd_mn DOUBLE, total_reserves_inr_cr DOUBLE, foreign_currency_assets_usd_mn DOUBLE,"
        " gold_reserves_usd_mn DOUBLE, sdrs_usd_mn DOUBLE, reserve_tranche_position_usd_mn DOUBLE,"
        " import_cover_months DOUBLE, citation VARCHAR NOT NULL, fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS trade_balance ("
        " id BIGINT DEFAULT nextval('seq_trade_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " exports_usd_bn DOUBLE, imports_usd_bn DOUBLE, trade_balance_usd_bn DOUBLE,"
        " oil_imports_usd_bn DOUBLE, non_oil_imports_usd_bn DOUBLE, oil_exports_usd_bn DOUBLE,"
        " non_oil_exports_usd_bn DOUBLE, services_surplus_usd_bn DOUBLE, citation VARCHAR NOT NULL,"
        " fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS bop ("
        " id BIGINT DEFAULT nextval('seq_bop_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " current_account_balance_usd_bn DOUBLE, current_account_to_gdp_pct DOUBLE,"
        " capital_account_balance_usd_bn DOUBLE, net_bop_usd_bn DOUBLE, services_balance_usd_bn DOUBLE,"
        " remittances_usd_bn DOUBLE, citation VARCHAR NOT NULL, fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS exchange_rates ("
        " id BIGINT DEFAULT nextval('seq_fx_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " usd_inr_rate DOUBLE, reer_40_basket DOUBLE, neer_40_basket DOUBLE, citation VARCHAR NOT NULL,"
        " fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS external_flows ("
        " id BIGINT DEFAULT nextval('seq_flows_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " net_fdi_usd_mn DOUBLE, net_fpi_usd_mn DOUBLE, ecb_usd_mn DOUBLE, nri_deposits_usd_mn DOUBLE,"
        " citation VARCHAR NOT NULL, fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS remittances_invisibles ("
        " id BIGINT DEFAULT nextval('seq_remit_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " private_transfers_net_usd_mn DOUBLE, receipts_usd_mn DOUBLE, payments_usd_mn DOUBLE,"
        " services_receipts_usd_mn DOUBLE, services_net_usd_mn DOUBLE, citation VARCHAR NOT NULL,"
        " fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS external_debt ("
        " id BIGINT DEFAULT nextval('seq_debt_id') PRIMARY KEY, period VARCHAR NOT NULL UNIQUE,"
        " total_debt_usd_bn DOUBLE, total_debt_inr_cr DOUBLE, general_government_usd_bn DOUBLE,"
        " short_term_debt_usd_bn DOUBLE, short_term_to_reserves_pct DOUBLE, debt_to_gdp_pct DOUBLE,"
        " citation VARCHAR NOT NULL, fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
    (
        "CREATE TABLE IF NOT EXISTS fetch_log ("
        " id BIGINT DEFAULT nextval('seq_ext_fetchlog_id') PRIMARY KEY, tool_name VARCHAR NOT NULL,"
        " status VARCHAR NOT NULL, rows_written INTEGER, error_msg VARCHAR,"
        " logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ),
]

_MIGRATION_STATEMENTS: list[str] = [
    "ALTER TABLE forex_reserves ADD COLUMN IF NOT EXISTS import_cover_months DOUBLE",
    "ALTER TABLE trade_balance ADD COLUMN IF NOT EXISTS oil_imports_usd_bn DOUBLE",
    "ALTER TABLE trade_balance ADD COLUMN IF NOT EXISTS non_oil_imports_usd_bn DOUBLE",
    "ALTER TABLE trade_balance ADD COLUMN IF NOT EXISTS oil_exports_usd_bn DOUBLE",
    "ALTER TABLE trade_balance ADD COLUMN IF NOT EXISTS non_oil_exports_usd_bn DOUBLE",
    "ALTER TABLE trade_balance ADD COLUMN IF NOT EXISTS services_surplus_usd_bn DOUBLE",
    "ALTER TABLE bop ADD COLUMN IF NOT EXISTS services_balance_usd_bn DOUBLE",
    "ALTER TABLE bop ADD COLUMN IF NOT EXISTS remittances_usd_bn DOUBLE",
    "ALTER TABLE external_flows ADD COLUMN IF NOT EXISTS ecb_usd_mn DOUBLE",
    "ALTER TABLE external_flows ADD COLUMN IF NOT EXISTS nri_deposits_usd_mn DOUBLE",
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
        for m_stmt in _MIGRATION_STATEMENTS:
            try:
                con.execute(m_stmt.strip())
            except Exception as exc:
                logger.debug("Migration statement skipped: %s (%s)", m_stmt, exc)
    logger.info("External sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    if not query_latest_rows("forex_reserves", limit=1):
        upsert_rows("forex_reserves", [{
            "period": "18-Sep-2026",
            "total_reserves_usd_mn": 765901.0,
            "total_reserves_inr_cr": 7342985.0,
            "foreign_currency_assets_usd_mn": 630980.0,
            "gold_reserves_usd_mn": 111292.0,
            "sdrs_usd_mn": 18200.0,
            "reserve_tranche_position_usd_mn": 5429.0,
            "import_cover_months": 11.8,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "RBI Weekly Statistical Supplement - Foreign Exchange Reserves",
                "table_reference": "external_sector.r574_foreign_exchange_reserves",
                "retrieval_url": "https://dbie.rbihub.in/data/forex-reserves.json",
                "observation_period": "18-Sep-2026",
                "fetched_at": now_iso,
                "freshness": "cached",
            }),
            "fetched_at": now_iso,
        }])

    if not query_latest_rows("trade_balance", limit=1):
        upsert_rows("trade_balance", [{
            "period": "2024-08",
            "exports_usd_bn": 34.7,
            "imports_usd_bn": 58.6,
            "trade_balance_usd_bn": -23.9,
            "oil_imports_usd_bn": 14.8,
            "non_oil_imports_usd_bn": 43.8,
            "oil_exports_usd_bn": 5.6,
            "non_oil_exports_usd_bn": 29.1,
            "services_surplus_usd_bn": 15.2,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Ministry of Commerce & Industry / RBI",
                "document_title": "India Foreign Trade Statistics",
                "table_reference": "external_sector.r433_india_s_foreign_trade_us_dollars",
                "retrieval_url": "https://data-api.dbie.rbihub.in/api/tables/external_sector/r433_india_s_foreign_trade_us_dollars/rows",
                "observation_period": "2024-08",
                "fetched_at": now_iso,
                "freshness": "cached",
            }),
            "fetched_at": now_iso,
        }])

    if not query_latest_rows("bop", limit=1):
        upsert_rows("bop", [{
            "period": "2024-Q1",
            "current_account_balance_usd_bn": -5.7,
            "current_account_to_gdp_pct": -0.6,
            "capital_account_balance_usd_bn": 23.5,
            "net_bop_usd_bn": 17.8,
            "services_balance_usd_bn": 42.1,
            "remittances_usd_bn": 31.2,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "Developments in India's Balance of Payments",
                "table_reference": "external_sector.ind_ovr_bop_rn",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-Q1",
                "fetched_at": now_iso,
                "freshness": "cached",
            }),
            "fetched_at": now_iso,
        }])

    if not query_latest_rows("remittances_invisibles", limit=1):
        upsert_rows("remittances_invisibles", [{
            "period": "2024-25",
            "private_transfers_net_usd_mn": 124555.8,
            "receipts_usd_mn": 135426.0,
            "payments_usd_mn": 10870.2,
            "services_receipts_usd_mn": 387540.5,
            "services_net_usd_mn": 188823.8,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI) / MoSPI",
                "document_title": "Invisibles by Category of Transactions - US Dollars",
                "table_reference": "mospi.rbi.indicator_9",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-25",
                "fetched_at": now_iso,
                "freshness": "cached",
            }),
            "fetched_at": now_iso,
        }])

    if not query_latest_rows("external_debt", limit=1):
        upsert_rows("external_debt", [{
            "period": "2024-12",
            "total_debt_usd_bn": 682.3,
            "total_debt_inr_cr": 5712400.0,
            "general_government_usd_bn": 158.4,
            "short_term_debt_usd_bn": 132.8,
            "short_term_to_reserves_pct": 18.9,
            "debt_to_gdp_pct": 18.7,
            "citation": json.dumps({
                "source_agent": "external_sector",
                "source_authority": "Reserve Bank of India (RBI) / MoSPI",
                "document_title": "External Debt of India - Quarterly",
                "table_reference": "mospi.rbi.indicator_27",
                "retrieval_url": "https://mcp.mospi.gov.in/",
                "observation_period": "2024-12",
                "fetched_at": now_iso,
                "freshness": "cached",
            }),
            "fetched_at": now_iso,
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
        "remittances_invisibles": ["period"],
        "external_debt": ["period"],
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
    try:
        with get_connection() as con:
            con.execute(
                "INSERT INTO fetch_log (tool_name, status, rows_written, error_msg) VALUES (?, ?, ?, ?)",
                [tool_name, status, rows_written, error_msg],
            )
    except Exception as exc:
        logger.warning("Failed to log fetch for %s: %s", tool_name, exc)


def query_latest_rows(table: str, limit: int) -> list[dict[str, Any]]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table!r}")

    order_clause = (
        "ORDER BY COALESCE(TRY_STRPTIME(period, '%d-%b-%Y'), TRY_STRPTIME(period, '%Y-%m-%d')) DESC, period DESC, fetched_at DESC"
        if table == "forex_reserves"
        else "ORDER BY period DESC, fetched_at DESC"
    )

    with get_connection() as con:
        result = con.execute(
            f"SELECT * FROM {table} {order_clause} LIMIT ?",
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
