"""Market data and real-time intelligence client for the Monetary Sector.

Integrates:
  1. Tavily AI Search (TVLY_KEY_1) for real-time RBI MPC statements, governor speeches,
     liquidity operations, and forward guidance.
  2. Benchmark Indian Government Securities (G-Sec) & money-market indicators
     to assess monetary policy transmission into market yields.

Strict Provenance:
  Every observation includes a Citation model detailing source authority,
  retrieval timestamp, and official table reference / canonical URL.
"""
from __future__ import annotations

import logging
import os

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from monetary_sector.config import monetary_settings
from monetary_sector.models import (
    Citation,
    DataFreshness,
    MonetaryMarketMetric,
    MonetaryMarketResponse,
    MonetaryNewsResponse,
    TavilyNewsItem,
)

logger = logging.getLogger(__name__)


def _get_tavily_key() -> str | None:
    return (
        monetary_settings.TVLY_KEY_1
        or monetary_settings.TAVILY_API_KEY
        or os.getenv("TVLY_KEY_1")
        or os.getenv("TAVILY_API_KEY")
    )


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(2),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def fetch_realtime_monetary_news(
    query: str = "RBI monetary policy repo rate MPC liquidity inflation stance India",
    max_results: int = 5,
) -> MonetaryNewsResponse:
    """Fetch recent RBI MPC decisions, monetary policy statements & stance via Tavily AI Search."""
    api_key = _get_tavily_key()
    if not api_key:
        logger.info("Tavily API key not configured for monetary sector. Skipping search enrichment.")
        return MonetaryNewsResponse(
            status=DataFreshness.UNAVAILABLE,
            query=query,
            news_items=[],
            total_results=0,
            error_message="TVLY_KEY_1 is not configured in environment.",
        )

    tavily_url = "https://api.tavily.com/search"
    enhanced_query = f"RBI monetary policy MPC repo rate liquidity inflation stance India {query}".strip()[:240]
    payload = {
        "api_key": api_key,
        "query": enhanced_query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(tavily_url, json=payload)
            if resp.status_code != 200:
                logger.warning("Tavily monetary search returned status %s: %s", resp.status_code, resp.text[:200])
                return MonetaryNewsResponse(
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
                title = str(r.get("title", "")).strip()
                url = str(r.get("url", "")).strip()
                content = str(r.get("content", "")).strip()[:800]
                if not title or not url:
                    continue
                items.append(
                    TavilyNewsItem(
                        title=title,
                        url=url,
                        content=content,
                        published_date=r.get("published_date"),
                        source="Tavily AI Search",
                        score=r.get("score"),
                    )
                )

            return MonetaryNewsResponse(
                status=DataFreshness.LIVE if items else DataFreshness.UNAVAILABLE,
                query=query,
                news_items=items,
                total_results=len(items),
            )
    except Exception as exc:
        logger.warning("Tavily search failed for monetary sector: %s", exc)
        return MonetaryNewsResponse(
            status=DataFreshness.UNAVAILABLE,
            query=query,
            news_items=[],
            total_results=0,
            error_message=str(exc),
        )


async def fetch_monetary_market_indicators(repo_rate: float | None = None) -> MonetaryMarketResponse:
    """Fetch the published RBI sovereign G-Sec yield and derive the policy spread.

    Every value comes from the RBI DBIE month-end SGL yield table; nothing is
    assumed. When no observation can be retrieved the response is UNAVAILABLE.
    """
    latest = None
    try:
        from capital_market_sector.client import fetch_gsec_yield_snapshot

        for record in await fetch_gsec_yield_snapshot():
            if getattr(record, "ten_year_gsec_yield_pct", None) is not None:
                latest = record
                break
    except Exception as exc:
        logger.warning("Sovereign G-Sec yield lookup failed for monetary sector: %s", exc)

    if latest is None:
        return MonetaryMarketResponse(
            status=DataFreshness.UNAVAILABLE,
            gsec_10y_yield_pct=None,
            overnight_wacr_pct=None,
            policy_spread_bps=None,
            metrics=[],
            total_records=0,
        )

    citation_payload = latest.citation.model_dump(mode="json")
    citation_payload["source_agent"] = "monetary_sector"
    citation = Citation.model_validate(citation_payload)

    yield_pct = latest.ten_year_gsec_yield_pct
    spread_bps = (
        round((yield_pct - repo_rate) * 100, 1)
        if repo_rate is not None and yield_pct is not None
        else None
    )

    metric = MonetaryMarketMetric(
        symbol="IN10Y_GSEC",
        name="10-Year Government Security (RBI month-end SGL transaction yield)",
        current_yield_pct=yield_pct,
        change_bps=None,
        spread_over_repo_bps=spread_bps,
        observation_date=latest.period,
        citation=citation,
    )

    return MonetaryMarketResponse(
        status=citation.freshness,
        gsec_10y_yield_pct=yield_pct,
        overnight_wacr_pct=None,
        policy_spread_bps=spread_bps,
        metrics=[metric],
        total_records=1,
    )

