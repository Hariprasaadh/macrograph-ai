"""Async client for RBI data exposed by the official RBIH DBIE MCP."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from monetary_sector import database as db
from monetary_sector.config import monetary_settings
from monetary_sector.models import (
    Citation,
    DataFreshness,
    MoneySupplyRecord,
    MonetaryStanceRecord,
    PolicyRatesRecord,
    SystemLiquidityRecord,
)
from monetary_sector.parsers import (
    parse_money_supply,
    parse_policy_rates,
    parse_system_liquidity,
)

logger = logging.getLogger(__name__)

_MCP_PACKAGE = "@reserve-bank-innovation-hub/dbie-mcp@0.1.0"
_STDIO_LINE_LIMIT = 16 * 1024 * 1024
_TABLES: dict[str, dict[str, str]] = {
    "policy_rates": {
        "title": "Select Economic Indicators",
        "query": "RBI Select Economic Indicators monthly policy repo rate CRR SLR",
        "database_table": "policy_rates",
        "document_title": "Select Economic Indicators (Monthly), RBI Bulletin Table 1",
    },
    "money_supply": {
        "title": "Money Stock Measures",
        "query": "Money Stock Measures M1 M2 M3",
        "database_table": "money_supply",
        "document_title": "Money Stock Measures, RBI Bulletin Table 6",
    },
    "system_liquidity": {
        "title": "Liquidity Operations By Rbi",
        "query": "Liquidity Operations by RBI repo reverse repo MSF SDF",
        "database_table": "system_liquidity",
        "document_title": "Liquidity Operations by RBI, RBI Bulletin Table 3",
    },
}


class MonetaryDataUnavailableError(Exception):
    """Raised when neither the official DBIE MCP nor local cache has data."""


class _DBIEMCPClient:
    """Small stdio JSON-RPC client for the official DBIE MCP executable."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._stderr_task: asyncio.Task[bytes] | None = None

    async def __aenter__(self) -> _DBIEMCPClient:
        if os.name == "nt":
            command = (
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                f"npx.cmd --yes {_MCP_PACKAGE}",
            )
        else:
            command = ("npx", "--yes", _MCP_PACKAGE)

        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=_STDIO_LINE_LIMIT,
        )
        assert self._process.stdin is not None
        self._stderr_task = asyncio.create_task(self._process.stderr.read())
        try:
            await self._request(
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "macrograph-ai", "version": "0.1.0"},
                },
            )
            self._notify("notifications/initialized")
        except Exception:
            self._process.kill()
            await self._process.wait()
            if self._stderr_task:
                await self._stderr_task
            raise
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._process is None:
            return
        if self._process.stdin and not self._process.stdin.is_closing():
            self._process.stdin.close()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()
        if self._stderr_task:
            try:
                stderr = await asyncio.wait_for(self._stderr_task, timeout=1)
            except asyncio.TimeoutError:
                self._stderr_task.cancel()
                stderr = b""
            if stderr and self._process.returncode not in (0, None) and exc is None:
                logger.warning("DBIE MCP process exited with stderr: %s", stderr.decode(errors="replace"))

    def _notify(self, method: str) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("DBIE MCP process is not running.")
        message = {"jsonrpc": "2.0", "method": method}
        self._process.stdin.write((json.dumps(message) + "\n").encode())

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("DBIE MCP process is not running.")
        self._request_id += 1
        request_id = self._request_id
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        self._process.stdin.write((json.dumps(request) + "\n").encode())
        await self._process.stdin.drain()

        deadline = asyncio.get_running_loop().time() + monetary_settings.DBIE_TIMEOUT
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"DBIE MCP timed out while handling {method}.")
            line = await asyncio.wait_for(self._process.stdout.readline(), timeout=remaining)
            if not line:
                raise ConnectionError("Official DBIE MCP exited before replying.")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("Official DBIE MCP wrote a malformed JSON-RPC message.") from error
            if not isinstance(response, dict) or response.get("id") != request_id:
                continue
            if response.get("error"):
                raise ValueError(f"Official DBIE MCP error: {response['error']}")
            result = response.get("result")
            if not isinstance(result, dict):
                raise ValueError(f"Official DBIE MCP returned no result for {method}.")
            return result

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        if result.get("isError"):
            raise ValueError(f"DBIE MCP tool {name} failed: {result.get('content')}")
        structured = result.get("structuredContent")
        if structured is not None:
            return structured
        content = result.get("content")
        if not isinstance(content, list):
            raise ValueError(f"DBIE MCP tool {name} returned no content.")
        text = next(
            (item.get("text") for item in content if isinstance(item, dict) and item.get("type") == "text"),
            None,
        )
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"DBIE MCP tool {name} returned empty text content.")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"DBIE MCP tool {name} returned malformed JSON content.") from error
        if not isinstance(payload, dict) or payload.get("error"):
            raise ValueError(f"DBIE MCP tool {name} returned an error payload: {payload}")
        return payload


async def _resolve_table(
    mcp: _DBIEMCPClient,
    dataset: str,
) -> dict[str, Any]:
    spec = _TABLES[dataset]
    search = await mcp.call_tool(
        "search_tables",
        {"query": spec["query"], "limit": 20},
    )
    candidates = search.get("results")
    if not isinstance(candidates, list):
        candidates = []
    target = next(
        (
            item for item in candidates
            if isinstance(item, dict)
            and str(item.get("title", "")).casefold() == spec["title"].casefold()
        ),
        None,
    )

    if target is None:
        catalogue = await mcp.call_tool("list_tables", {"section": "Banking"})
        tables = catalogue.get("tables")
        if isinstance(tables, list):
            target = next(
                (
                    item for item in tables
                    if isinstance(item, dict)
                    and str(item.get("title", "")).casefold() == spec["title"].casefold()
                ),
                None,
            )

    if not isinstance(target, dict) or not isinstance(target.get("table"), str):
        raise ValueError(f"Official DBIE catalogue did not resolve {spec['title']!r}.")
    return target


def _frequency_from_source(title: str, payload: dict[str, Any]) -> str | None:
    frequency = payload.get("frequency")
    if isinstance(frequency, str) and frequency:
        return frequency
    for known in ("Daily", "Weekly", "Fortnightly", "Monthly", "Quarterly", "Annual"):
        if known.casefold() in title.casefold():
            return known
    return None


async def _fetch_table(
    mcp: _DBIEMCPClient,
    dataset: str,
    lookback: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = _TABLES[dataset]
    target = await _resolve_table(mcp, dataset)
    result = await mcp.call_tool(
        "get_table",
        {"table": target["table"], "max_array_items": min(max(lookback * 35, 100), 10000)},
    )
    payload = result.get("data")
    if not isinstance(payload, dict):
        raise ValueError(f"DBIE {spec['title']} response did not contain table data.")
    context = {
        "document_title": spec["document_title"],
        "table_reference": target["table"],
        "retrieval_url": target.get("page_url") or f"{result.get('source', '')}{target['table']}",
        "source_base_url": result.get("source"),
        "source_note": result.get("note"),
        "frequency": (
            _frequency_from_source(
                f"{target.get('title', '')} {target.get('description', '')}",
                payload,
            )
            or _frequency_from_source(spec["document_title"], payload)
        ),
        "unit": payload.get("unit") or payload.get("units"),
        "as_of": result.get("as_of"),
    }
    if not result.get("source") or not result.get("note"):
        raise ValueError("DBIE response omitted source or data-vintage note.")
    return payload, context


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


def _save_records(table: str, records: list[Any], tool_name: str) -> None:
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
    db.log_fetch(tool_name, "upstream_snapshot", rows_written=written)


def _log_fallback(tool_name: str, error: Exception) -> None:
    logger.warning("%s failed; falling back to DuckDB: %s", tool_name, error)
    try:
        db.log_fetch(tool_name, "cache_fallback", error_msg=str(error))
    except Exception as log_error:
        logger.warning("Could not record %s fallback in fetch log: %s", tool_name, log_error)


async def _fetch_live_records(dataset: str, lookback: int) -> list[Any]:
    parser = {
        "policy_rates": parse_policy_rates,
        "money_supply": parse_money_supply,
        "system_liquidity": parse_system_liquidity,
    }[dataset]
    async with _DBIEMCPClient() as mcp:
        payload, context = await _fetch_table(mcp, dataset, lookback)
    return parser(payload, lookback, context)


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


async def _fetch_with_cache(
    dataset: str,
    lookback: int,
    record_type: Any,
) -> list[Any]:
    db.initialise_schema()
    spec = _TABLES[dataset]
    tool_name = f"get_{dataset}"
    try:
        records = await _fetch_live_records(dataset, lookback)
        _save_records(spec["database_table"], records, tool_name)
        return records
    except Exception as exc:
        _log_fallback(tool_name, exc)
        return _load_cache(spec["database_table"], lookback, record_type, tool_name)


async def fetch_policy_rates(lookback_months: int = 12) -> list[PolicyRatesRecord]:
    """Fetch policy and reserve rates from DBIE's verified monthly table."""
    return await _fetch_with_cache("policy_rates", lookback_months, PolicyRatesRecord)


async def fetch_money_supply(lookback_months: int = 12) -> list[MoneySupplyRecord]:
    """Fetch the published money-stock table, preserving its reported values."""
    return await _fetch_with_cache("money_supply", lookback_months, MoneySupplyRecord)


async def fetch_system_liquidity(lookback_months: int = 6) -> list[SystemLiquidityRecord]:
    """Fetch RBI liquidity-operation components without inventing a net total."""
    return await _fetch_with_cache("system_liquidity", lookback_months, SystemLiquidityRecord)


async def fetch_monetary_stance_snapshot() -> list[MonetaryStanceRecord]:
    """Return a sourced policy-rate snapshot; unsupported stance metrics remain absent."""
    try:
        rates = await fetch_policy_rates(lookback_months=1)
        if not rates:
            raise ValueError("No policy-rate observations were returned.")
        rate = rates[0]
        record = MonetaryStanceRecord(
            period=rate.period,
            repo_rate_pct=rate.repo_rate_pct,
            stance_label=None,
            real_policy_rate_pct=None,
            m3_growth_pct=None,
            system_liquidity_status=None,
            citation=rate.citation,
        )
        _save_records("monetary_stance", [record], "get_monetary_stance_snapshot")
        return [record]
    except Exception as exc:
        _log_fallback("get_monetary_stance_snapshot", exc)
        return _load_cache(
            "monetary_stance", 1, MonetaryStanceRecord, "Monetary stance snapshot",
        )
