"""Async HTTP client for the Finance Sector.

Retrieval strategy (resilient caching):
  1. Attempt live fetch from RBI DBIE (CDN JSON or Postgres REST API).
  2. Validate the raw payload — reject obviously malformed responses.
  3. Parse into typed Pydantic models (via parsers.py) and upsert into sector DuckDB.
  4. On ANY fetch failure, fall back to the most recent cached rows in DuckDB
     and return with DataFreshness.CACHED so callers know the data age.

Rules:
  - No hardcoded economic numbers anywhere in this file.
  - If live fetch fails AND cache is empty -> raise FinanceDataUnavailableError.
  - All outbound HTTP calls are wrapped with Tenacity retry logic.
  - httpx.AsyncClient is used exclusively (no requests, no blocking I/O).
"""
from __future__ import annotations

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

from finance_sector import database as db
from finance_sector.cache_loaders import (
    FinanceDataUnavailableError,
    load_asset_quality_from_cache,
    load_credit_from_cache,
    load_deposits_from_cache,
    load_lending_rates_from_cache,
)
from finance_sector.config import finance_settings
from finance_sector.market_client import (
    fetch_banking_market_indicators,
    fetch_realtime_finance_news,
)
from finance_sector.models import (
    BankCreditGrowthRecord,
    BankGroup,
    DepositRecord,
    LendingRateRecord,
    NPARecord,
)
from finance_sector.parsers import (
    parse_asset_quality,
    parse_credit_records,
    parse_deposits,
    parse_lending_rates,
)

logger = logging.getLogger(__name__)

# ── DBIE endpoints ─────────────────────────────────────────────────────────
_CDN = finance_settings.DBIE_CDN_BASE
_API = finance_settings.DBIE_API_BASE

_CREDIT_CDN_URL = f"{_CDN}/bank-credit-by-sector.json"
_BANK_SURVEY_CDN_URL = f"{_CDN}/commercial-bank-survey.json"
_BUSINESS_CDN_URL = f"{_CDN}/business-of-scheduled-banks.json"
_RATES_API_URL = f"{_API}/financial_sector/r531_key_rates/rows"
_MPC_RATES_API_URL = f"{_API}/financial_sector/r1491_mpc_voting_pattern_policy_rate/rows"
_NPA_API_URL = (
    f"{_API}/financial_sector/"
    "r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou/rows"
)
_CRAR_API_URL = (
    f"{_API}/financial_sector/"
    "r329_distribution_of_scheduled_commercial_banks_by_crar/rows"
)


# ── Tenacity retry decorator & HTTP client ────────────────────────────────

def _make_retry():
    return retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


@_make_retry()
async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    """Fetch and parse a JSON response. Raises on non-2xx."""
    response = await client.get(url, params=params, timeout=finance_settings.DBIE_TIMEOUT)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            float(finance_settings.DBIE_TIMEOUT),
            connect=finance_settings.HTTP_CONNECT_TIMEOUT,
            read=finance_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/finance-sector"},
        follow_redirects=True,
    )


# ── Pillar 1: Bank Credit Growth ──────────────────────────────────────────

async def fetch_bank_credit_growth(lookback_months: int = 12) -> list[BankCreditGrowthRecord]:
    """Fetch sectoral bank credit from RBI DBIE CDN; fall back to cache."""
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, _CREDIT_CDN_URL)

        records = parse_credit_records(payload)
        records = records[-lookback_months:] if len(records) > lookback_months else records

        db_rows = [
            {
                "period": r.period,
                "gross_credit_cr": r.gross_credit_cr,
                "non_food_credit_cr": r.non_food_credit_cr,
                "non_food_credit_yoy_pct": r.non_food_credit_yoy_pct,
                "agriculture_cr": r.sectoral.agriculture_cr,
                "industry_cr": r.sectoral.industry_cr,
                "industry_msme_cr": r.sectoral.industry_msme_cr,
                "industry_large_cr": r.sectoral.industry_large_cr,
                "services_cr": r.sectoral.services_cr,
                "personal_loans_cr": r.sectoral.personal_loans_cr,
                "personal_housing_cr": r.sectoral.personal_housing_cr,
                "personal_vehicle_cr": r.sectoral.personal_vehicle_cr,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("bank_credit_growth", db_rows)
        db.log_fetch("get_bank_credit_growth", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live credit fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_bank_credit_growth", "cache_fallback", error_msg=str(exc))
        return load_credit_from_cache(lookback_months)


# ── Pillar 2: Asset Quality & Capital Adequacy ────────────────────────────

async def fetch_asset_quality(
    bank_group: BankGroup = BankGroup.ALL_SCB,
    lookback_quarters: int = 8,
) -> list[NPARecord]:
    """Fetch NPA and CRAR data from DBIE Postgres REST API; fall back to cache."""
    try:
        async with _build_client() as client:
            npa_payload = await _fetch_json(
                client, _NPA_API_URL, params={"limit": 200, "offset": 0}
            )
            crar_payload = await _fetch_json(
                client, _CRAR_API_URL, params={"limit": 200, "offset": 0}
            )

        records = parse_asset_quality(npa_payload, crar_payload, bank_group, lookback_quarters)

        db_rows = [
            {
                "period": r.period,
                "bank_group": r.bank_group.value,
                "gross_npa_pct": r.gross_npa_pct,
                "net_npa_pct": r.net_npa_pct,
                "gross_npa_cr": r.gross_npa_cr,
                "net_npa_cr": r.net_npa_cr,
                "provision_coverage_ratio_pct": r.provision_coverage_ratio_pct,
                "crar_pct": r.crar_pct,
                "cet1_pct": r.cet1_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("asset_quality", db_rows)
        db.log_fetch("get_asset_quality", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live asset quality fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_asset_quality", "cache_fallback", error_msg=str(exc))
        return load_asset_quality_from_cache(bank_group, lookback_quarters)


# ── Pillar 3: Lending Rates ───────────────────────────────────────────────

async def fetch_lending_rates(lookback_months: int = 12) -> list[LendingRateRecord]:
    """Fetch WALR/MCLR/WADTDR and Policy Rates from DBIE; fall back to cache."""
    try:
        async with _build_client() as client:
            try:
                mpc_payload = await _fetch_json(
                    client, _MPC_RATES_API_URL, params={"limit": max(50, lookback_months + 15), "offset": 0}
                )
                records = parse_lending_rates(mpc_payload, lookback_months)
            except Exception:
                payload = await _fetch_json(
                    client, _RATES_API_URL, params={"limit": max(50, lookback_months + 15), "offset": 0}
                )
                records = parse_lending_rates(payload, lookback_months)

        db_rows = [
            {
                "period": r.period,
                "walr_fresh_pct": r.walr_fresh_pct,
                "walr_outstanding_pct": r.walr_outstanding_pct,
                "mclr_1yr_median_pct": r.mclr_1yr_median_pct,
                "wadtdr_fresh_pct": r.wadtdr_fresh_pct,
                "wadtdr_outstanding_pct": r.wadtdr_outstanding_pct,
                "repo_rate_pct": r.repo_rate_pct,
                "lending_spread_over_repo_pct": r.lending_spread_over_repo_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("lending_rates", db_rows)
        db.log_fetch("get_lending_and_deposit_rates", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live lending rates fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_lending_and_deposit_rates", "cache_fallback", error_msg=str(exc))
        return load_lending_rates_from_cache(lookback_months)


# ── Pillar 4: Deposits & CD Ratio ─────────────────────────────────────────

async def fetch_deposits_and_cd_ratio(lookback_months: int = 12) -> list[DepositRecord]:
    """Fetch deposit and CD ratio data from RBI DBIE CDN; fall back to cache."""
    try:
        async with _build_client() as client:
            survey = await _fetch_json(client, _BANK_SURVEY_CDN_URL)
            business = await _fetch_json(client, _BUSINESS_CDN_URL)

        records = parse_deposits(survey, business, lookback_months)
        db_rows = [
            {
                "period": r.period,
                "aggregate_deposits_cr": r.aggregate_deposits_cr,
                "deposits_yoy_pct": r.deposits_yoy_pct,
                "demand_deposits_cr": r.demand_deposits_cr,
                "time_deposits_cr": r.time_deposits_cr,
                "casa_ratio_pct": r.casa_ratio_pct,
                "bank_credit_cr": r.bank_credit_cr,
                "cd_ratio_pct": r.cd_ratio_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in records
        ]
        written = db.upsert_rows("deposits_cd_ratio", db_rows)
        db.log_fetch("get_deposits_and_cd_ratio", "live", rows_written=written)
        return records

    except Exception as exc:
        logger.warning("Live deposits fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_deposits_and_cd_ratio", "cache_fallback", error_msg=str(exc))
        return load_deposits_from_cache(lookback_months)
