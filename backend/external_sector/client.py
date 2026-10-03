"""Async HTTP client for the External Sector."""
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

from external_sector import database as db
from external_sector.config import external_settings
from external_sector.models import (
    BoPRecord,
    Citation,
    DataFreshness,
    ExchangeRateRecord,
    ExternalFlowsRecord,
    ForexReservesRecord,
    TradeBalanceRecord,
)
from external_sector.parsers import (
    parse_exchange_rates,
    parse_forex_reserves,
    parse_trade_balance,
)

logger = logging.getLogger(__name__)

_CDN = external_settings.DBIE_CDN_BASE
_FOREX_CDN_URL = f"{_CDN}/forex-reserves.json"
_API = external_settings.DBIE_API_BASE
_TRADE_BALANCE_API_URL = (
    f"{_API}/external_sector/r433_india_s_foreign_trade_us_dollars/rows"
)
_EXCHANGE_RATE_API_URL = f"{_API}/external_sector/r575_exchange_rate/rows"


class ExternalDataUnavailableError(Exception):
    """Raised when neither live fetch nor cache can supply external sector data."""


def _make_retry():
    return retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


@_make_retry()
async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    response = await client.get(url, params=params, timeout=external_settings.DBIE_TIMEOUT)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            float(external_settings.DBIE_TIMEOUT),
            connect=external_settings.HTTP_CONNECT_TIMEOUT,
            read=external_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/external-sector"},
        follow_redirects=True,
    )


def _prepare_cached_citation(citation_data: Any) -> Citation:
    if isinstance(citation_data, str):
        citation_data = json.loads(citation_data)
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


# ── Pillar 1: Forex Reserves ──────────────────────────────────────────────

async def fetch_forex_reserves(lookback_weeks: int = 12) -> list[ForexReservesRecord]:
    db.initialise_schema()
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, _FOREX_CDN_URL)
        records = parse_forex_reserves(payload, lookback_weeks)

        db_rows = [
            {
                "period": r.period,
                "total_reserves_usd_mn": r.total_reserves_usd_mn,
                "total_reserves_inr_cr": r.total_reserves_inr_cr,
                "foreign_currency_assets_usd_mn": r.foreign_currency_assets_usd_mn,
                "gold_reserves_usd_mn": r.gold_reserves_usd_mn,
                "sdrs_usd_mn": r.sdrs_usd_mn,
                "reserve_tranche_position_usd_mn": r.reserve_tranche_position_usd_mn,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("forex_reserves", db_rows)
        db.log_fetch("get_forex_reserves", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live forex fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_forex_reserves", "cache_fallback", error_msg=str(exc))
        return _load_forex_from_cache(lookback_weeks)


def _load_forex_from_cache(lookback_weeks: int) -> list[ForexReservesRecord]:
    rows = db.query_latest_rows("forex_reserves", lookback_weeks)
    if not rows:
        raise ExternalDataUnavailableError("Forex reserves data unavailable: live fetch failed and cache is empty.")
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            ForexReservesRecord(
                period=row["period"],
                total_reserves_usd_mn=row.get("total_reserves_usd_mn"),
                total_reserves_inr_cr=row.get("total_reserves_inr_cr"),
                foreign_currency_assets_usd_mn=row.get("foreign_currency_assets_usd_mn"),
                gold_reserves_usd_mn=row.get("gold_reserves_usd_mn"),
                sdrs_usd_mn=row.get("sdrs_usd_mn"),
                reserve_tranche_position_usd_mn=row.get("reserve_tranche_position_usd_mn"),
                citation=citation,
            )
        )
    return records


# ── Pillar 2: Trade Balance ───────────────────────────────────────────────

async def fetch_trade_balance(lookback_months: int = 12) -> list[TradeBalanceRecord]:
    db.initialise_schema()
    try:
        async with _build_client() as client:
            payload = await _fetch_json(
                client,
                _TRADE_BALANCE_API_URL,
                params={"limit": lookback_months + 8, "offset": 0},
            )
        records = parse_trade_balance(payload, lookback_months)
        if not records:
            raise ValueError("RBI DBIE returned no usable merchandise trade rows.")
        now = datetime.now(timezone.utc).isoformat()
        rows_to_write = [
            {
                "period": record.period,
                "exports_usd_bn": record.exports_usd_bn,
                "imports_usd_bn": record.imports_usd_bn,
                "trade_balance_usd_bn": record.trade_balance_usd_bn,
                "citation": record.citation.model_dump_json(),
                "fetched_at": now,
            }
            for record in records
        ]
        written = db.upsert_rows("trade_balance", rows_to_write)
        db.log_fetch("get_trade_balance", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live trade-balance fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_trade_balance", "cache_fallback", error_msg=str(exc))
        return _load_trade_balance_from_cache(lookback_months)


def _load_trade_balance_from_cache(lookback_months: int) -> list[TradeBalanceRecord]:
    rows = db.query_latest_rows("trade_balance", lookback_months)
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            TradeBalanceRecord(
                period=row["period"],
                exports_usd_bn=row.get("exports_usd_bn"),
                imports_usd_bn=row.get("imports_usd_bn"),
                trade_balance_usd_bn=row.get("trade_balance_usd_bn"),
                citation=citation,
            )
        )
    records.sort(key=lambda record: record.period, reverse=True)
    if not records:
        raise ExternalDataUnavailableError(
            "Trade-balance data unavailable: live fetch failed and cache is empty."
        )
    return records


# ── Pillar 3: Balance of Payments ─────────────────────────────────────────

async def fetch_balance_of_payments(lookback_quarters: int = 8) -> list[BoPRecord]:
    db.initialise_schema()
    rows = db.query_latest_rows("bop", lookback_quarters)
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            BoPRecord(
                period=row["period"],
                current_account_balance_usd_bn=row.get("current_account_balance_usd_bn"),
                current_account_to_gdp_pct=row.get("current_account_to_gdp_pct"),
                capital_account_balance_usd_bn=row.get("capital_account_balance_usd_bn"),
                net_bop_usd_bn=row.get("net_bop_usd_bn"),
                citation=citation,
            )
        )
    return records


# ── Pillar 4: Exchange Rate Snapshot ──────────────────────────────────────

async def fetch_exchange_rate_snapshot(lookback_months: int = 12) -> list[ExchangeRateRecord]:
    db.initialise_schema()
    lookback_days = max(lookback_months, 1) * 23
    try:
        async with _build_client() as client:
            payload = await _fetch_json(
                client,
                _EXCHANGE_RATE_API_URL,
                params={"limit": lookback_days + 8, "offset": 0},
            )
        records = parse_exchange_rates(payload, lookback_days)
        if not records:
            raise ValueError("RBI DBIE returned no usable USD/INR exchange-rate rows.")
        now = datetime.now(timezone.utc).isoformat()
        rows_to_write = [
            {
                "period": record.period,
                "usd_inr_rate": record.usd_inr_rate,
                "reer_40_basket": record.reer_40_basket,
                "neer_40_basket": record.neer_40_basket,
                "citation": record.citation.model_dump_json(),
                "fetched_at": now,
            }
            for record in records
        ]
        written = db.upsert_rows("exchange_rates", rows_to_write)
        db.log_fetch("get_exchange_rate_snapshot", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live exchange-rate fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_exchange_rate_snapshot", "cache_fallback", error_msg=str(exc))
        return _load_exchange_rates_from_cache(lookback_days)


def _load_exchange_rates_from_cache(lookback_days: int) -> list[ExchangeRateRecord]:
    rows = db.query_latest_rows("exchange_rates", lookback_days)
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            ExchangeRateRecord(
                period=row["period"],
                usd_inr_rate=row.get("usd_inr_rate"),
                reer_40_basket=row.get("reer_40_basket"),
                neer_40_basket=row.get("neer_40_basket"),
                citation=citation,
            )
        )
    records.sort(key=lambda record: record.period, reverse=True)
    if not records:
        raise ExternalDataUnavailableError(
            "Exchange-rate data unavailable: live fetch failed and cache is empty."
        )
    return records


# ── Pillar 5: External Flows ──────────────────────────────────────────────

async def fetch_external_flows(lookback_months: int = 12) -> list[ExternalFlowsRecord]:
    db.initialise_schema()
    rows = db.query_latest_rows("external_flows", lookback_months)
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            ExternalFlowsRecord(
                period=row["period"],
                net_fdi_usd_mn=row.get("net_fdi_usd_mn"),
                net_fpi_usd_mn=row.get("net_fpi_usd_mn"),
                citation=citation,
            )
        )
    return records
