"""DuckDB cache helpers for the Monetary Sector.

Owns the cache exception, dataset TTLs, row save/load, and freshness checks.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from monetary_sector import database as db
from monetary_sector.models import Citation, DataFreshness

logger = logging.getLogger(__name__)

class MonetaryDataUnavailableError(Exception):
    """Raised when neither the official DBIE MCP nor local cache has data."""


_DATASET_TTL_SECONDS: dict[str, int] = {
    "policy_rates": 600,
    "money_supply": 600,
    "system_liquidity": 600,
    "monetary_stance": 600,
}


def _prepare_cached_citation(citation_data: Any) -> Citation:

    if isinstance(citation_data, str):
        citation_data = json.loads(citation_data)
    if not isinstance(citation_data, dict):
        raise ValueError("Cached monetary observation has invalid citation metadata.")
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


def _is_legacy_seed(row: dict[str, Any]) -> bool:
    citation = row.get("citation")
    if isinstance(citation, str):
        try:
            citation = json.loads(citation)
        except json.JSONDecodeError:
            return False
    if not isinstance(citation, dict) or citation.get("freshness") != "cached":
        return False
    return citation.get("table_reference") in {
        "monetary_sector.r532_laf_operations",
        "monetary_sector.mpc_stance",
        "financial_sector.r531_key_rates",
        "financial_sector.r689_commercial_bank_survey",
    }


def _save_records(
    table: str, records: list[Any], tool_name: str, fetch_status: str = "upstream_snapshot"
) -> None:
    if not records:
        raise ValueError(f"{tool_name} returned no validated records.")
    fetched_at = datetime.now(timezone.utc)
    rows = [
        {
            **record.model_dump(mode="json", exclude={"citation"}),
            "citation": record.citation.model_dump_json(),
            "fetched_at": (fetched_at - timedelta(milliseconds=index)).isoformat(),
        }
        for index, record in enumerate(records)
    ]
    written = db.upsert_rows(table, rows)
    db.log_fetch(tool_name, fetch_status, rows_written=written)


def _load_cache(table: str, limit: int, record_type: Any, tool_name: str) -> list[Any]:
    try:
        rows = db.query_latest_rows(table, limit)
    except Exception as exc:
        raise MonetaryDataUnavailableError(
            f"{tool_name} unavailable: DBIE MCP failed and DuckDB cache could not be read."
        ) from exc
    rows = [row for row in rows if not _is_legacy_seed(row)]
    if not rows:
        raise MonetaryDataUnavailableError(
            f"{tool_name} unavailable: DBIE MCP failed and cache is empty."
        )
    records = []
    for row in rows:
        try:
            records.append(
                record_type(
                    **{key: value for key, value in row.items()
                       if key not in {"id", "citation", "fetched_at"}},
                    citation=_prepare_cached_citation(row.get("citation")),
                )
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Ignoring invalid cached %s row: %s", tool_name, exc)
    if not records:
        raise MonetaryDataUnavailableError(
            f"{tool_name} unavailable: no valid cached observations remain."
        )
    return records


# Fresh-cache TTL per dataset (seconds). Mirrors the capital sector's
# _rows_are_recent short-circuit: a query served within the TTL reuses the
# just-fetched rows with zero MCP spawns, so overlapping chat requests can no
# longer stampede uvx/npx. Explicit live-data requests bypass the TTL.


def _cached_rows_are_recent(table: str, max_age_seconds: int) -> bool:
    """True when the newest non-legacy cached row was fetched within the TTL."""
    try:
        rows = db.query_latest_rows(table, 1)
    except Exception:
        return False
    rows = [row for row in rows if not _is_legacy_seed(row)]
    if not rows:
        return False
    fetched_at = rows[0].get("fetched_at")
    if isinstance(fetched_at, str):
        try:
            fetched_at = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(fetched_at, datetime):
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched_at).total_seconds() <= max_age_seconds


def _load_fresh_cache(
    table: str, limit: int, record_type: Any, tool_name: str, max_age_seconds: int
) -> list[Any] | None:
    """Return validated cached rows when they are within TTL, else None."""
    if not _cached_rows_are_recent(table, max_age_seconds):
        return None
    try:
        return _load_cache(table, limit, record_type, tool_name)
    except Exception as exc:
        logger.warning("Fresh %s cache unreadable, going live: %s", tool_name, exc)
        return None
