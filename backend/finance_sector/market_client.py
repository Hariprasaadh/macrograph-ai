"""Market data and real-time intelligence client for the Finance Sector.

Integrates:
  1. Yahoo Finance (yfinance) for Indian banking equities and NIFTY Bank index.
  2. Tavily AI Search (TVLY_KEY_1) for real-time RBI announcements and banking news.

Strict Provenance:
  Every observation includes a Citation model detailing source authority,
  retrieval timestamp, and official ticker / canonical URL.
"""
from __future__ import annotations

import asyncio
import logging
import os
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

from finance_sector.config import finance_settings
from finance_sector.models import (
    BankEquityMetric,
    BankingMarketResponse,
    Citation,
    DataFreshness,
    FinanceNewsResponse,
    TavilyNewsItem,
)

logger = logging.getLogger(__name__)

_BANKING_TICKERS = [
    ("SBIN.NS", "State Bank of India (PSB Benchmark)"),
    ("HDFCBANK.NS", "HDFC Bank Ltd (Private Sector Benchmark)"),
    ("ICICIBANK.NS", "ICICI Bank Ltd"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank Ltd"),
    ("AXISBANK.NS", "Axis Bank Ltd"),
]

_BENCHMARK_TICKER = ("^NSEBANK", "Nifty Bank Index")


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return round(f, 4) if not (f != f) else None  # check nan
    except (ValueError, TypeError):
        return None


def _fetch_single_ticker_sync(symbol: str, name: str) -> BankEquityMetric | None:
    """Synchronous worker to fetch one ticker via yfinance (runs in thread pool)."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = getattr(ticker, "fast_info", None)

        current_price = _safe_float(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or (getattr(fast_info, "last_price", None) if fast_info else None)
        )
        prev_close = _safe_float(
            info.get("previousClose")
            or info.get("regularMarketPreviousClose")
            or (getattr(fast_info, "previous_close", None) if fast_info else None)
        )

        change_pct = None
        if current_price is not None and prev_close and prev_close > 0:
            change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        raw_mcap = info.get("marketCap") or (getattr(fast_info, "market_cap", None) if fast_info else None)
        mcap_cr = round(float(raw_mcap) / 10000000.0, 2) if raw_mcap else None

        pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
        pb = _safe_float(info.get("priceToBook"))

        h52 = _safe_float(info.get("fiftyTwoWeekHigh") or (getattr(fast_info, "year_high", None) if fast_info else None))
        l52 = _safe_float(info.get("fiftyTwoWeekLow") or (getattr(fast_info, "year_low", None) if fast_info else None))

        obs_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        citation = Citation(
            source_agent="finance_sector",
            source_authority="National Stock Exchange of India (NSE) via Yahoo Finance",
            document_title=f"Market Quote & Financial Ratios: {name} ({symbol})",
            table_reference=f"yfinance:{symbol}",
            retrieval_url=f"https://finance.yahoo.com/quote/{symbol}",
            observation_period=obs_date,
            freshness=DataFreshness.LIVE,
        )

        return BankEquityMetric(
            symbol=symbol,
            name=name,
            current_price=current_price,
            change_pct=change_pct,
            pe_ratio=pe,
            pb_ratio=pb,
            market_cap_cr=mcap_cr,
            high_52w=h52,
            low_52w=l52,
            citation=citation,
        )
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", symbol, exc)
        return None


async def fetch_banking_market_indicators() -> BankingMarketResponse:
    """Fetch live market data for Nifty Bank and key commercial banks using yfinance."""
    loop = asyncio.get_running_loop()

    # Fetch benchmark index
    benchmark_metric = await loop.run_in_executor(
        None, _fetch_single_ticker_sync, _BENCHMARK_TICKER[0], _BENCHMARK_TICKER[1]
    )

    # Fetch top banks concurrently in worker threads
    tasks = [
        loop.run_in_executor(None, _fetch_single_ticker_sync, sym, name)
        for sym, name in _BANKING_TICKERS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    top_banks: list[BankEquityMetric] = [
        r for r in results if isinstance(r, BankEquityMetric) and r is not None
    ]

    status = DataFreshness.LIVE if (benchmark_metric or top_banks) else DataFreshness.UNAVAILABLE
    total = len(top_banks) + (1 if benchmark_metric else 0)

    return BankingMarketResponse(
        status=status,
        benchmark_index=benchmark_metric,
        top_banks=top_banks,
        total_records=total,
    )


# ── Tavily Real-Time Search Client ──────────────────────────────────────────

def _get_tavily_key() -> str | None:
    return (
        finance_settings.TVLY_KEY_1
        or os.getenv("TVLY_KEY_1")
    )


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(2),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def fetch_realtime_finance_news(
    query: str = "RBI monetary policy commercial bank credit growth India",
    max_results: int = 5,
) -> FinanceNewsResponse:
    """Fetch recent banking & financial developments via Tavily AI Search."""
    api_key = _get_tavily_key()
    if not api_key:
        logger.info("Tavily API key not configured. Skipping real-time search enrichment.")
        return FinanceNewsResponse(
            status=DataFreshness.UNAVAILABLE,
            query=query,
            news_items=[],
            total_results=0,
            error_message="TVLY_KEY_1 is not configured in environment.",
        )

    tavily_url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(tavily_url, json=payload)
            if resp.status_code != 200:
                logger.warning("Tavily search returned status %s: %s", resp.status_code, resp.text[:200])
                return FinanceNewsResponse(
                    status=DataFreshness.UNAVAILABLE,
                    query=query,
                    news_items=[],
                    total_results=0,
                    error_message=f"Tavily HTTP {resp.status_code}",
                )

            data = resp.json()
            raw_results = data.get("results", [])
            items: list[TavilyNewsItem] = []
            for r in raw_results:
                items.append(
                    TavilyNewsItem(
                        title=str(r.get("title", "")).strip(),
                        url=str(r.get("url", "")).strip(),
                        content=str(r.get("content", "")).strip()[:800],
                        published_date=r.get("published_date"),
                        source="Tavily AI Search",
                    )
                )

            return FinanceNewsResponse(
                status=DataFreshness.LIVE,
                query=query,
                news_items=items,
                total_results=len(items),
            )
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return FinanceNewsResponse(
            status=DataFreshness.UNAVAILABLE,
            query=query,
            news_items=[],
            total_results=0,
            error_message=str(exc),
        )
