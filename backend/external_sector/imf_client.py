"""Async client for querying the public IMF SDMX MCP server.

Connects to https://imf.caseyjhand.com/mcp via JSON-RPC 2.0 / Streamable HTTP
to retrieve official IMF World Economic Outlook (WEO) medium-term projections
for India's Current Account Deficit (% GDP) and export volume growth.
Zero authentication required.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from external_sector.config import external_settings
from external_sector.models import (
    BoPRecord,
    Citation,
    DataFreshness,
    IMFExternalOutlookRecord,
)
from external_sector.parsers import parse_period_sort_key, safe_float_val

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

    async def get_india_bop_quarterly(self, lookback_quarters: int = 8) -> list[BoPRecord]:
        """Fetch India's quarterly Balance of Payments from IMF SDMX 3.0 MCP Server."""
        try:
            result = await self._call_imf_tool(
                tool_name="imf_query_dataset",
                arguments={
                    "dataflow_id": "BOP",
                    "key": "IND.NETCD_T.CAB+KAB.USD.Q",
                    "last_n_observations": lookback_quarters,
                },
            )
            structured = result.get("structuredContent", {})
            observations = structured.get("observations", [])

            by_period: dict[str, dict[str, float]] = {}
            for obs in observations:
                period = str(obs.get("time_period", "")).strip()
                series_key = str(obs.get("series_key", "")).strip()
                val = obs.get("value")
                if period and series_key and val is not None:
                    try:
                        by_period.setdefault(period, {})[series_key] = float(val)
                    except (ValueError, TypeError):
                        pass

            now = datetime.now(timezone.utc)
            records: list[BoPRecord] = []
            for period, series_map in sorted(by_period.items(), reverse=True):
                cab_usd = series_map.get("IND.NETCD_T.CAB.USD.Q")
                kab_usd = series_map.get("IND.NETCD_T.KAB.USD.Q")
                cab_bn = round(cab_usd / 1e9, 3) if cab_usd is not None else None
                kab_bn = round(kab_usd / 1e9, 3) if kab_usd is not None else None
                net_bop = round((cab_usd + (kab_usd or 0.0)) / 1e9, 3) if cab_usd is not None else None

                citation = Citation(
                    source_agent="external_sector",
                    source_authority="International Monetary Fund (IMF)",
                    document_title="Balance of Payments Statistics (BPM6)",
                    table_reference="IMF.STA/BOP/21.0.0",
                    retrieval_url="https://data.imf.org/",
                    observation_period=period,
                    fetched_at=now,
                    freshness=DataFreshness.LIVE,
                )
                records.append(
                    BoPRecord(
                        period=period,
                        current_account_balance_usd_bn=cab_bn,
                        capital_account_balance_usd_bn=kab_bn,
                        net_bop_usd_bn=net_bop,
                        citation=citation,
                    )
                )
            return records[:lookback_quarters]
        except Exception as exc:
            logger.warning("Failed to fetch quarterly BOP from IMF MCP: %s", exc)
            return []


imf_client = IMFClient()


async def fetch_imf_external_outlook(
    start_year: str = "2022",
    end_year: str = "2027",
) -> list[IMFExternalOutlookRecord]:
    """Fetch multilateral medium-term external outlook from IMF SDMX MCP server."""
    obs_list = await imf_client.get_india_weo_outlook(start_year, end_year)
    grouped: dict[str, dict[str, Any]] = {}

    for item in obs_list:
        p = str(item.get("period") or "").strip()
        if not p:
            continue
        if p not in grouped:
            grouped[p] = {"period": p, "source": item.get("source", "Source: IMF WEO")}
        k = str(item.get("series_key") or "")
        val = safe_float_val(item.get("value"))
        if "BCA_NGDPD" in k:
            grouped[p]["current_account_to_gdp_pct"] = round(val, 3) if val is not None else None
        elif "TX_RPCH" in k:
            grouped[p]["export_volume_growth_pct"] = round(val, 2) if val is not None else None
        elif "BCA." in k:
            grouped[p]["current_account_balance_usd_bn"] = round(val / 1e9, 2) if val is not None else None

    records = []
    for p in sorted(grouped.keys(), key=parse_period_sort_key, reverse=True):
        entry = grouped[p]
        citation = Citation(
            source_agent="external_sector",
            source_authority="International Monetary Fund (IMF)",
            document_title="IMF World Economic Outlook (WEO)",
            table_reference="imf.sdmx.weo.IND.BCA_NGDPD+TX_RPCH+BCA.A",
            retrieval_url="https://data.imf.org/",
            observation_period=str(p),
            freshness=DataFreshness.LIVE,
        )
        records.append(
            IMFExternalOutlookRecord(
                period=p,
                current_account_to_gdp_pct=entry.get("current_account_to_gdp_pct"),
                current_account_balance_usd_bn=entry.get("current_account_balance_usd_bn"),
                export_volume_growth_pct=entry.get("export_volume_growth_pct"),
                citation=citation,
            )
        )
    return records


