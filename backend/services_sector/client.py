"""Async HTTP client for the Services Sector.

Retrieval strategy (resilient caching):
  1. Attempt live fetch from MoSPI e-Sankhyiki MCP (ISP + NAS datasets).
  2. Validate the raw payload — reject obviously malformed responses.
  3. Parse into typed Pydantic models (via parsers.py) and upsert into sector DuckDB.
  4. On ANY fetch failure, fall back to the most recent cached rows in DuckDB
     and return with DataFreshness.CACHED so callers know the data age.

Rules:
  - No hardcoded economic numbers anywhere in this file.
  - If live fetch fails AND cache is empty -> raise ServicesDataUnavailableError.
  - All outbound HTTP calls are wrapped with Tenacity retry logic.
  - httpx.AsyncClient is used exclusively (no requests, no blocking I/O).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from services_sector import database as db
from services_sector import mospi_client as mcp
from services_sector.cache_loaders import (
    ServicesDataUnavailableError,
    load_freight_from_cache,
    load_gva_from_cache,
    load_isp_from_cache,
    load_pmi_from_cache,
)
from services_sector.models import (
    ISPRecord,
    ServicesGVARecord,
    ServicesPMIRecord,
    ServiceSubSector,
    TransportFreightRecord,
)
from services_sector.parsers import (
    parse_isp_records,
    parse_services_gva,
    parse_services_pmi,
    parse_transport_freight,
)

logger = logging.getLogger(__name__)

# Financial years queried for ISP history (verified live via get_metadata('ISP')).
_ISP_FY_YEARS = ("2026-27", "2025-26")

# Bound concurrent MCP calls so one agent run cannot hammer the MoSPI endpoint.
_MCP_CONCURRENCY = 8
_mcp_semaphore = asyncio.Semaphore(_MCP_CONCURRENCY)


async def _bounded_isp_fetch(code: int, year: str) -> Any:
    """Fetch one ISP sub-sector/year slice under the concurrency guard."""
    async with _mcp_semaphore:
        return await mcp.get_data("ISP", mcp.isp_sector_year_filters(code, year))


# ── Pillar 1: ISP Growth ──────────────────────────────────────────────────

async def fetch_isp_growth(
    sub_sector: ServiceSubSector | None = None,
    lookback_months: int = 12,
) -> list[ISPRecord]:
    """Fetch monthly ISP from MoSPI MCP (19 sub-sectors); fall back to cache."""
    try:
        # Validated ISP filters: frequency_code 2 = Monthly + FY year.
        # The upstream API caps unfiltered calls (~10 rows) and rejects
        # 'limit', so fetch each of the 19 sub-sector codes per FY year
        # concurrently and combine the monthly series.
        combos = [
            (code, year)
            for year in _ISP_FY_YEARS
            for code in mcp.ISP_SUB_SECTOR_CODES.values()
        ]
        payloads = await asyncio.gather(*[
            _bounded_isp_fetch(code, year)
            for code, year in combos
        ], return_exceptions=True)

        from services_sector.parsers import extract_rows
        combined: dict[str, Any] = {"data": []}
        for payload in payloads:
            if isinstance(payload, Exception):
                logger.warning("ISP sub-sector fetch skipped: %s", payload)
                continue
            combined["data"].extend(extract_rows(payload))

        records = parse_isp_records(combined, lookback_months * 2)
        if sub_sector is not None:
            records = [r for r in records if r.sub_sector == sub_sector]
            records = records[-lookback_months:] if len(records) > lookback_months else records

        db_rows = [
            {
                "period": r.period,
                "sub_sector": r.sub_sector.value,
                "isp_index": r.isp_index,
                "isp_yoy_pct": r.isp_yoy_pct,
                "isp_mom_pct": r.isp_mom_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("isp_growth", db_rows)
        db.log_fetch("get_isp_growth", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live ISP fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_isp_growth", "cache_fallback", error_msg=str(exc))
        return load_isp_from_cache(sub_sector, lookback_months)


# ── Pillar 2: Services GVA (NAS) ──────────────────────────────────────────

async def fetch_services_gva() -> list[ServicesGVARecord]:
    """Fetch Services GVA (NAS indicator 1, services industries) from MoSPI MCP; fall back to cache."""
    try:
        # Validated NAS filters: indicator_code 1 = GVA, base 2011-12 Current
        # series, annual frequency — one call per services industry_code.
        payloads = await asyncio.gather(*[
            mcp.get_data("NAS", mcp.nas_gva_filters(industry_code))
            for industry_code in mcp.NAS_SERVICES_INDUSTRY_CODES
        ])

        from services_sector.parsers import extract_rows
        all_rows: list[dict] = []
        for payload in payloads:
            all_rows.extend(extract_rows(payload))

        records = parse_services_gva({"data": all_rows})

        db_rows = [
            {
                "period": r.period,
                "nas_statement": r.nas_statement,
                "segment": r.segment,
                "gva_current_cr": r.gva_current_cr,
                "gva_constant_cr": r.gva_constant_cr,
                "gva_yoy_pct": r.gva_yoy_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("services_gva", db_rows)
        db.log_fetch("get_services_gva", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live services GVA fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_services_gva", "cache_fallback", error_msg=str(exc))
        return load_gva_from_cache()


# ── Pillar 3: Services PMI ────────────────────────────────────────────────

async def fetch_services_pmi(lookback_months: int = 12) -> list[ServicesPMIRecord]:
    """Return Services PMI sentiment from the curated press-release mirror.

    Verified 2026-10-05: no PMI dataset exists on the MoSPI e-Sankhyiki MCP
    (27 datasets, none covering PMI — it is proprietary S&P Global / HSBC
    survey data). There is therefore no MCP service for this function.
    The sector stores the latest press-release observations in DuckDB and
    reports them honestly as CACHED; real-time PMI headlines arrive via the
    Tavily news tool in the agent layer.
    """
    db.log_fetch("get_services_pmi", "curated_mirror")
    return load_pmi_from_cache(lookback_months)


# ── Pillar 4: Transport, Freight & Telecom ────────────────────────────────

async def fetch_transport_and_freight(lookback_months: int = 6) -> list[TransportFreightRecord]:
    """Fetch NSS80 CMST telecom-penetration data (All-India); fall back to cache."""
    try:
        # Validated NSS80 filters: indicator_code 17/18 (phone/internet),
        # state_code 37 = All-India. Values are % of households.
        payloads = await asyncio.gather(*[
            mcp.get_data("NSS80", mcp.nss80_telecom_filters(indicator_code))
            for indicator_code in mcp.NSS80_TELECOM_INDICATORS
        ])
        from services_sector.parsers import extract_rows
        rows: list[dict] = []
        for payload in payloads:
            rows.extend(extract_rows(payload))
        if not rows:
            raise ValueError("Empty NSS80 telecom payload.")
        records = parse_transport_freight({"data": rows}, lookback_months * 10)

        db_rows = [
            {
                "period": r.period,
                "indicator": r.indicator,
                "value": r.value,
                "unit": r.unit,
                "yoy_pct": r.yoy_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("transport_freight", db_rows)
        db.log_fetch("get_transport_and_freight_indicators", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live transport/freight fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_transport_and_freight_indicators", "cache_fallback", error_msg=str(exc))
        return load_freight_from_cache(lookback_months)
