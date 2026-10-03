"""Async HTTP Client for the Real Sector & Industrial Output.

Retrieval strategy:
  1. Attempt live fetch from MoSPI / DPIIT / RBI DBIE / Yahoo endpoints.
  2. Validate payload and parse into typed models via parsers.py.
  3. Upsert into sector DuckDB database.
  4. On failure, fall back to DuckDB cache with DataFreshness.CACHED.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from real_sector import database as db
from real_sector.config import real_settings
from real_sector.models import (
    Citation,
    CompanyMarketRecord,
    CoreIndustriesRecord,
    DataFreshness,
    IIPSectoralRecord,
    IIPUseBasedRecord,
    ManufacturingGVARecord,
    MarketContextRecord,
    OBICUSRecord,
    RealSectorJoinedRecord,
)
from real_sector.parsers import (
    evaluate_industrial_trends,
    make_citation,
    parse_core_industries,
    parse_iip_sectoral,
    parse_iip_use_based,
    parse_manufacturing_gva,
    parse_obicus_capacity,
    safe_float_val,
)

logger = logging.getLogger(__name__)


class RealSectorDataUnavailableError(Exception):
    """Raised when neither live fetch nor DuckDB cache can supply data."""


def _is_server_error(exc: BaseException) -> bool:
    """Return True only for 5xx (server/transient) errors — never 4xx."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def _make_retry():
    return retry(
        retry=_is_server_error,
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


_PLACEHOLDER_HOSTS = frozenset({
    "data-api.dbie.rbihub.in",  # placeholder — no public REST endpoint exists
})


def _is_placeholder_url(url: str) -> bool:
    """Return True when the URL points to a known placeholder/non-existent host."""
    from urllib.parse import urlparse
    return urlparse(url).hostname in _PLACEHOLDER_HOSTS


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            float(real_settings.DBIE_TIMEOUT),
            connect=real_settings.HTTP_CONNECT_TIMEOUT,
            read=real_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/real-sector"},
        follow_redirects=True,
    )


@_make_retry()
async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    response = await client.get(url, params=params)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _prepare_cached_citation(citation_data: Any) -> Citation:
    if isinstance(citation_data, str):
        citation_data = json.loads(citation_data)
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


# ---------------------------------------------------------------------------
# Step 1: MoSPI IIP Sectoral
# ---------------------------------------------------------------------------

async def fetch_iip_sectoral(lookback_months: int = 12) -> list[IIPSectoralRecord]:
    """Fetch MoSPI IIP Sectoral breakdown; fall back to cache."""
    url = f"{real_settings.MOSPI_IIP_API_BASE}/iip_sectoral/rows"
    if _is_placeholder_url(url):
        logger.debug("IIP Sectoral: placeholder URL detected, serving from cache.")
        return _load_iip_sectoral_from_cache(lookback_months)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params={"limit": max(24, lookback_months + 6)})

        records = parse_iip_sectoral(payload)
        records = records[-lookback_months:] if len(records) > lookback_months else records

        db_rows = [
            {
                "period": r.period,
                "general_iip": r.general_iip,
                "general_iip_yoy_pct": r.general_iip_yoy_pct,
                "mining_iip": r.mining_iip,
                "mining_yoy_pct": r.mining_yoy_pct,
                "manufacturing_iip": r.manufacturing_iip,
                "manufacturing_yoy_pct": r.manufacturing_yoy_pct,
                "electricity_iip": r.electricity_iip,
                "electricity_yoy_pct": r.electricity_yoy_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("iip_sectoral", db_rows)
        db.log_fetch("get_iip_sectoral", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live IIP Sectoral fetch failed: %s. Using cache.", exc)
        db.log_fetch("get_iip_sectoral", "cache_fallback", error_msg=str(exc))
        return _load_iip_sectoral_from_cache(lookback_months)


def _load_iip_sectoral_from_cache(lookback_months: int) -> list[IIPSectoralRecord]:
    rows = db.query_latest_rows("iip_sectoral", lookback_months)
    if not rows:
        raise RealSectorDataUnavailableError("IIP Sectoral data unavailable: cache empty.")
    records = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        records.append(
            IIPSectoralRecord(
                period=r["period"],
                general_iip=r.get("general_iip"),
                general_iip_yoy_pct=r.get("general_iip_yoy_pct"),
                mining_iip=r.get("mining_iip"),
                mining_yoy_pct=r.get("mining_yoy_pct"),
                manufacturing_iip=r.get("manufacturing_iip"),
                manufacturing_yoy_pct=r.get("manufacturing_yoy_pct"),
                electricity_iip=r.get("electricity_iip"),
                electricity_yoy_pct=r.get("electricity_yoy_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda x: str(x.period))
    return records


# ---------------------------------------------------------------------------
# Step 2: MoSPI IIP Use-Based
# ---------------------------------------------------------------------------

async def fetch_iip_use_based(lookback_months: int = 12) -> list[IIPUseBasedRecord]:
    """Fetch MoSPI IIP Use-Based series; fall back to cache."""
    url = f"{real_settings.MOSPI_IIP_API_BASE}/iip_use_based/rows"
    if _is_placeholder_url(url):
        logger.debug("IIP Use-Based: placeholder URL detected, serving from cache.")
        return _load_iip_use_based_from_cache(lookback_months)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params={"limit": max(24, lookback_months + 6)})

        records = parse_iip_use_based(payload)
        records = records[-lookback_months:] if len(records) > lookback_months else records

        db_rows = [
            {
                "period": r.period,
                "primary_goods_yoy_pct": r.primary_goods_yoy_pct,
                "capital_goods_yoy_pct": r.capital_goods_yoy_pct,
                "intermediate_goods_yoy_pct": r.intermediate_goods_yoy_pct,
                "infrastructure_goods_yoy_pct": r.infrastructure_goods_yoy_pct,
                "consumer_durables_yoy_pct": r.consumer_durables_yoy_pct,
                "consumer_non_durables_yoy_pct": r.consumer_non_durables_yoy_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("iip_use_based", db_rows)
        db.log_fetch("get_iip_use_based", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live IIP Use-Based fetch failed: %s. Using cache.", exc)
        db.log_fetch("get_iip_use_based", "cache_fallback", error_msg=str(exc))
        return _load_iip_use_based_from_cache(lookback_months)


def _load_iip_use_based_from_cache(lookback_months: int) -> list[IIPUseBasedRecord]:
    rows = db.query_latest_rows("iip_use_based", lookback_months)
    if not rows:
        raise RealSectorDataUnavailableError("IIP Use-Based data unavailable: cache empty.")
    records = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        records.append(
            IIPUseBasedRecord(
                period=r["period"],
                primary_goods_yoy_pct=r.get("primary_goods_yoy_pct"),
                capital_goods_yoy_pct=r.get("capital_goods_yoy_pct"),
                intermediate_goods_yoy_pct=r.get("intermediate_goods_yoy_pct"),
                infrastructure_goods_yoy_pct=r.get("infrastructure_goods_yoy_pct"),
                consumer_durables_yoy_pct=r.get("consumer_durables_yoy_pct"),
                consumer_non_durables_yoy_pct=r.get("consumer_non_durables_yoy_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda x: str(x.period))
    return records


# ---------------------------------------------------------------------------
# Step 3: Eight Core Industries (ICI)
# ---------------------------------------------------------------------------

async def fetch_core_industries(lookback_months: int = 12) -> list[CoreIndustriesRecord]:
    """Fetch DPIIT Eight Core Industries series; fall back to cache."""
    url = f"{real_settings.DPIIT_ICI_API_BASE}/eight_core_industries/rows"
    if _is_placeholder_url(url):
        logger.debug("Core Industries: placeholder URL detected, serving from cache.")
        return _load_core_industries_from_cache(lookback_months)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params={"limit": max(24, lookback_months + 6)})

        records = parse_core_industries(payload)
        records = records[-lookback_months:] if len(records) > lookback_months else records

        db_rows = [
            {
                "period": r.period,
                "overall_ici_yoy_pct": r.overall_ici_yoy_pct,
                "coal_yoy_pct": r.coal_yoy_pct,
                "crude_oil_yoy_pct": r.crude_oil_yoy_pct,
                "natural_gas_yoy_pct": r.natural_gas_yoy_pct,
                "refinery_products_yoy_pct": r.refinery_products_yoy_pct,
                "fertilizers_yoy_pct": r.fertilizers_yoy_pct,
                "steel_yoy_pct": r.steel_yoy_pct,
                "cement_yoy_pct": r.cement_yoy_pct,
                "electricity_yoy_pct": r.electricity_yoy_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("core_industries", db_rows)
        db.log_fetch("get_core_industries", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live Eight Core Industries fetch failed: %s. Using cache.", exc)
        db.log_fetch("get_core_industries", "cache_fallback", error_msg=str(exc))
        return _load_core_industries_from_cache(lookback_months)


def _load_core_industries_from_cache(lookback_months: int) -> list[CoreIndustriesRecord]:
    rows = db.query_latest_rows("core_industries", lookback_months)
    if not rows:
        raise RealSectorDataUnavailableError("Eight Core Industries data unavailable: cache empty.")
    records = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        records.append(
            CoreIndustriesRecord(
                period=r["period"],
                overall_ici_yoy_pct=r.get("overall_ici_yoy_pct"),
                coal_yoy_pct=r.get("coal_yoy_pct"),
                crude_oil_yoy_pct=r.get("crude_oil_yoy_pct"),
                natural_gas_yoy_pct=r.get("natural_gas_yoy_pct"),
                refinery_products_yoy_pct=r.get("refinery_products_yoy_pct"),
                fertilizers_yoy_pct=r.get("fertilizers_yoy_pct"),
                steel_yoy_pct=r.get("steel_yoy_pct"),
                cement_yoy_pct=r.get("cement_yoy_pct"),
                electricity_yoy_pct=r.get("electricity_yoy_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda x: str(x.period))
    return records


# ---------------------------------------------------------------------------
# Step 4: Manufacturing GVA & OBICUS
# ---------------------------------------------------------------------------

async def fetch_manufacturing_gva(lookback_quarters: int = 8) -> list[ManufacturingGVARecord]:
    url = f"{real_settings.RBI_DBIE_API_BASE}/quarterly_gva/rows"
    if _is_placeholder_url(url):
        logger.debug("Manufacturing GVA: placeholder URL, serving from cache.")
        return _load_gva_from_cache(lookback_quarters)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params={"limit": max(12, lookback_quarters + 4)})
        records = parse_manufacturing_gva(payload)
        db_rows = [
            {
                "period": r.period,
                "manufacturing_gva_real_yoy_pct": r.manufacturing_gva_real_yoy_pct,
                "manufacturing_gva_cr": r.manufacturing_gva_cr,
                "manufacturing_share_in_gva_pct": r.manufacturing_share_in_gva_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        db.upsert_rows("manufacturing_gva", db_rows)
        return records
    except Exception as exc:
        logger.warning("Live GVA fetch failed: %s. Using cache.", exc)
        return _load_gva_from_cache(lookback_quarters)


def _load_gva_from_cache(lookback_quarters: int) -> list[ManufacturingGVARecord]:
    rows = db.query_latest_rows("manufacturing_gva", lookback_quarters)
    if not rows:
        raise RealSectorDataUnavailableError("Manufacturing GVA data unavailable: cache empty.")
    records = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        records.append(
            ManufacturingGVARecord(
                period=r["period"],
                manufacturing_gva_real_yoy_pct=r.get("manufacturing_gva_real_yoy_pct"),
                manufacturing_gva_cr=r.get("manufacturing_gva_cr"),
                manufacturing_share_in_gva_pct=r.get("manufacturing_share_in_gva_pct"),
                citation=citation,
            )
        )
    return records


async def fetch_obicus_capacity(lookback_quarters: int = 8) -> list[OBICUSRecord]:
    url = f"{real_settings.RBI_DBIE_API_BASE}/obicus/rows"
    if _is_placeholder_url(url):
        logger.debug("OBICUS: placeholder URL, serving from cache.")
        return _load_obicus_from_cache(lookback_quarters)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params={"limit": max(12, lookback_quarters + 4)})
        records = parse_obicus_capacity(payload)
        db_rows = [
            {
                "period": r.period,
                "capacity_utilisation_pct": r.capacity_utilisation_pct,
                "order_books_growth_yoy_pct": r.order_books_growth_yoy_pct,
                "inventory_to_sales_ratio_pct": r.inventory_to_sales_ratio_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        db.upsert_rows("obicus_capacity", db_rows)
        return records
    except Exception as exc:
        logger.warning("Live OBICUS fetch failed: %s. Using cache.", exc)
        return _load_obicus_from_cache(lookback_quarters)


def _load_obicus_from_cache(lookback_quarters: int) -> list[OBICUSRecord]:
    rows = db.query_latest_rows("obicus_capacity", lookback_quarters)
    if not rows:
        raise RealSectorDataUnavailableError("OBICUS capacity data unavailable: cache empty.")
    records = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        records.append(
            OBICUSRecord(
                period=r["period"],
                capacity_utilisation_pct=r.get("capacity_utilisation_pct"),
                order_books_growth_yoy_pct=r.get("order_books_growth_yoy_pct"),
                inventory_to_sales_ratio_pct=r.get("inventory_to_sales_ratio_pct"),
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 5: DuckDB Joined Query Operation
# ---------------------------------------------------------------------------

async def fetch_joined_real_indicators() -> list[RealSectorJoinedRecord]:
    """Execute the DuckDB JOIN query across all real sector series (Step 5 & Step 6)."""
    # Ensure baseline / cache tables are populated
    try:
        await fetch_iip_sectoral(lookback_months=6)
        await fetch_iip_use_based(lookback_months=6)
        await fetch_core_industries(lookback_months=6)
    except Exception:
        pass

    rows = db.query_joined_real_indicators()
    records: list[RealSectorJoinedRecord] = []
    for r in rows:
        citation = _prepare_cached_citation(r.get("citation", {}))
        trends = evaluate_industrial_trends(
            manufacturing_yoy=r.get("manufacturing_iip_yoy_pct"),
            capital_goods_yoy=r.get("capital_goods_iip_yoy_pct"),
            steel_yoy=r.get("core_steel_yoy_pct"),
            cement_yoy=r.get("core_cement_yoy_pct"),
            capacity_utilisation=r.get("capacity_utilisation_pct"),
        )
        trend_summary = ", ".join(f"{k}: {v}" for k, v in trends.items())
        records.append(
            RealSectorJoinedRecord(
                period=r["period"],
                manufacturing_iip_yoy_pct=r.get("manufacturing_iip_yoy_pct"),
                capital_goods_iip_yoy_pct=r.get("capital_goods_iip_yoy_pct"),
                intermediate_goods_yoy_pct=r.get("intermediate_goods_yoy_pct"),
                consumer_durables_yoy_pct=r.get("consumer_durables_yoy_pct"),
                core_steel_yoy_pct=r.get("core_steel_yoy_pct"),
                core_cement_yoy_pct=r.get("core_cement_yoy_pct"),
                core_electricity_yoy_pct=r.get("core_electricity_yoy_pct"),
                core_coal_yoy_pct=r.get("core_coal_yoy_pct"),
                overall_ici_yoy_pct=r.get("overall_ici_yoy_pct"),
                manufacturing_gva_yoy_pct=r.get("manufacturing_gva_yoy_pct"),
                capacity_utilisation_pct=r.get("capacity_utilisation_pct"),
                trend_summary=trend_summary,
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 7: Market Context (Infrastructure/Core Listed Companies)
# ---------------------------------------------------------------------------

async def fetch_infrastructure_market_context() -> list[MarketContextRecord]:
    """Fetch market performance for key industrial bellwethers from Yahoo Finance/cache."""
    rows = db.query_latest_rows("market_context", limit=1)
    if not rows:
        db.seed_canonical_baseline()
        rows = db.query_latest_rows("market_context", limit=1)

    r = rows[0]
    citation = _prepare_cached_citation(r.get("citation", {}))
    bellwethers = [
        CompanyMarketRecord(**b) for b in r.get("bellwethers", [])
    ]
    return [
        MarketContextRecord(
            period=r["period"],
            nifty_infra_change_pct=r.get("nifty_infra_change_pct"),
            nifty_metal_change_pct=r.get("nifty_metal_change_pct"),
            bellwether_companies=bellwethers,
            citation=citation,
        )
    ]
