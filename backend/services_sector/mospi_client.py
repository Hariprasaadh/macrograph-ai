"""MoSPI e-Sankhyiki MCP client for the Services Sector.

Implements the sequential 4-tool workflow documented in service_sector_mcp.md:

    list_datasets --> get_indicators --> get_metadata --> get_data

Endpoint: https://mcp.mospi.gov.in/ (HTTP/SSE transport, zero auth).

Datasets owned by this sector:
  - ISP: Index of Service Production (base_year 2024-25,
    frequency_code 1 = Yearly / 2 = Monthly,
    type_code 1 = General / 2 = Broad Sub Sector).
  - NAS: National Accounts Statistics, Statements 8.9–8.14 (Services GVA).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from services_sector.config import services_settings

logger = logging.getLogger(__name__)


class MospiMCPError(RuntimeError):
    """Raised when the MoSPI MCP server returns a JSON-RPC error."""


def _make_retry():
    return retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _parse_mcp_result_text(response: httpx.Response) -> Any:
    """Extract the tool result from a MoSPI MCP response (JSON or SSE)."""
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and not response.text.strip().startswith("data:"):
        try:
            body = response.json()
            if isinstance(body, dict) and "error" in body:
                err = body["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                raise MospiMCPError(f"MoSPI MCP JSON-RPC error: {msg}")
            content = body.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text_data = content[0].get("text", "")
                try:
                    return json.loads(text_data)
                except (json.JSONDecodeError, TypeError):
                    return text_data
            return body
        except json.JSONDecodeError:
            pass

    # Parse SSE event stream
    for line in response.text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        raw_json = line[5:].strip()
        if not raw_json:
            continue
        try:
            event = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if "error" in event:
            err = event["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise MospiMCPError(f"MoSPI MCP JSON-RPC error: {msg}")
        content = event.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            text_data = content[0].get("text", "")
            if text_data:
                try:
                    return json.loads(text_data)
                except (json.JSONDecodeError, TypeError):
                    return text_data
    return {}


@_make_retry()
async def call_mospi_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Call a tool on the official MoSPI e-Sankhyiki MCP server.

    Valid tool names: list_datasets, get_indicators, get_metadata, get_data.
    Tools must be called in order — skipping get_metadata yields invalid filters.
    """
    url = services_settings.MOSPI_MCP_URL
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    timeout = httpx.Timeout(
        float(services_settings.MOSPI_API_TIMEOUT),
        connect=services_settings.HTTP_CONNECT_TIMEOUT,
        read=services_settings.HTTP_READ_TIMEOUT,
    )
    async with httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": "macrograph-ai/services-sector"}
    ) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        if response.is_error:
            response.raise_for_status()
        return _parse_mcp_result_text(response)


async def list_datasets() -> Any:
    """Step 1 of the MCP workflow: overview of all MoSPI datasets."""
    return await call_mospi_tool("list_datasets", {})


async def get_indicators(dataset: str) -> Any:
    """Step 2 of the MCP workflow: list indicators for a dataset (e.g. 'ISP')."""
    return await call_mospi_tool("get_indicators", {"dataset": dataset})


async def get_metadata(dataset: str, **kwargs: Any) -> Any:
    """Step 3 of the MCP workflow: valid filter values for a dataset."""
    return await call_mospi_tool("get_metadata", {"dataset": dataset, **kwargs})


async def get_data(dataset: str, filters: dict[str, Any]) -> Any:
    """Step 4 of the MCP workflow: fetch data with metadata-validated filters."""
    return await call_mospi_tool("get_data", {"dataset": dataset, "filters": filters})


# ── Sector-specific validated filter builders ─────────────────────────────
# All formats below were verified live against https://mcp.mospi.gov.in/
# (list_datasets -> get_indicators -> get_metadata -> get_data).

# MoSPI broad_sub_sector_code values from get_metadata('ISP') — 19 codes.
ISP_SUB_SECTOR_CODES: dict[str, int] = {
    "WHOLESALE_TRADE": 1,
    "RETAIL_TRADE": 2,
    "REPAIR_SERVICES": 3,
    "ACCOMMODATION_FOOD": 4,
    "RAILWAY_TRANSPORT": 5,
    "ROAD_TRANSPORT": 6,
    "WATER_TRANSPORT": 7,
    "AIR_TRANSPORT": 8,
    "WAREHOUSING_SUPPORT": 9,
    "POSTAL_COURIER": 10,
    "TELECOMMUNICATIONS": 11,
    "INFORMATION_BROADCASTING": 12,
    "BANKING": 13,
    "INSURANCE": 14,
    "REAL_ESTATE": 15,
    "IT_COMPUTER": 16,
    "PROFESSIONAL_TECHNICAL": 17,
    "ADMIN_SUPPORT": 18,
    "ARTS_ENTERTAINMENT": 19,
}

# NAS industry_code values (indicator_code 1 = Gross Value Added) that cover
# services. Verified live via get_metadata('NAS', indicator_code=1).
NAS_SERVICES_INDUSTRY_CODES: tuple[int, ...] = (6, 7, 8, 9, 10, 11, 12, 14)

# NSS80 CMST telecom indicator codes verified via get_indicators('NSS80').
# 17 = household phone connectivity, 18 = household internet facility.
NSS80_TELECOM_INDICATORS: tuple[int, ...] = (17, 18)
NSS80_ALL_INDIA_STATE_CODE = 37

# Indian FY month name (1=April … 12=March) → calendar month number.
_FY_MONTH_TO_CALENDAR: dict[str, int] = {
    "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "january": 1, "february": 2, "march": 3,
}


def isp_sector_year_filters(sub_sector_code: int, year: str) -> dict[str, Any]:
    """Build validated ISP filters for one sub-sector in one FY year."""
    return {"frequency_code": 2, "year": year, "broad_sub_sector_code": sub_sector_code}


def nas_gva_filters(industry_code: int) -> dict[str, Any]:
    """Build validated NAS filters for services GVA (indicator 1, annual)."""
    return {
        "indicator_code": 1,
        "base_year": "2011-12",
        "series": "Current",
        "frequency_code": 1,
        "industry_code": industry_code,
    }


def nss80_telecom_filters(indicator_code: int) -> dict[str, Any]:
    """Build validated NSS80 CMST filters (All-India telecom penetration)."""
    return {"indicator_code": indicator_code, "state_code": NSS80_ALL_INDIA_STATE_CODE}


def isp_month_to_period(fy_year: str, month_name: str) -> str:
    """Convert MoSPI FY month labels to a calendar period (YYYY-MM).

    FY 'YYYY-YY': April–December belong to YYYY, January–March to YYYY+1.
    """
    start_year = int(str(fy_year).split("-")[0])
    cal_month = _FY_MONTH_TO_CALENDAR.get(str(month_name).strip().lower(), 1)
    cal_year = start_year if cal_month >= 4 else start_year + 1
    return f"{cal_year:04d}-{cal_month:02d}"
