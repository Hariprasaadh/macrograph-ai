"""Real Sector DuckDB database initialisation and schema management.

Owns the sector-dedicated DuckDB file (`real_sector.duckdb`).
Includes DDL, thread-safe connection pooling, baseline seeding, and JOIN operations
across IIP, Eight Core Industries, Manufacturing GVA, and OBICUS.
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
    "obicus_capacity",
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
    "CREATE SEQUENCE IF NOT EXISTS seq_obicus_id START 1",
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

    # Table 5: RBI DBIE OBICUS Capacity Utilization
    """
    CREATE TABLE IF NOT EXISTS obicus_capacity (
        id                           BIGINT DEFAULT nextval('seq_obicus_id') PRIMARY KEY,
        period                       VARCHAR NOT NULL UNIQUE,
        capacity_utilisation_pct     DOUBLE,
        order_books_growth_yoy_pct   DOUBLE,
        inventory_to_sales_ratio_pct DOUBLE,
        citation                     VARCHAR NOT NULL,
        fetched_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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


def initialise_schema(seed_baseline: bool = True) -> None:
    """Create all tables and indices if they do not yet exist, and seed baseline."""
    _ensure_data_dir()
    with get_connection() as con:
        for stmt in _DDL_STATEMENTS:
            con.execute(stmt.strip())
    logger.info("Real sector DuckDB schema initialised at %s", _DB_PATH)
    if seed_baseline:
        seed_canonical_baseline()


def seed_canonical_baseline() -> None:
    """Populate baseline official MoSPI, DPIIT, and RBI records if tables are empty."""
    # 1. IIP Sectoral
    iip_rows = query_latest_rows("iip_sectoral", limit=1)
    if not iip_rows:
        upsert_rows("iip_sectoral", [{
            "period": "2024-08",
            "general_iip": 145.2,
            "general_iip_yoy_pct": -0.1,
            "mining_iip": 109.8,
            "mining_yoy_pct": -4.3,
            "manufacturing_iip": 145.8,
            "manufacturing_yoy_pct": 1.0,
            "electricity_iip": 208.5,
            "electricity_yoy_pct": -3.7,
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": "Quick Estimates of Index of Industrial Production (IIP)",
                "table_reference": "mospi_iip_sectoral_2011_12",
                "retrieval_url": "https://mospi.gov.in/iip",
                "observation_period": "2024-08",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 2. IIP Use-Based
    use_rows = query_latest_rows("iip_use_based", limit=1)
    if not use_rows:
        upsert_rows("iip_use_based", [{
            "period": "2024-08",
            "primary_goods_yoy_pct": -2.6,
            "capital_goods_yoy_pct": 0.7,
            "intermediate_goods_yoy_pct": 3.0,
            "infrastructure_goods_yoy_pct": 1.9,
            "consumer_durables_yoy_pct": 5.2,
            "consumer_non_durables_yoy_pct": -4.5,
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": "IIP Use-Based Classification",
                "table_reference": "mospi_iip_use_based_2011_12",
                "retrieval_url": "https://mospi.gov.in/iip",
                "observation_period": "2024-08",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 3. Eight Core Industries
    ici_rows = query_latest_rows("core_industries", limit=1)
    if not ici_rows:
        upsert_rows("core_industries", [{
            "period": "2024-08",
            "overall_ici_yoy_pct": -1.8,
            "coal_yoy_pct": -8.1,
            "crude_oil_yoy_pct": -5.0,
            "natural_gas_yoy_pct": -3.6,
            "refinery_products_yoy_pct": -1.0,
            "fertilizers_yoy_pct": 3.2,
            "steel_yoy_pct": 4.5,
            "cement_yoy_pct": 3.0,
            "electricity_yoy_pct": -5.0,
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "DPIIT / Office of Economic Adviser",
                "document_title": "Index of Eight Core Industries (ICI)",
                "table_reference": "dpiit_eight_core_industries_2011_12",
                "retrieval_url": "https://eaindustry.nic.in/ici",
                "observation_period": "2024-08",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 4. Manufacturing GVA
    gva_rows = query_latest_rows("manufacturing_gva", limit=1)
    if not gva_rows:
        upsert_rows("manufacturing_gva", [{
            "period": "2024-Q1",
            "manufacturing_gva_real_yoy_pct": 7.0,
            "manufacturing_gva_cr": 724500.0,
            "manufacturing_share_in_gva_pct": 16.2,
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "National Statistical Office (NSO) / RBI DBIE",
                "document_title": "Quarterly Estimates of Gross Value Added (GVA)",
                "table_reference": "real_sector.quarterly_gva_by_economic_activity",
                "retrieval_url": "https://data-api.dbie.rbihub.in/api/tables/real_sector/quarterly_gva",
                "observation_period": "2024-Q1",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 5. OBICUS Capacity Utilization
    obicus_rows = query_latest_rows("obicus_capacity", limit=1)
    if not obicus_rows:
        upsert_rows("obicus_capacity", [{
            "period": "2024-Q1",
            "capacity_utilisation_pct": 74.0,
            "order_books_growth_yoy_pct": 6.8,
            "inventory_to_sales_ratio_pct": 48.2,
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "document_title": "Order Books, Inventories and Capacity Utilisation Survey (OBICUS)",
                "table_reference": "real_sector.obicus_capacity_utilisation_round_65",
                "retrieval_url": "https://dbie.rbihub.in/obicus",
                "observation_period": "2024-Q1",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "cached",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])

    # 6. Market Context Bellwethers
    market_rows = query_latest_rows("market_context", limit=1)
    if not market_rows:
        upsert_rows("market_context", [{
            "period": "2024-09-30",
            "nifty_infra_change_pct": 1.2,
            "nifty_metal_change_pct": -0.8,
            "bellwethers_json": json.dumps([
                {"symbol": "TATASTEEL.NS", "company_name": "Tata Steel Ltd", "sector_category": "Steel", "current_price": 164.5, "change_pct_1m": -1.2, "change_pct_1y": 28.4, "pe_ratio": 42.1},
                {"symbol": "JSWSTEEL.NS", "company_name": "JSW Steel Ltd", "sector_category": "Steel", "current_price": 985.0, "change_pct_1m": 0.5, "change_pct_1y": 24.1, "pe_ratio": 29.8},
                {"symbol": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Ltd", "sector_category": "Cement", "current_price": 11200.0, "change_pct_1m": 2.1, "change_pct_1y": 35.6, "pe_ratio": 46.2},
                {"symbol": "LT.NS", "company_name": "Larsen & Toubro Ltd", "sector_category": "Capital Goods & Infra", "current_price": 3650.0, "change_pct_1m": 1.8, "change_pct_1y": 26.5, "pe_ratio": 36.4},
                {"symbol": "BHEL.NS", "company_name": "Bharat Heavy Electricals Ltd", "sector_category": "Capital Goods", "current_price": 275.0, "change_pct_1m": -3.2, "change_pct_1y": 110.2, "pe_ratio": 85.0},
            ]),
            "citation": json.dumps({
                "source_agent": "real_sector",
                "source_authority": "National Stock Exchange of India (NSE) / Yahoo Finance",
                "document_title": "Industrial & Infrastructure Market Bellwethers",
                "table_reference": "nse_infrastructure_metal_capital_goods_basket",
                "retrieval_url": "https://www.nseindia.com",
                "observation_period": "2024-09-30",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "upstream_snapshot",
            }),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }])


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
            o.capacity_utilisation_pct AS capacity_utilisation_pct,
            COALESCE(s.citation, c.citation) AS citation
        FROM iip_sectoral s
        FULL OUTER JOIN iip_use_based u ON s.period = u.period
        FULL OUTER JOIN core_industries c ON s.period = c.period
        LEFT JOIN (
            SELECT * FROM manufacturing_gva ORDER BY fetched_at DESC LIMIT 1
        ) g ON 1=1
        LEFT JOIN (
            SELECT * FROM obicus_capacity ORDER BY fetched_at DESC LIMIT 1
        ) o ON 1=1
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
