"""Market and real-time intelligence client for the Real Sector.

Mirrors the finance-sector market_client pattern, adapted to growth data:

1. Yahoo Finance chart API (httpx, no key) for growth-sensitive market
   context: Nifty 50, steel/cement/capital-goods bellwethers, USD/INR, crude.
2. Tavily AI Search (TVLY_KEY_2) for real-time GDP/GFCF/IIP releases and
   RBI growth commentary.
3. Free web search (DuckDuckGo HTML, no key, no package) as the third
   consolidation leg alongside Tavily and Yahoo.

Strict Provenance: market quotes carry ticker, date, and canonical URL;
news/search hits carry title, URL, and snippet. Missing data is reported
as unavailable, never estimated.
"""
from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from real_sector.config import real_settings

logger = logging.getLogger(__name__)

# Growth-sensitive market context (Yahoo Finance symbols, no key required).
GROWTH_PROXY_TICKERS: list[tuple[str, str, str]] = [
    ("^NSEI", "Nifty 50 Index (aggregate demand sentiment)", "Index points"),
    ("TATASTEEL.NS", "Tata Steel Ltd (steel capex proxy)", "INR"),
    ("ULTRACEMCO.NS", "UltraTech Cement Ltd (construction proxy)", "INR"),
    ("LT.NS", "Larsen & Toubro Ltd (capex order-book proxy)", "INR"),
    ("INR=X", "USD/INR Exchange Rate (external drag proxy)", "INR per USD"),
    ("CL=F", "WTI Crude Oil (input-cost proxy)", "USD per barrel"),
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
        return {
            "symbol": symbol,
            "name": name,
            "unit": unit,
            "current_price": current_price,
            "change_pct": change_pct,
            "observation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source_authority": "Yahoo Finance",
            "retrieval_url": f"https://finance.yahoo.com/quote/{symbol}",
            "freshness": "live" if current_price is not None else "unavailable",
        }
    except Exception as exc:
        logger.warning("yahoo proxy fetch failed for %s: %s", symbol, exc)
        return None


async def fetch_growth_market_proxies() -> dict[str, Any]:
    """Fetch growth-sensitive market proxies concurrently via Yahoo chart API."""
    if not real_settings.REAL_MARKET_ENABLED:
        return {"status": "disabled", "proxies": [], "total": 0}
    results = await asyncio.gather(
        *(_fetch_single_proxy(sym, name, unit) for sym, name, unit in GROWTH_PROXY_TICKERS),
        return_exceptions=True,
    )
    proxies = [r for r in results if isinstance(r, dict) and r is not None]
    live = [p for p in proxies if p.get("current_price") is not None]
    return {"status": "live" if live else "unavailable", "proxies": proxies, "total": len(proxies)}


def _get_tavily_key() -> str | None:
    return (
        getattr(real_settings, "TVLY_KEY_2", None)
        or os.getenv("TVLY_KEY_2")
        or os.getenv("TVLY_KEY_1")
        or os.getenv("TVLY_KEY_3")
    )


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(2),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def fetch_realtime_growth_news(
    query: str = "India GDP growth GFCF MoSPI release latest",
    max_results: int = 5,
) -> dict[str, Any]:
    """Fetch recent GDP/GFCF releases and RBI growth commentary via Tavily."""
    api_key = _get_tavily_key()
    if not api_key:
        logger.info("Tavily key not configured. Skipping growth news enrichment.")
        return {
            "status": "unavailable",
            "query": query,
            "news_items": [],
            "total_results": 0,
            "error_message": "TVLY_KEY_2 is not configured in environment.",
        }
    try:
        async with httpx.AsyncClient(timeout=real_settings.REAL_SEARCH_TIMEOUT) as client:
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
        logger.warning("Tavily growth search failed: %s", exc)
        return {
            "status": "unavailable",
            "query": query,
            "news_items": [],
            "total_results": 0,
            "error_message": str(exc),
        }


_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _parse_ddg_html(page: str, limit: int) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for match in _RESULT_RE.finditer(page):
        url, title, snippet = match.groups()
        title = html.unescape(_TAG_RE.sub("", title)).strip()[:250]
        snippet = html.unescape(_TAG_RE.sub("", snippet)).strip()[:800]
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http") or not title or not snippet:
            continue
        hits.append({"title": title, "url": url, "snippet": snippet, "source": "DuckDuckGo web search"})
        if len(hits) >= limit:
            break
    return hits


async def fetch_free_web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Free web search via DuckDuckGo HTML (no key, no extra package).

    Third consolidation leg alongside Tavily and Yahoo. Failures degrade to
    an unavailable status so the agent can still answer from official data.
    """
    if not real_settings.REAL_WEB_SEARCH_ENABLED:
        return {"status": "disabled", "query": query, "hits": [], "total_results": 0}
    try:
        async with httpx.AsyncClient(timeout=real_settings.REAL_SEARCH_TIMEOUT) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            resp.raise_for_status()
            hits = _parse_ddg_html(resp.text, max_results)
            _ = quote_plus(query)
            return {
                "status": "live" if hits else "unavailable",
                "query": query,
                "hits": hits,
                "total_results": len(hits),
            }
    except Exception as exc:
        logger.warning("Free web search failed: %s", exc)
        return {
            "status": "unavailable",
            "query": query,
            "hits": [],
            "total_results": 0,
            "error_message": f"{type(exc).__name__}: {exc}",
        }
