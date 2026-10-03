"""Async client for querying the public IMF SDMX MCP server.

Connects to https://imf.caseyjhand.com/mcp via JSON-RPC 2.0 / Streamable HTTP
to retrieve official IMF World Economic Outlook (WEO) medium-term projections
for India's Current Account Deficit (% GDP) and export volume growth.
Zero authentication required.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from external_sector.config import external_settings

logger = logging.getLogger(__name__)


class IMFClient:
    """Client for IMF SDMX 3.0 MCP Server."""

    def __init__(
        self,
        base_url: str = external_settings.IMF_MCP_URL,
        timeout: float = external_settings.IMF_API_TIMEOUT,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _call_imf_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a tool on the IMF MCP server via JSON-RPC 2.0 / Streamable HTTP."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()

            # Parse SSE lines for the result payload
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    data = json.loads(line[5:])
                    if "result" in data:
                        return data["result"]
                    if "error" in data:
                        raise ValueError(f"IMF MCP error: {data['error']}")

        raise RuntimeError("No result received from IMF MCP server")

    async def get_india_weo_outlook(
        self,
        start_year: str = "2022",
        end_year: str = "2027",
    ) -> list[dict[str, Any]]:
        """Fetch India's WEO current account (% GDP) and export volume outlook."""
        try:
            result = await self._call_imf_tool(
                tool_name="imf_query_dataset",
                arguments={
                    "dataflow_id": "WEO",
                    "key": "IND.BCA_NGDPD+TX_RPCH+BCA.A",
                    "start_period": start_year,
                    "end_period": end_year,
                },
            )
            structured = result.get("structuredContent", {})
            observations = structured.get("observations", [])
            source = structured.get("source", "Source: International Monetary Fund (IMF), WEO")
            
            output = []
            for obs in observations:
                output.append({
                    "series_key": obs.get("series_key"),
                    "period": str(obs.get("time_period")),
                    "value": obs.get("value"),
                    "source": source,
                })
            return output
        except Exception as exc:
            logger.warning("Failed to fetch WEO outlook from IMF MCP: %s", exc)
            return []


imf_client = IMFClient()
