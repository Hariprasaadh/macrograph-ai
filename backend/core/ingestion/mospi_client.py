"""Official MoSPI MCP Client (e-Sankhyiki Integration).

Integrates Macrograph-AI directly with India's official Ministry of Statistics
and Programme Implementation (MoSPI) MCP Server at https://mcp.mospi.gov.in/.

Provides live statistical data across:
- CPI (Consumer Price Index & Retail Inflation)
- NAS (National Accounts Statistics / Real GDP & GVA)
- IIP (Index of Industrial Production)
- PLFS (Periodic Labour Force Survey / Unemployment & LFPR)
- WPI (Wholesale Price Index)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

MOSPI_MCP_URL = "https://mcp.mospi.gov.in/"


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def call_mospi_mcp(tool_name: str, arguments: Dict[str, Any], timeout: float = 15.0) -> Any:
    """Calls a tool on the official MoSPI FastMCP Server (https://mcp.mospi.gov.in/)."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(MOSPI_MCP_URL, json=payload, headers=headers)
        if resp.is_error:
            resp.raise_for_status()

        # Parse SSE response text
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                event = json.loads(line[6:])
                content = event.get("result", {}).get("content", [])
                if content and isinstance(content, list):
                    text_data = content[0].get("text", "")
                    try:
                        return json.loads(text_data)
                    except Exception:
                        return text_data
    return None


async def fetch_live_cpi(year: int = 2024, month_code: int = 12) -> List[Dict[str, Any]]:
    """Fetch official All-India CPI Inflation metrics from MoSPI."""
    try:
        data = await call_mospi_mcp(
            "get_data",
            {
                "dataset": "CPI",
                "filters": {
                    "base_year": "2012",
                    "series": "Current",
                    "year": year,
                    "month_code": month_code,
                    "limit": 10,
                },
            },
        )
        if isinstance(data, dict):
            return data.get("data", [])
        return []
    except Exception as e:
        logger.warning("MoSPI CPI fetch failed: %s", e)
        return []


async def fetch_live_nas_gdp() -> Dict[str, Any]:
    """Fetch official National Accounts Statistics (GDP / GVA) indicators."""
    try:
        indicators = await call_mospi_mcp("get_indicators", {"dataset": "NAS"})
        return indicators if isinstance(indicators, dict) else {}
    except Exception as e:
        logger.warning("MoSPI NAS fetch failed: %s", e)
        return {}
