"""DuckDB persistence for briefs; own tables inside the existing macro_store.duckdb (read-write, like MacroDataStore)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import duckdb

from ..database.macro_store import macro_store

_NEWS_TTL_SECONDS = 6 * 3600


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(macro_store.db_path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_briefs (
            brief_date VARCHAR PRIMARY KEY, headline VARCHAR, executive_summary VARCHAR,
            pillars_json VARCHAR, warnings_json VARCHAR, watch_today_json VARCHAR,
            provenance_json VARCHAR, llm_model VARCHAR, created_at VARCHAR
        )""")
    con.execute("""
        CREATE TABLE IF NOT EXISTS brief_news_cache (
            query_hash VARCHAR PRIMARY KEY, response_json VARCHAR, fetched_at VARCHAR
        )""")
    return con


def _row_to_brief(row: Any) -> Dict[str, Any]:
    return {
        "date": row[0], "headline": row[1], "executive_summary": row[2],
        "key_drivers": json.loads(row[3] or "[]"), "warnings": json.loads(row[4] or "[]"),
        "watch_today": json.loads(row[5] or "[]"), "provenance": json.loads(row[6] or "{}"),
        "llm_model": row[7], "created_at": row[8],
    }


_COLUMNS = ("brief_date, headline, executive_summary, pillars_json, warnings_json, "
            "watch_today_json, provenance_json, llm_model, created_at")


def save_brief(brief: Dict[str, Any]) -> None:
    with _connect() as con:
        con.execute(f"INSERT OR REPLACE INTO daily_briefs ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            brief["date"], brief["headline"], brief["executive_summary"],
            json.dumps(brief["key_drivers"]), json.dumps(brief["warnings"]), json.dumps(brief["watch_today"]),
            json.dumps(brief["provenance"]), brief.get("llm_model") or "", brief["created_at"],
        ))


def get_brief(brief_date: str) -> Optional[Dict[str, Any]]:
    with _connect() as con:
        row = con.execute(f"SELECT {_COLUMNS} FROM daily_briefs WHERE brief_date = ?", (brief_date,)).fetchone()
    return _row_to_brief(row) if row else None


def get_latest_brief() -> Optional[Dict[str, Any]]:
    with _connect() as con:
        row = con.execute(f"SELECT {_COLUMNS} FROM daily_briefs ORDER BY brief_date DESC LIMIT 1").fetchone()
    return _row_to_brief(row) if row else None


def list_briefs(limit: int = 7) -> List[Dict[str, Any]]:
    with _connect() as con:
        rows = con.execute(f"SELECT {_COLUMNS} FROM daily_briefs ORDER BY brief_date DESC LIMIT ?",
                           (max(1, min(limit, 60)),)).fetchall()
    return [_row_to_brief(r) for r in rows]


def cached_news_get(query_hash: str) -> Optional[Dict[str, Any]]:
    with _connect() as con:
        row = con.execute("SELECT response_json, fetched_at FROM brief_news_cache WHERE query_hash = ?",
                          (query_hash,)).fetchone()
    if not row:
        return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds()
    return json.loads(row[0]) if age < _NEWS_TTL_SECONDS else None


def cached_news_set(query_hash: str, response: Dict[str, Any]) -> None:
    with _connect() as con:
        con.execute("INSERT OR REPLACE INTO brief_news_cache VALUES (?, ?, ?)",
                    (query_hash, json.dumps(response), datetime.now(timezone.utc).isoformat()))
