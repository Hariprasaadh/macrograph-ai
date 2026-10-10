"""National Accounts fetcher for the Real Sector (GDP & GFCF).

Primary source — MoSPI NAS MCP (https://mcp.mospi.gov.in/, per readmeformcp.md
4-tool workflow: get_indicators -> get_metadata -> get_data):
  - indicator_code 5 (Gross Domestic Product): current_price = nominal GDP,
    constant_price = real GDP, unit Rs Crore, base 2011-12 (15-year history).
  - indicator_code 9 (Gross Fixed Capital Formation): same price split.

Fallback source — IMF WEO MCP (https://imf.caseyjhand.com/mcp, per
readmeformcp.md): IND.NGDP_RPCH.A (real growth %) and IND.NGDP.A (nominal
level). Projection years beyond the current calendar year are dropped.

Rules:
  - One row per financial year: the latest estimate vintage wins
    (Final > Revised > Provisional > Advance).
  - YoY growth is computed from same-vintage levels, never mixed across bases.
  - No hardcoded economic values. Unavailable data raises
    RealSectorDataUnavailableError so callers return the Unavailable sentinel.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastmcp import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from real_sector.config import real_settings
from real_sector.models import Citation, DataFreshness, GDPRecord, GFCFRecord
from real_sector.parsers import make_citation, safe_float_val

logger = logging.getLogger(__name__)


class RealSectorDataUnavailableError(Exception):
    """Raised when national-accounts data cannot be retrieved from any authorized MCP server."""


NAS_BASE_YEAR = "2011-12"
NAS_SERIES = "Current"
NAS_FREQUENCY_CODE = 1
NAS_INDICATOR_GDP = 5
NAS_INDICATOR_GFCF = 9
IMF_MCP_URL = "https://imf.caseyjhand.com/mcp"

# Higher wins. Matched on revision_name so all NAS bases share one ordering.
_REVISION_PRIORITY = (
    ("final estimates", 80),
    ("third revised", 70),
    ("second revised", 60),
    ("first revised", 50),
    ("provisional", 40),
    ("second advance", 30),
    ("first advance", 20),
)


def _revision_rank(name: Any) -> int:
    lowered = str(name or "").strip().lower()
    for needle, rank in _REVISION_PRIORITY:
        if needle in lowered:
            return rank
    return 0


def _yoy(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100.0, 2)


@retry(
    retry=retry_if_exception_type((Exception,)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(2),
    reraise=True,
)
async def _call_nas_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with Client(real_settings.MOSPI_MCP_URL, timeout=real_settings.MCP_TIMEOUT) as client:
        res = await client.call_tool(tool_name, arguments)
        if getattr(res, "is_error", False):
            raise RuntimeError(f"MoSPI NAS MCP tool {tool_name} returned error: {res.content}")
        data = getattr(res, "structured_content", None)
        if isinstance(data, dict) and data:
            return data
        content = getattr(res, "content", [])
        text = content[0].text if content and hasattr(content[0], "text") else ""
        import json as _json

        return _json.loads(text) if text else {}


async def _fetch_nas_indicator(indicator_code: int, limit: int = 100) -> list[dict[str, Any]]:
    """Page through NAS get_data until all records for the indicator are collected."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = await _call_nas_mcp(
            "get_data",
            {
                "dataset": "NAS",
                "filters": {
                    "indicator_code": indicator_code,
                    "base_year": NAS_BASE_YEAR,
                    "series": NAS_SERIES,
                    "frequency_code": NAS_FREQUENCY_CODE,
                    "limit": limit,
                    "page": page,
                },
            },
        )
        if payload.get("error"):
            raise RuntimeError(f"NAS get_data error: {payload.get('error')}")
        batch = payload.get("data", [])
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(r for r in batch if isinstance(r, dict))
        meta = payload.get("meta_data", {}) or {}
        total_pages = meta.get("totalPages")
        if total_pages is None or page >= int(total_pages):
            break
        page += 1
        if page > 60:
            logger.warning("NAS pagination exceeded 60 pages for indicator %s", indicator_code)
            break
    return rows


def _dedup_by_vintage(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the highest-priority estimate vintage per financial year."""
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        year = str(row.get("year") or "").strip()
        if not year:
            continue
        rank = _revision_rank(row.get("revision"))
        prev = best.get(year)
        if prev is None or rank >= _revision_rank(prev.get("revision")):
            best[year] = row
    return best


def _sort_years(years: list[str]) -> list[str]:
    def _key(year: str) -> tuple[int, ...]:
        parts = year.replace("-", " ").split()
        nums: list[int] = []
        for part in parts:
            try:
                nums.append(int(part))
            except ValueError:
                continue
        return tuple(nums) if nums else (0,)

    return sorted(years, key=_key)


async def fetch_gdp(lookback_years: int = 10) -> list[GDPRecord]:
    """Fetch annual real + nominal GDP from MoSPI NAS (IMF WEO fallback)."""
    try:
        rows = await _fetch_nas_indicator(NAS_INDICATOR_GDP)
        yearly = _dedup_by_vintage(rows)
        ordered = _sort_years(list(yearly.keys()))
        if not ordered:
            raise RealSectorDataUnavailableError("No GDP rows returned from MoSPI NAS.")
        records: list[GDPRecord] = []
        prev_real: float | None = None
        prev_nominal: float | None = None
        for year in ordered:
            row = yearly[year]
            real = safe_float_val(row.get("constant_price"))
            nominal = safe_float_val(row.get("current_price"))
            real_yoy = _yoy(real, prev_real)
            nominal_yoy = _yoy(nominal, prev_nominal)
            deflator = (
                round((1 + (nominal_yoy or 0) / 100) / (1 + (real_yoy or 0) / 100) * 100 - 100, 2)
                if real_yoy is not None and nominal_yoy is not None
                else None
            )
            records.append(
                GDPRecord(
                    period=year,
                    real_gdp_cr=real,
                    nominal_gdp_cr=nominal,
                    real_gdp_yoy_pct=real_yoy,
                    nominal_gdp_yoy_pct=nominal_yoy,
                    gdp_deflator_yoy_pct=deflator,
                    base_year=str(row.get("base_year") or NAS_BASE_YEAR),
                    revision=str(row.get("revision") or "Unknown"),
                    citation=make_citation(
                        authority="National Statistical Office (NSO), MoSPI",
                        document_title="National Accounts Statistics — Gross Domestic Product",
                        table_reference="MoSPI eSankhyiki NAS indicator_code=5 (Annual, Base 2011-12)",
                        retrieval_url="https://mcp.mospi.gov.in/",
                        observation_period=year,
                        freshness=DataFreshness.LIVE,
                        dataset="gdp",
                        frequency="Annual",
                        unit="Rs Crore",
                        as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    ),
                )
            )
            if real is not None:
                prev_real = real
            if nominal is not None:
                prev_nominal = nominal
        return records[-lookback_years:] if len(records) > lookback_years else records
    except RealSectorDataUnavailableError:
        raise
    except Exception as exc:
        logger.warning("MoSPI NAS GDP fetch failed, trying IMF WEO fallback: %s", exc)
        return await _fetch_gdp_imf_fallback(lookback_years)


async def _fetch_gdp_imf_fallback(lookback_years: int) -> list[GDPRecord]:
    """IMF WEO fallback: real growth (NGDP_RPCH) + nominal level (NGDP), actuals only."""

    async def _query(key: str) -> list[dict[str, Any]]:
        async with Client(IMF_MCP_URL, timeout=real_settings.MCP_TIMEOUT) as client:
            res = await client.call_tool(
                "imf_query_dataset",
                {"dataflow_id": "WEO", "key": key, "last_n_observations": lookback_years + 8},
            )
            data = getattr(res, "structured_content", None) or {}
            obs = data.get("observations", [])
            return [o for o in obs if isinstance(o, dict)]

    try:
        current_year = datetime.now(timezone.utc).year
        real_rows, nominal_rows = await asyncio.gather(
            _query("IND.NGDP_RPCH.A"), _query("IND.NGDP.A")
        )
        real_by_year = {
            str(o.get("time_period")): safe_float_val(o.get("value"))
            for o in real_rows
            if str(o.get("time_period")).isdigit() and int(o["time_period"]) <= current_year
        }
        nominal_by_year = {
            str(o.get("time_period")): safe_float_val(o.get("value"))
            for o in nominal_rows
            if str(o.get("time_period")).isdigit() and int(o["time_period"]) <= current_year
        }
        years = sorted(set(real_by_year) | set(nominal_by_year))[-lookback_years:]
        if not years:
            raise RealSectorDataUnavailableError("No IMF WEO GDP observations for India.")
        records = []
        for year in years:
            nominal_inr = nominal_by_year.get(year)
            records.append(
                GDPRecord(
                    period=year,
                    real_gdp_cr=None,
                    nominal_gdp_cr=round(nominal_inr / 1e7, 1) if nominal_inr else None,
                    real_gdp_yoy_pct=real_by_year.get(year),
                    nominal_gdp_yoy_pct=None,
                    gdp_deflator_yoy_pct=None,
                    base_year=None,
                    revision="IMF WEO estimate",
                    citation=Citation(
                        source_agent="real_sector",
                        source_authority="International Monetary Fund",
                        document_title="World Economic Outlook (WEO) — India",
                        table_reference="WEO IND.NGDP_RPCH.A / IND.NGDP.A",
                        retrieval_url="https://data.imf.org/",
                        observation_period=year,
                        freshness=DataFreshness.LIVE,
                        dataset="gdp",
                        frequency="Annual",
                        unit="%; INR",
                    ),
                )
            )
        return records
    except RealSectorDataUnavailableError:
        raise
    except Exception as exc:
        raise RealSectorDataUnavailableError(f"GDP unavailable from MoSPI NAS and IMF WEO: {exc}") from exc


async def fetch_gfcf(lookback_years: int = 10) -> list[GFCFRecord]:
    """Fetch annual real + nominal GFCF from MoSPI NAS (all institutional sectors)."""
    try:
        rows = await _fetch_nas_indicator(NAS_INDICATOR_GFCF)
        aggregate = [r for r in rows if r.get("institutional_sector") in (None, "", "Total")]
        yearly = _dedup_by_vintage(aggregate or rows)
        ordered = _sort_years(list(yearly.keys()))
        if not ordered:
            raise RealSectorDataUnavailableError("No GFCF rows returned from MoSPI NAS.")
        gdp_rows = await _fetch_nas_indicator(NAS_INDICATOR_GDP)
        gdp_yearly = _dedup_by_vintage(gdp_rows)
        records: list[GFCFRecord] = []
        prev_real: float | None = None
        prev_nominal: float | None = None
        for year in ordered:
            row = yearly[year]
            real = safe_float_val(row.get("constant_price"))
            nominal = safe_float_val(row.get("current_price"))
            gdp_nominal = safe_float_val((gdp_yearly.get(year) or {}).get("current_price"))
            records.append(
                GFCFRecord(
                    period=year,
                    real_gfcf_cr=real,
                    nominal_gfcf_cr=nominal,
                    real_gfcf_yoy_pct=_yoy(real, prev_real),
                    nominal_gfcf_yoy_pct=_yoy(nominal, prev_nominal),
                    gfcf_to_gdp_pct=round(nominal / gdp_nominal * 100, 2)
                    if nominal and gdp_nominal
                    else None,
                    base_year=str(row.get("base_year") or NAS_BASE_YEAR),
                    revision=str(row.get("revision") or "Unknown"),
                    citation=make_citation(
                        authority="National Statistical Office (NSO), MoSPI",
                        document_title="National Accounts Statistics — Gross Fixed Capital Formation",
                        table_reference="MoSPI eSankhyiki NAS indicator_code=9 (Annual, Base 2011-12)",
                        retrieval_url="https://mcp.mospi.gov.in/",
                        observation_period=year,
                        freshness=DataFreshness.LIVE,
                        dataset="gfcf",
                        frequency="Annual",
                        unit="Rs Crore",
                        as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    ),
                )
            )
            if real is not None:
                prev_real = real
            if nominal is not None:
                prev_nominal = nominal
        return records[-lookback_years:] if len(records) > lookback_years else records
    except RealSectorDataUnavailableError:
        raise
    except Exception as exc:
        raise RealSectorDataUnavailableError(f"GFCF data unavailable from MoSPI NAS: {exc}") from exc
