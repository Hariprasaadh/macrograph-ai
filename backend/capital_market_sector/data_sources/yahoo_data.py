"""Yahoo Finance chart data provider for Indian equity indices and volatility."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from capital_market_sector.config import capital_settings
from capital_market_sector.models import (
    Citation,
    DataFreshness,
    IndiaVixRecord,
    NiftySnapshotRecord,
    SectoralPerformanceRecord,
)

logger = logging.getLogger(__name__)


def _make_retry():
    return retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=capital_settings.HTTP_CONNECT_TIMEOUT, read=capital_settings.HTTP_READ_TIMEOUT),
        headers={"User-Agent": "macrograph-ai/capital-market-sector"},
        follow_redirects=True,
    )


@_make_retry()
async def fetch_yahoo_chart_payload(client: httpx.AsyncClient, symbol: str, range_value: str = "5d") -> tuple[dict[str, Any], str]:
    encoded_symbol = quote(symbol, safe="")
    url = f"{capital_settings.YAHOO_FINANCE_CHART_URL.rstrip('/')}/{encoded_symbol}"
    params = {"range": range_value, "interval": "1d"}
    retrieval_url = str(httpx.URL(url, params=params))
    response = await client.get(url, params=params, timeout=10.0)
    if response.is_error:
        response.raise_for_status()
    payload = response.json()
    return payload, retrieval_url


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def chart_data(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("Yahoo Finance returned a non-object chart response.")
    chart = payload.get("chart")
    if not isinstance(chart, dict):
        raise ValueError("Yahoo Finance response did not contain chart data.")
    if chart.get("error"):
        raise ValueError(f"Yahoo Finance chart error: {chart['error']}")
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("Yahoo Finance returned no chart observations.")

    result = results[0]
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    quotes = indicators.get("quote") if isinstance(indicators, dict) else None
    quote_data = quotes[0] if isinstance(quotes, list) and quotes else None
    if not isinstance(timestamps, list) or not isinstance(quote_data, dict):
        raise ValueError("Yahoo Finance chart response is missing timestamps or quote data.")

    meta = result.get("meta")
    if not isinstance(meta, dict):
        meta = {}

    series = {
        key: quote_data.get(key) if isinstance(quote_data.get(key), list) else []
        for key in ("open", "high", "low", "close", "volume")
    }
    return meta, [
        {
            "timestamp": timestamp,
            "open": series["open"][index] if index < len(series["open"]) else None,
            "high": series["high"][index] if index < len(series["high"]) else None,
            "low": series["low"][index] if index < len(series["low"]) else None,
            "close": series["close"][index] if index < len(series["close"]) else None,
            "volume": series["volume"][index] if index < len(series["volume"]) else None,
        }
        for index, timestamp in enumerate(timestamps)
        if isinstance(timestamp, (int, float))
    ]


def parse_market_chart(
    payload: Any,
    *,
    symbol: str,
    document_title: str,
    retrieval_url: str,
    is_vix: bool,
) -> list[NiftySnapshotRecord] | list[IndiaVixRecord]:
    meta, bars = chart_data(payload)
    bars.sort(key=lambda bar: bar["timestamp"])
    records: list[NiftySnapshotRecord] | list[IndiaVixRecord] = []
    previous_close = finite_number(meta.get("chartPreviousClose"))

    for bar in bars:
        close = finite_number(bar["close"])
        if close is None:
            continue
        observation_date = datetime.fromtimestamp(
            bar["timestamp"], timezone.utc
        ).astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
        prior_close = previous_close
        change_points = close - prior_close if prior_close is not None else None
        change_pct = (
            (change_points / prior_close) * 100
            if change_points is not None and prior_close
            else None
        )
        citation = Citation(
            source_authority="Yahoo Finance (aggregated market provider; not the NSE itself)",
            document_title=document_title,
            table_reference=f"Yahoo Finance chart symbol {symbol}",
            retrieval_url=retrieval_url,
            observation_period=observation_date,
            fetched_at=datetime.now(timezone.utc),
            freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        )

        if is_vix:
            regime = "Low" if close < 13.0 else ("Normal" if close <= 18.0 else ("Elevated" if close <= 24.0 else "High"))
            records.append(
                IndiaVixRecord(
                    period=observation_date,
                    vix_close=close,
                    vix_change_pct=change_pct,
                    volatility_regime=regime,
                    citation=citation,
                )
            )
        else:
            records.append(
                NiftySnapshotRecord(
                    period=observation_date,
                    index_name=meta.get("shortName") or meta.get("longName") or "NIFTY 50",
                    open_price=finite_number(bar["open"]),
                    high_price=finite_number(bar["high"]),
                    low_price=finite_number(bar["low"]),
                    close_price=close,
                    change_points=change_points,
                    change_pct=change_pct,
                    volume_shares=finite_number(bar["volume"]),
                    citation=citation,
                )
            )
        previous_close = close

    if not records:
        raise ValueError(f"Yahoo Finance returned no usable observations for {symbol}.")
    records.sort(key=lambda record: record.period, reverse=True)
    return records


async def fetch_sectoral_indices(client: httpx.AsyncClient) -> SectoralPerformanceRecord:
    symbols = {
        "nifty_50": "^NSEI",
        "bank": "^NSEBANK",
        "it": "^CNXIT",
        "auto": "^CNXAUTO",
        "pharma": "^CNXPHARMA",
        "fmcg": "^CNXFMCG",
    }
    changes: dict[str, float | None] = {}
    as_of_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

    for sector, sym in symbols.items():
        try:
            payload, _ = await fetch_yahoo_chart_payload(client, sym, "5d")
            meta, bars = chart_data(payload)
            if bars:
                latest = bars[-1]
                close = finite_number(latest["close"])
                prev = finite_number(meta.get("chartPreviousClose"))
                if close and prev:
                    changes[sector] = round(((close - prev) / prev) * 100, 2)
        except Exception as exc:
            logger.debug("Sector fetch skipped for %s (%s): %s", sector, sym, exc)
            changes[sector] = None

    valid = {k: v for k, v in changes.items() if k != "nifty_50" and v is not None}
    lead = max(valid, key=valid.get) if valid else None
    lag = min(valid, key=valid.get) if valid else None

    return SectoralPerformanceRecord(
        period=as_of_date,
        nifty_50_change_pct=changes.get("nifty_50"),
        nifty_bank_change_pct=changes.get("bank"),
        nifty_it_change_pct=changes.get("it"),
        nifty_auto_change_pct=changes.get("auto"),
        nifty_pharma_change_pct=changes.get("pharma"),
        nifty_fmcg_change_pct=changes.get("fmcg"),
        leading_sector=f"NIFTY {lead.upper()}" if lead else None,
        lagging_sector=f"NIFTY {lag.upper()}" if lag else None,
        citation=Citation(
            source_authority="NSE India / Yahoo Finance Provider",
            document_title="NSE Sectoral Indices Live Snapshot",
            table_reference="nse.sectoral_indices_snapshot",
            retrieval_url="https://query1.finance.yahoo.com/v8/finance/chart",
            observation_period=as_of_date,
            fetched_at=datetime.now(timezone.utc),
            freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        ),
    )
