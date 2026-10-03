"""
Labour sector client.

Data source:
    MoSPI eSankhyiki MCP
    https://mcp.mospi.gov.in/

PLFS workflow:
    list_datasets
        -> get_indicators
        -> get_metadata
        -> get_data

Indicator codes and aggregate filters are resolved from MoSPI responses.

The client follows the existing Labour-sector database contract.
It does not modify or assume a new database schema.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from labour_sector import database as db
from labour_sector.config import labour_settings
from labour_sector.parsers import (
    parse_labour_records,
    parse_unemployment_records,
    parse_lfpr_records,
    parse_wpr_records,
)
from labour_sector.models import DataFreshness


logger = logging.getLogger(__name__)


class LabourDataUnavailableError(RuntimeError):
    """Raised when Labour/PLFS data is unavailable."""


def _is_legacy_baseline(record: dict[str, Any], table_name: str) -> bool:
    citation = record.get("citation")
    if isinstance(citation, str):
        try:
            citation = json.loads(citation)
        except json.JSONDecodeError:
            return False
    legacy_tables = {
        "unemployment": "labour_sector.plfs_unemployment",
        "lfpr": "labour_sector.plfs_lfpr",
        "wpr": "labour_sector.plfs_wpr",
        "labour_conditions": "labour_sector.epfo_payroll",
    }
    return (
        isinstance(citation, dict)
        and citation.get("freshness") == DataFreshness.CACHED.value
        and citation.get("table_reference") == legacy_tables.get(table_name)
    )


# ---------------------------------------------------------------------------
# MoSPI configuration
# ---------------------------------------------------------------------------

_MOSPI_MCP_URL = str(
    labour_settings.MOSPI_MCP_BASE
).rstrip("/")

_DATASET = "PLFS"

# Monthly PLFS frequency, verified in MoSPI's live indicator catalogue.
_FREQUENCY_CODE = 3

_INDICATOR_TERMS = {
    "unemployment": ("unemployment rate",),
    "lfpr": ("labour force participation rate", "labor force participation rate", "lfpr"),
    "wpr": ("worker population ratio", "wpr"),
    "labour_conditions": ("employment conditions",),
}


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            60.0,
            connect=30.0,
        ),
        headers={
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        },
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# MCP response handling
# ---------------------------------------------------------------------------

def _decode_json_text(value: Any) -> Any:
    """Decode a JSON string when the MCP server returns JSON as text."""

    if not isinstance(value, str):
        return value

    text = value.strip()

    if not text:
        return value

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _parse_sse_response(text: str) -> list[Any]:
    """
    Parse Server-Sent Events returned by the MoSPI MCP endpoint.

    Expected format:

        event: message
        data: {...}
    """

    payloads: list[Any] = []

    for line in text.splitlines():
        line = line.strip()

        if not line.startswith("data:"):
            continue

        raw = line[5:].strip()

        if not raw:
            continue

        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError:
            decoded = _decode_json_text(raw)

            if decoded != raw:
                payloads.append(decoded)

    return payloads


def _unwrap_mcp_result(value: Any) -> Any:
    """
    Recursively unwrap common JSON-RPC/MCP response envelopes.
    """

    if isinstance(value, str):
        decoded = _decode_json_text(value)

        if decoded is not value:
            return _unwrap_mcp_result(decoded)

        return value

    if isinstance(value, list):
        values = [
            _unwrap_mcp_result(item)
            for item in value
        ]

        if len(values) == 1:
            return values[0]

        return values

    if not isinstance(value, dict):
        return value

    # JSON-RPC error.
    if value.get("error") is not None:
        error = value["error"]

        raise LabourDataUnavailableError(
            f"MoSPI MCP returned an error: {error}"
        )

    # MCP application error.
    if value.get("isError") is True:
        raise LabourDataUnavailableError(
            value.get("message")
            or value.get("error")
            or value.get("content")
            or "MoSPI MCP returned an error."
        )

    # JSON-RPC result envelope.
    if "result" in value:
        return _unwrap_mcp_result(
            value["result"]
        )

    # MCP content envelope.
    if "content" in value:
        content = value["content"]

        if isinstance(content, list):
            extracted: list[Any] = []

            for item in content:

                if (
                    isinstance(item, dict)
                    and "text" in item
                ):
                    extracted.append(
                        _unwrap_mcp_result(
                            item["text"]
                        )
                    )
                else:
                    extracted.append(
                        _unwrap_mcp_result(item)
                    )

            if len(extracted) == 1:
                return extracted[0]

            return extracted

        return _unwrap_mcp_result(content)

    return {
        key: _unwrap_mcp_result(val)
        for key, val in value.items()
    }


async def _call_mcp_tool(
    client: httpx.AsyncClient,
    request_id: int,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """
    Call a tool exposed by the MoSPI MCP server.
    """

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    response = await client.post(
        _MOSPI_MCP_URL,
        json=payload,
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get("content-type", "")
        .lower()
    )

    if "text/event-stream" in content_type:

        messages = _parse_sse_response(
            response.text
        )

        if not messages:
            raise LabourDataUnavailableError(
                f"MoSPI MCP returned an empty SSE "
                f"response for {tool_name}."
            )

        raw_result = messages[-1]

    else:

        try:
            raw_result = response.json()

        except ValueError as exc:

            raise LabourDataUnavailableError(
                f"MoSPI MCP returned non-JSON "
                f"data for {tool_name}."
            ) from exc

    return _unwrap_mcp_result(
        raw_result
    )


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def _raise_if_mcp_error(
    payload: Any,
    tool_name: str,
) -> None:
    """Raise when a structured MCP error is returned."""

    if not isinstance(payload, dict):
        return

    if payload.get("isError") is True:

        raise LabourDataUnavailableError(
            f"MoSPI {tool_name} failed: "
            f"{payload.get('error') or payload.get('message') or payload}"
        )

    if payload.get("error"):

        raise LabourDataUnavailableError(
            f"MoSPI {tool_name} failed: "
            f"{payload['error']}"
        )


def _extract_filter_values(
    metadata: Any,
) -> dict[str, Any]:
    """
    Extract filter_values from get_metadata().
    """

    if not isinstance(metadata, dict):

        raise LabourDataUnavailableError(
            "MoSPI metadata response is not a dictionary."
        )

    _raise_if_mcp_error(
        metadata,
        "get_metadata",
    )

    metadata_data = metadata.get("data")
    if not isinstance(metadata_data, dict):
        metadata_data = {}

    filter_values = metadata.get("filter_values") or metadata_data.get("filter_values")

    if not isinstance(filter_values, dict):
        raise LabourDataUnavailableError(
            "MoSPI metadata response did not contain filter_values."
        )

    nested_data = filter_values.get("data")
    if isinstance(nested_data, dict):
        return nested_data

    return filter_values


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _pick_value(
    values: Any,
    preferred_labels: tuple[str, ...],
) -> Any | None:
    """Select an aggregate code only when metadata labels it explicitly."""
    if isinstance(values, dict):
        nested = values.get("values") or values.get("options") or values.get("data")
        values = nested if nested is not None else [
            {"code": code, "label": label}
            for code, label in values.items()
            if isinstance(label, str)
        ]
    if not isinstance(values, list):
        return None

    for item in values:
        if isinstance(item, dict):
            value = next(
                (
                    item[key]
                    for key in ("code", "value", "id", "gender_code", "age_code", "sector_code")
                    if item.get(key) is not None
                ),
                None,
            )
            label = " ".join(
                str(item.get(key, ""))
                for key in ("label", "name", "title", "description", "text")
            ).casefold()
        else:
            value = item
            label = str(item).casefold()
        if value is not None and any(term in label for term in preferred_labels):
            return value
    return None


def _indicator_code(indicators: Any, indicator_key: str) -> tuple[Any, str]:
    terms = _INDICATOR_TERMS[indicator_key]
    frequency_groups = indicators.get("indicators_by_frequency") if isinstance(indicators, dict) else None
    if isinstance(frequency_groups, dict):
        frequency_prefix = f"frequency_code_{_FREQUENCY_CODE}_"
        indicators = next(
            (group for key, group in frequency_groups.items() if key.startswith(frequency_prefix)),
            None,
        )
        if indicators is None:
            raise LabourDataUnavailableError(
                "MoSPI indicator catalogue did not include monthly PLFS indicators."
            )
    for item in _walk_dicts(indicators):
        name = " ".join(
            str(item.get(key, ""))
            for key in ("indicator_name", "indicator", "name", "label", "title", "description")
        ).casefold()
        code = next(
            (
                item[key]
                for key in ("indicator_code", "code", "id")
                if item.get(key) is not None
            ),
            None,
        )
        if code is not None and any(term in name for term in terms):
            return code, name.strip()
    raise LabourDataUnavailableError(
        f"MoSPI PLFS indicator catalogue did not identify {indicator_key}."
    )


def _filter_options(filter_values: dict[str, Any], dimension: str) -> Any:
    aliases = {
        "gender": ("gender", "gender_code", "sex", "sex_code"),
        "age": ("age", "age_code", "age_group", "age_group_code"),
        "sector": ("sector", "sector_code", "area", "area_code"),
    }
    return next(
        (filter_values[key] for key in aliases[dimension] if key in filter_values),
        None,
    )


def _build_plfs_filters(
    metadata: dict[str, Any],
    indicator_code: Any,
) -> dict[str, Any]:
    """
    Build valid PLFS filters from MoSPI metadata.

    No filter value is fabricated when the metadata does not expose it.
    """

    filter_values = _extract_filter_values(
        metadata
    )

    filters: dict[str, Any] = {
        "indicator_code": indicator_code,
        "frequency_code": _FREQUENCY_CODE,
    }

    choices = (
        ("gender_code", "gender", ("person", "persons", "all genders", "total")),
        ("age_code", "age", ("15 years and above", "15 years+", "age 15+", "15+")),
        ("sector_code", "sector", ("rural + urban", "rural and urban", "all india", "all sectors")),
    )
    for filter_name, dimension, labels in choices:
        code = _pick_value(_filter_options(filter_values, dimension), labels)
        if code is None:
            raise LabourDataUnavailableError(
                f"MoSPI metadata did not expose the required aggregate {dimension} filter."
            )
        filters[filter_name] = code

    return filters


# ---------------------------------------------------------------------------
# PLFS workflow
# ---------------------------------------------------------------------------

async def _fetch_plfs_indicator(
    indicator_key: str,
) -> Any:
    """
    Execute the official PLFS workflow:

        get_indicators
            ->
        get_metadata
            ->
        get_data
    """

    async with _build_client() as client:

        datasets = await _call_mcp_tool(
            client,
            1,
            "list_datasets",
            {},
        )
        _raise_if_mcp_error(datasets, "list_datasets")
        if "plfs" not in json.dumps(datasets, default=str).casefold():
            raise LabourDataUnavailableError(
                "MoSPI dataset catalogue did not list PLFS."
            )

        # Step 1: discover the requested indicator from the live catalogue.
        indicators = await _call_mcp_tool(
            client,
            2,
            "get_indicators",
            {
                "dataset": _DATASET,
                "frequency_code": _FREQUENCY_CODE,
            },
        )

        _raise_if_mcp_error(
            indicators,
            "get_indicators",
        )
        indicator_code, indicator_name = _indicator_code(indicators, indicator_key)

        # Step 2: retrieve valid filter values.
        metadata = await _call_mcp_tool(
            client,
            3,
            "get_metadata",
            {
                "dataset": _DATASET,
                "indicator_code": indicator_code,
                "frequency_code": _FREQUENCY_CODE,
            },
        )

        _raise_if_mcp_error(
            metadata,
            "get_metadata",
        )

        filters = _build_plfs_filters(
            metadata,
            indicator_code,
        )

        logger.info(
            "Fetching PLFS indicator=%s (%s) with filters=%s",
            indicator_code, indicator_name,
            filters,
        )

        # Step 3: retrieve actual observations.
        data = await _call_mcp_tool(
            client,
            4,
            "get_data",
            {
                "dataset": _DATASET,
                "filters": filters,
            },
        )

        _raise_if_mcp_error(
            data,
            "get_data",
        )

        return data, indicator_code, indicator_name


# ---------------------------------------------------------------------------
# Cache-aware indicator fetching
# ---------------------------------------------------------------------------

async def _fetch_indicator_with_cache(
    *,
    indicator_key: str,
    parser,
    table_name: str,
    unavailable_message: str,
) -> list[dict[str, Any]]:

    db.initialise_schema()
    try:

        raw_data, indicator_code, indicator_name = await _fetch_plfs_indicator(indicator_key)

        records = parser(
            raw_data
        )

        if not records:

            raise LabourDataUnavailableError(
                f"MoSPI returned no usable "
                f"{table_name} records."
            )

        fetched_at = datetime.now(timezone.utc)
        for index, record in enumerate(records):
            record["citation"] = {
                "source_agent": "labour_sector",
                "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "document_title": f"Periodic Labour Force Survey (PLFS): {indicator_name}",
                "table_reference": f"PLFS indicator {indicator_code}",
                "retrieval_url": _MOSPI_MCP_URL + "/",
                "observation_period": record["period"],
                "fetched_at": (fetched_at - timedelta(milliseconds=index)).isoformat(),
                "freshness": DataFreshness.LIVE.value,
            }

        records.sort(key=lambda record: str(record["period"]), reverse=True)
        db.upsert_rows(
            table_name,
            records,
        )

        db.log_fetch(
            "PLFS",
            "success",
            len(records),
            None,
        )

        return records

    except Exception as exc:

        logger.warning(
            "Live PLFS %s fetch failed: %s. "
            "Falling back to cache.",
            table_name,
            exc,
        )

        db.log_fetch(
            "PLFS",
            "cache_fallback",
            0,
            str(exc),
        )

        cached = [
            record
            for record in db.query_latest_rows(table_name, limit=100)
            if not _is_legacy_baseline(record, table_name)
        ]

        if cached:
            for record in cached:
                citation = record.get("citation")
                if isinstance(citation, str) and citation.startswith("http"):
                    citation = {
                        "source_agent": "labour_sector",
                        "source_authority": "Ministry of Statistics and Programme Implementation (MoSPI)",
                        "document_title": f"PLFS {table_name} cached observation",
                        "table_reference": f"PLFS {table_name}",
                        "retrieval_url": citation,
                        "observation_period": record["period"],
                        "fetched_at": str(record.get("fetched_at") or datetime.now(timezone.utc).isoformat()),
                    }
                if not isinstance(citation, dict):
                    continue
                citation = dict(citation)
                citation.setdefault("source_agent", "labour_sector")
                citation.setdefault(
                    "source_authority",
                    "Ministry of Statistics and Programme Implementation (MoSPI)",
                )
                citation.setdefault(
                    "document_title",
                    f"PLFS {table_name} cached observation",
                )
                citation.setdefault("table_reference", f"PLFS {table_name}")
                citation.setdefault("retrieval_url", _MOSPI_MCP_URL + "/")
                citation.setdefault("observation_period", record["period"])
                citation.setdefault(
                    "fetched_at",
                    str(record.get("fetched_at") or datetime.now(timezone.utc).isoformat()),
                )
                citation["freshness"] = DataFreshness.CACHED.value
                record["citation"] = citation
            cached = [record for record in cached if isinstance(record.get("citation"), dict)]
            if cached:
                cached.sort(key=lambda record: str(record.get("period", "")), reverse=True)
                return cached

        raise LabourDataUnavailableError(
            unavailable_message
        ) from exc


# ---------------------------------------------------------------------------
# Public Labour API
# ---------------------------------------------------------------------------

async def fetch_unemployment_snapshot() -> list[dict[str, Any]]:
    """
    Fetch PLFS Unemployment Rate.

    Official indicator:
        3 = Unemployment Rate
    """

    return await _fetch_indicator_with_cache(
        indicator_key="unemployment",
        parser=parse_unemployment_records,
        table_name="unemployment",
        unavailable_message=(
            "Unemployment data unavailable: "
            "live fetch failed and cache is empty."
        ),
    )


async def fetch_labour_force_participation() -> list[dict[str, Any]]:
    """
    Fetch PLFS Labour Force Participation Rate.

    Official indicator:
        1 = LFPR
    """

    return await _fetch_indicator_with_cache(
        indicator_key="lfpr",
        parser=parse_lfpr_records,
        table_name="lfpr",
        unavailable_message=(
            "Labour force participation data unavailable: "
            "live fetch failed and cache is empty."
        ),
    )


async def fetch_worker_population_ratio() -> list[dict[str, Any]]:
    """
    Fetch PLFS Worker Population Ratio.

    Official indicator:
        2 = WPR
    """

    return await _fetch_indicator_with_cache(
        indicator_key="wpr",
        parser=parse_wpr_records,
        table_name="wpr",
        unavailable_message=(
            "Worker population ratio data unavailable: "
            "live fetch failed and cache is empty."
        ),
    )


async def fetch_labour_employment_conditions() -> list[dict[str, Any]]:
    """
    Fetch PLFS employment-condition data.

    Official indicator:
        5 = Employment Conditions
    """

    return await _fetch_indicator_with_cache(
        indicator_key="labour_conditions",
        parser=parse_labour_records,
        table_name="labour_conditions",
        unavailable_message=(
            "Labour employment conditions unavailable: "
            "live fetch failed and cache is empty."
        ),
    )