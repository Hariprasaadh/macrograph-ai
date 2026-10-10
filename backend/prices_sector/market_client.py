"""Market and real-time intelligence client for the Prices sector.

Mirrors the finance sector's market_client pattern, adapted to inflation:

1. Yahoo Finance (yfinance) for inflation-sensitive market proxies that move
   consumer prices with a lead/lag: crude oil, gold, USD/INR, Nifty 50.
2. Tavily AI Search (TVLY_KEY_3) for real-time CPI/WPI releases and RBI
   inflation commentary.

Strict Provenance: every proxy quote carries source authority, ticker,
observation date, and canonical URL. Missing data is reported as
unavailable, never estimated.
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

from .config import prices_settings

logger = logging.getLogger(__name__)

# Inflation-sensitive market proxies (Yahoo Finance tickers, no key required).
PRICE_PROXY_TICKERS: list[tuple[str, str, str]] = [
    ("CL=F", "WTI Crude Oil (fuel pass-through proxy)", "USD per barrel"),
    ("GC=F", "Gold Spot (safe-haven / import-cost proxy)", "USD per troy ounce"),
    ("INR=X", "USD/INR Exchange Rate (imported-inflation proxy)", "INR per USD"),
    ("^NSEI", "Nifty 50 Index (demand-sentiment proxy)", "Index points"),
]


def _safe_float(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        f = float(val)
        return round(f, 4) if f == f and abs(f) != float("inf") else None
    except (ValueError, TypeError):
        return None


async def _fetch_single_proxy(symbol: str, name: str, unit: str) -> dict[str, Any] | None:
    """Fetch one Yahoo chart quote via the lightweight chart API (bounded timeout)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url, params={"interval": "1d", "range": "5d"})
            resp.raise_for_status()
            results = (resp.json().get("chart") or {}).get("result") or []
            if not results:
                return None
            meta = results[0].get("meta") or {}
            current_price = _safe_float(meta.get("regularMarketPrice"))
            prev_close = _safe_float(meta.get("chartPreviousClose") or meta.get("previousClose"))
            if current_price is None:
                closes = (((results[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
                closes = [c for c in closes if c is not None]
                current_price = _safe_float(closes[-1]) if closes else None
                prev_close = _safe_float(closes[-2]) if len(closes) > 1 else prev_close
        change_pct = None
        if current_price is not None and prev_close and prev_close > 0:
            change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)
        obs_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "symbol": symbol,
            "name": name,
            "unit": unit,
            "current_price": current_price,
            "change_pct": change_pct,
            "observation_date": obs_date,
            "source_authority": "Yahoo Finance",
            "retrieval_url": f"https://finance.yahoo.com/quote/{symbol}",
            "freshness": "live" if current_price is not None else "unavailable",
        }
    except Exception as exc:
        logger.warning("yahoo proxy fetch failed for %s: %s", symbol, exc)
        return None


async def fetch_inflation_market_proxies() -> dict[str, Any]:
    """Fetch inflation-sensitive market proxies concurrently via Yahoo chart API."""
    if not prices_settings.PRICES_MARKET_ENABLED:
        return {"status": "disabled", "proxies": [], "total": 0}
    results = await asyncio.gather(
        *(_fetch_single_proxy(sym, name, unit) for sym, name, unit in PRICE_PROXY_TICKERS),
        return_exceptions=True,
    )
    proxies = [r for r in results if isinstance(r, dict) and r is not None]
    live = [p for p in proxies if p.get("current_price") is not None]
    return {
        "status": "live" if live else "unavailable",
        "proxies": proxies,
        "total": len(proxies),
    }


def _get_tavily_key() -> str | None:
    key = prices_settings.TVLY_KEY_3.get_secret_value()
    if key:
        return key
    return os.getenv("TVLY_KEY_3") or os.getenv("TVLY_KEY_1")


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(2),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def fetch_realtime_prices_news(
    query: str = "India CPI inflation MoSPI release latest",
    max_results: int = 5,
) -> dict[str, Any]:
    """Fetch recent CPI/WPI releases and RBI inflation commentary via Tavily."""
    api_key = _get_tavily_key()
    if not api_key:
        logger.info("Tavily key not configured. Skipping inflation news enrichment.")
        return {
            "status": "unavailable",
            "query": query,
            "news_items": [],
            "total_results": 0,
            "error_message": "TVLY_KEY_3 is not configured in environment.",
        }
    try:
        async with httpx.AsyncClient(timeout=prices_settings.PRICES_SEARCH_TIMEOUT) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "topic": "finance",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("results", [])
            items = [
                {
                    "title": str(r.get("title", "")).strip()[:250],
                    "url": str(r.get("url", "")).strip(),
                    "snippet": str(r.get("content", "")).strip()[:800],
                    "published_date": r.get("published_date"),
                    "source": "Tavily AI Search",
                }
                for r in raw
                if isinstance(r, dict) and r.get("url") and r.get("content")
            ]
            return {
                "status": "live" if items else "unavailable",
                "query": query,
                "news_items": items,
                "total_results": len(items),
            }
    except Exception as exc:
        logger.warning("Tavily inflation search failed: %s", exc)
        return {
            "status": "unavailable",
            "query": query,
            "news_items": [],
            "total_results": 0,
            "error_message": str(exc),
        }
