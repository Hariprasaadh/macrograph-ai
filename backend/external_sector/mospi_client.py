"""MoSPI eSankhyiki MCP Client for External Sector Datasets."""
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

from external_sector.config import external_settings

logger = logging.getLogger(__name__)


def _make_retry():
    return retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


@_make_retry()
async def call_mospi_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the official MoSPI eSankhyiki MCP server."""
    url = external_settings.MOSPI_MCP_URL
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    timeout = httpx.Timeout(
        float(external_settings.MOSPI_API_TIMEOUT),
        connect=external_settings.HTTP_CONNECT_TIMEOUT,
        read=external_settings.HTTP_READ_TIMEOUT,
    )
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "macrograph-ai/external-sector"}) as client:
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

        # Parse SSE event stream
        for line in response.text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                raw_json = line[5:].strip()
                if not raw_json:
                    continue
                parsed = json.loads(raw_json)
                content = parsed.get("result", {}).get("content", [])
                if content and isinstance(content, list):
                    text_data = content[0].get("text", "")
                    if text_data:
                        return json.loads(text_data)
        return {}


async def fetch_mospi_rbi_dataset(indicator_code: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Fetch official RBI data series from MoSPI eSankhyiki MCP."""
    query_filters: dict[str, Any] = {"sub_indicator_code": indicator_code}
    if filters:
        query_filters.update(filters)

    data = await call_mospi_tool(
        tool_name="get_data",
        arguments={
            "dataset": "RBI",
            "filters": query_filters,
        },
    )
    raw_list = data.get("data", [])
    return raw_list if isinstance(raw_list, list) else []
