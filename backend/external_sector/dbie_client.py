"""RBI DBIE HTTP Client for High-Frequency External Datasets."""
from __future__ import annotations

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

_CDN = external_settings.DBIE_CDN_BASE
FOREX_CDN_URL = f"{_CDN}/forex-reserves.json"
_API = external_settings.DBIE_API_BASE
TRADE_BALANCE_API_URL = f"{_API}/external_sector/r433_india_s_foreign_trade_us_dollars/rows"
EXCHANGE_RATE_API_URL = f"{_API}/external_sector/r575_exchange_rate/rows"


def _make_retry():
    return retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            float(external_settings.DBIE_TIMEOUT),
            connect=external_settings.HTTP_CONNECT_TIMEOUT,
            read=external_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/external-sector"},
        follow_redirects=True,
    )


@_make_retry()
async def fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    response = await client.get(url, params=params, timeout=external_settings.DBIE_TIMEOUT)
    if response.is_error:
        response.raise_for_status()
    return response.json()


async def fetch_raw_forex() -> Any:
    """Fetch raw weekly forex reserves from DBIE CDN."""
    async with build_client() as client:
        return await fetch_json(client, FOREX_CDN_URL)


async def fetch_raw_trade(limit: int) -> Any:
    """Fetch raw monthly merchandise trade rows from DBIE API."""
    async with build_client() as client:
        return await fetch_json(client, TRADE_BALANCE_API_URL, params={"limit": limit, "offset": 0})


async def fetch_raw_exchange_rates(limit: int) -> Any:
    """Fetch raw daily exchange rate rows from DBIE API."""
    async with build_client() as client:
        return await fetch_json(client, EXCHANGE_RATE_API_URL, params={"limit": limit, "offset": 0})
