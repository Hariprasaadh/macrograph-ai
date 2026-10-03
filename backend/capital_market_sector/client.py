"""Async HTTP client for the Capital Markets Sector.

Retrieval strategy:
  1. Fetch the NSE market breadth through its verified MCP tool.
  2. Fetch tenor-labelled monthly SGL transaction yields from RBI DBIE.
  3. Use Yahoo Finance snapshots only for index/VIX fields not exposed by the
     configured NSE MCP tools.
  4. Persist observations and reuse recent DuckDB rows before upstream calls.

Yahoo Finance is an aggregated provider, not the NSE and not a real-time tick
feed. RBI G-Sec yields are monthly SGL transaction yields, not live benchmark
bond quotes.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from capital_market_sector import database as db
from capital_market_sector.config import capital_settings
from capital_market_sector.models import (
    Citation,
    DataFreshness,
    GSecYieldRecord,
    IndiaVixRecord,
    MarketBreadthRecord,
    MarketHistoryRecord,
    NiftySnapshotRecord,
)
from capital_market_sector.mcp_client import call_nse_tool
from capital_market_sector.parsers import parse_gsec_yields, parse_market_breadth

logger = logging.getLogger(__name__)

_MARKET_CACHE_TTL_SECONDS = 300
_SLOW_MARKET_CACHE_TTL_SECONDS = 21_600
_GSEC_YIELD_TABLE = (
    "financial_markets/"
    "r217_month_end_yield_of_sgl_transactions_in_government_dated_se"
)
_GSEC_YIELD_API_URL = (
    f"{capital_settings.RBI_DBIE_API_BASE.rstrip('/')}/{_GSEC_YIELD_TABLE}/rows"
)


class CapitalMarketDataUnavailableError(Exception):
    """Raised when neither live fetch nor cache can supply capital markets data."""


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
    response = await client.get(url, params=params, timeout=10.0)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=capital_settings.HTTP_CONNECT_TIMEOUT, read=capital_settings.HTTP_READ_TIMEOUT),
        headers={"User-Agent": "macrograph-ai/capital-market-sector"},
        follow_redirects=True,
    )


def _prepare_cached_citation(citation_data: Any) -> Citation:
    if isinstance(citation_data, str):
        citation_data = json.loads(citation_data)
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _chart_data(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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


def _snapshot_citation(
    symbol: str,
    period: str,
    document_title: str,
    retrieval_url: str,
) -> Citation:
    return Citation(
        source_authority="Yahoo Finance (aggregated market data; not the NSE itself)",
        document_title=document_title,
        table_reference=f"Yahoo Finance chart symbol {symbol}",
        retrieval_url=retrieval_url,
        observation_period=period,
        fetched_at=datetime.now(timezone.utc),
        freshness=DataFreshness.UPSTREAM_SNAPSHOT,
    )


def _parse_market_chart(
    payload: Any,
    *,
    symbol: str,
    document_title: str,
    retrieval_url: str,
    is_vix: bool,
) -> list[NiftySnapshotRecord] | list[IndiaVixRecord]:
    meta, bars = _chart_data(payload)
    bars.sort(key=lambda bar: bar["timestamp"])
    records: list[NiftySnapshotRecord] | list[IndiaVixRecord] = []
    previous_close = _finite_number(meta.get("chartPreviousClose"))

    for bar in bars:
        close = _finite_number(bar["close"])
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
        citation = _snapshot_citation(
            symbol, observation_date, document_title, retrieval_url
        )

        if is_vix:
            records.append(
                IndiaVixRecord(
                    period=observation_date,
                    vix_close=close,
                    vix_change_pct=change_pct,
                    volatility_regime=None,
                    citation=citation,
                )
            )
        else:
            records.append(
                NiftySnapshotRecord(
                    period=observation_date,
                    index_name=meta.get("shortName") or meta.get("longName") or "NIFTY 50",
                    open_price=_finite_number(bar["open"]),
                    high_price=_finite_number(bar["high"]),
                    low_price=_finite_number(bar["low"]),
                    close_price=close,
                    change_points=change_points,
                    change_pct=change_pct,
                    volume_shares=_finite_number(bar["volume"]),
                    citation=citation,
                )
            )
        previous_close = close

    if not records:
        raise ValueError(f"Yahoo Finance returned no usable observations for {symbol}.")
    records.sort(key=lambda record: record.period, reverse=True)
    return records


def _save_live_records(table: str, records: list[Any], tool_name: str) -> None:
    fetched_at = datetime.now(timezone.utc)
    rows = [
        {
            **record.model_dump(mode="json", exclude={"citation"}),
            "citation": record.citation.model_dump_json(),
            "fetched_at": (fetched_at - timedelta(milliseconds=index)).isoformat(),
        }
        for index, record in enumerate(records)
    ]
    written = db.upsert_rows(table, rows)
    db.log_fetch(tool_name, "upstream_snapshot", rows_written=written)


def _is_seed_observation(row: dict[str, Any]) -> bool:
    citation = row.get("citation")
    if isinstance(citation, str):
        try:
            citation = json.loads(citation)
        except json.JSONDecodeError:
            return False
    return isinstance(citation, dict) and citation.get("table_reference") in {
        "capital_market_sector.nifty_50_bhavcopy",
        "capital_market_sector.india_vix",
        "capital_market_sector.gsec_yields",
        "financial_sector.r531_gsec_yields",
        "capital_market_sector.market_breadth",
    }


def _rows_are_recent(rows: list[dict[str, Any]], max_age_seconds: int) -> bool:
    if not rows:
        return False
    fetched_at = rows[0].get("fetched_at")
    if isinstance(fetched_at, str):
        try:
            fetched_at = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(fetched_at, datetime):
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched_at).total_seconds() <= max_age_seconds


def _query_non_seed_rows(table: str, limit: int) -> list[dict[str, Any]]:
    return [
        row for row in db.query_latest_rows(table, limit=limit)
        if not _is_seed_observation(row)
    ]


def _nifty_records_from_rows(rows: list[dict[str, Any]]) -> list[NiftySnapshotRecord]:
    return [
        NiftySnapshotRecord(
            period=row["period"],
            index_name=row.get("index_name", "NIFTY 50"),
            open_price=row.get("open_price"),
            high_price=row.get("high_price"),
            low_price=row.get("low_price"),
            close_price=row.get("close_price"),
            change_points=row.get("change_points"),
            change_pct=row.get("change_pct"),
            volume_shares=row.get("volume_shares"),
            turnover_cr=row.get("turnover_cr"),
            citation=_prepare_cached_citation(row.get("citation", {})),
        )
        for row in rows
    ]


async def _fetch_yahoo_chart(
    *,
    symbol: str,
    range_value: str,
    document_title: str,
    table: str,
    tool_name: str,
    is_vix: bool,
) -> list[Any]:
    encoded_symbol = quote(symbol, safe="")
    url = f"{capital_settings.YAHOO_FINANCE_CHART_URL.rstrip('/')}/{encoded_symbol}"
    params = {"range": range_value, "interval": "1d"}
    retrieval_url = str(httpx.URL(url, params=params))
    try:
        async with _build_client() as client:
            payload = await _fetch_json(client, url, params)
        records = _parse_market_chart(
            payload,
            symbol=symbol,
            document_title=document_title,
            retrieval_url=retrieval_url,
            is_vix=is_vix,
        )
        _save_live_records(table, records, tool_name)
        return records
    except Exception as exc:
        logger.warning("%s provider fetch failed: %s. Falling back to cache.", tool_name, exc)
        try:
            db.log_fetch(tool_name, "cache_fallback", error_msg=str(exc))
        except Exception as log_error:
            logger.warning("Could not record %s cache fallback: %s", tool_name, log_error)
        raise


# ── Tool 1: NIFTY Snapshot ────────────────────────────────────────────────

async def fetch_nifty_snapshot() -> list[NiftySnapshotRecord]:
    db.initialise_schema()
    recent_rows = _query_non_seed_rows("nifty_snapshot", limit=5)
    if _rows_are_recent(recent_rows, _MARKET_CACHE_TTL_SECONDS):
        return _nifty_records_from_rows(recent_rows)
    try:
        return await _fetch_yahoo_chart(
            symbol="^NSEI",
            range_value="5d",
            document_title="NIFTY 50 daily chart (Yahoo Finance provider snapshot)",
            table="nifty_snapshot",
            tool_name="yahoo_nifty_chart",
            is_vix=False,
        )
    except Exception as exc:
        try:
            return _load_nifty_from_cache()
        except CapitalMarketDataUnavailableError as cache_error:
            raise cache_error from exc


def _load_nifty_from_cache() -> list[NiftySnapshotRecord]:
    rows = _query_non_seed_rows("nifty_snapshot", limit=5)
    if not rows:
        raise CapitalMarketDataUnavailableError("NIFTY snapshot data unavailable.")
    return _nifty_records_from_rows(rows)


# ── Tool 2: Market History ────────────────────────────────────────────────

async def fetch_market_history(lookback_months: int = 12) -> list[MarketHistoryRecord]:
    db.initialise_schema()
    rows = db.query_latest_rows("market_history", lookback_months)
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            MarketHistoryRecord(
                period=row["period"],
                index_name=row.get("index_name", "NIFTY 50"),
                close_price=row.get("close_price"),
                yoy_return_pct=row.get("yoy_return_pct"),
                pe_ratio=row.get("pe_ratio"),
                pb_ratio=row.get("pb_ratio"),
                dividend_yield_pct=row.get("dividend_yield_pct"),
                citation=citation,
            )
        )
    return records


# ── Tool 3: India VIX ─────────────────────────────────────────────────────

async def fetch_india_vix(lookback_days: int = 30) -> list[IndiaVixRecord]:
    db.initialise_schema()
    recent_rows = _query_non_seed_rows("india_vix", limit=lookback_days)
    if _rows_are_recent(recent_rows, _MARKET_CACHE_TTL_SECONDS):
        return [
            IndiaVixRecord(
                period=row["period"],
                vix_close=row.get("vix_close"),
                vix_change_pct=row.get("vix_change_pct"),
                volatility_regime=row.get("volatility_regime"),
                citation=_prepare_cached_citation(row.get("citation", {})),
            )
            for row in recent_rows
        ]
    range_value = "1mo" if lookback_days <= 31 else "3mo"
    try:
        return await _fetch_yahoo_chart(
            symbol="^INDIAVIX",
            range_value=range_value,
            document_title="India VIX daily chart (Yahoo Finance provider snapshot)",
            table="india_vix",
            tool_name="yahoo_india_vix_chart",
            is_vix=True,
        )
    except Exception as exc:
        try:
            rows = [
                row for row in db.query_latest_rows("india_vix", lookback_days)
                if not _is_seed_observation(row)
            ]
            if not rows:
                raise CapitalMarketDataUnavailableError("India VIX data unavailable.")
            return [
                IndiaVixRecord(
                    period=row["period"],
                    vix_close=row.get("vix_close"),
                    vix_change_pct=row.get("vix_change_pct"),
                    volatility_regime=row.get("volatility_regime"),
                    citation=_prepare_cached_citation(row.get("citation", {})),
                )
                for row in rows
            ]
        except CapitalMarketDataUnavailableError as cache_error:
            raise cache_error from exc


# ── Tool 4: Market Breadth ────────────────────────────────────────────────

async def fetch_market_breadth() -> list[MarketBreadthRecord]:
    db.initialise_schema()
    rows = _query_non_seed_rows("market_breadth", limit=5)
    if _rows_are_recent(rows, _MARKET_CACHE_TTL_SECONDS):
        return _market_breadth_records_from_rows(rows)
    as_of_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    try:
        payload = await call_nse_tool(
            capital_settings.NSE_BHAVCOPY_MCP,
            "get_market_breadth",
            {"date": as_of_date},
        )
        citation = Citation(
            source_authority="National Stock Exchange of India (NSE)",
            document_title="NSE Market Breadth Summary",
            table_reference="NSE Bhavcopy MCP tool: get_market_breadth",
            retrieval_url=capital_settings.NSE_BHAVCOPY_MCP,
            observation_period=str(payload.get("date") or as_of_date),
            fetched_at=datetime.now(timezone.utc),
            freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        )
        record = parse_market_breadth(payload, citation)
        _save_live_records("market_breadth", [record], "nse_mcp_market_breadth")
        return [record]
    except Exception as exc:
        logger.warning("NSE MCP market breadth fetch failed: %s. Falling back to cache.", exc)
        try:
            db.log_fetch("nse_mcp_market_breadth", "cache_fallback", error_msg=str(exc))
        except Exception as log_error:
            logger.warning("Could not record market breadth cache fallback: %s", log_error)
        if not rows:
            rows = _query_non_seed_rows("market_breadth", limit=5)
        return _market_breadth_records_from_rows(rows)


def _market_breadth_records_from_rows(
    rows: list[dict[str, Any]],
) -> list[MarketBreadthRecord]:
    records = []
    for row in rows:
        citation = _prepare_cached_citation(row.get("citation", {}))
        records.append(
            MarketBreadthRecord(
                period=row["period"],
                total_stocks=row.get("total_stocks"),
                advances_count=row.get("advances_count"),
                declines_count=row.get("declines_count"),
                unchanged_count=row.get("unchanged_count"),
                advance_decline_ratio=row.get("advance_decline_ratio"),
                total_volume=row.get("total_volume"),
                citation=citation,
            )
        )
    if not records:
        raise CapitalMarketDataUnavailableError("NSE market breadth data unavailable.")
    return records


# ── Tool 5: G-Sec Yield Snapshot ──────────────────────────────────────────

async def fetch_gsec_yield_snapshot() -> list[GSecYieldRecord]:
    db.initialise_schema()
    rows = _query_non_seed_rows("gsec_yields", limit=24)
    if _rows_are_recent(rows, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return _gsec_records_from_rows(rows)
    try:
        async with _build_client() as client:
            payload = await _fetch_json(
                client,
                _GSEC_YIELD_API_URL,
                params={"limit": 2000, "offset": 0},
            )

        def citation_for(period: str) -> Citation:
            return Citation(
                source_authority="Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
                document_title=(
                    "Month-end Yield of SGL Transactions in Government Dated Securities "
                    "for Various Maturities"
                ),
                table_reference=f"financial_markets.{_GSEC_YIELD_TABLE.split('/')[-1]}",
                retrieval_url=_GSEC_YIELD_API_URL,
                observation_period=period,
                fetched_at=datetime.now(timezone.utc),
                freshness=DataFreshness.UPSTREAM_SNAPSHOT,
            )

        records = parse_gsec_yields(
            payload,
            lookback_months=24,
            citation_factory=citation_for,
        )
        if not records:
            raise ValueError("RBI DBIE returned no usable tenor-labelled G-Sec yields.")
        _save_live_records("gsec_yields", records, "rbi_dbie_monthly_gsec_yields")
        return records
    except Exception as exc:
        logger.warning("RBI DBIE G-Sec yield fetch failed: %s. Falling back to cache.", exc)
        try:
            db.log_fetch("rbi_dbie_monthly_gsec_yields", "cache_fallback", error_msg=str(exc))
        except Exception as log_error:
            logger.warning("Could not record G-Sec yield cache fallback: %s", log_error)
        if not rows:
            rows = _query_non_seed_rows("gsec_yields", limit=24)
        return _gsec_records_from_rows(rows)


def _gsec_records_from_rows(rows: list[dict[str, Any]]) -> list[GSecYieldRecord]:
    records = [
        GSecYieldRecord(
            period=row["period"],
            ten_year_gsec_yield_pct=row.get("ten_year_gsec_yield_pct"),
            five_year_gsec_yield_pct=row.get("five_year_gsec_yield_pct"),
            two_year_gsec_yield_pct=row.get("two_year_gsec_yield_pct"),
            yield_curve_spread_2s10s_bps=row.get("yield_curve_spread_2s10s_bps"),
            citation=_prepare_cached_citation(row.get("citation", {})),
        )
        for row in rows
    ]
    if not records:
        raise CapitalMarketDataUnavailableError(
            "G-Sec yield data unavailable: RBI DBIE fetch failed and cache is empty."
        )
    return records
