"""Tavily Client for Real-time Macroeconomic Web Intelligence."""
from __future__ import annotations

from datetime import datetime, timezone
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
from external_sector.models import Citation, DataFreshness, RealtimeIntelligenceRecord

logger = logging.getLogger(__name__)


def _make_retry():
    return retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


@_make_retry()
async def _execute_tavily_search(query: str, api_key: str, max_results: int = 4) -> dict[str, Any]:
    timeout = httpx.Timeout(
        15.0,
        connect=external_settings.HTTP_CONNECT_TIMEOUT,
        read=external_settings.HTTP_READ_TIMEOUT,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            external_settings.TAVILY_API_URL,
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": True,
            },
        )
        if response.is_error:
            response.raise_for_status()
        return response.json()


async def fetch_realtime_intelligence(
    query: str = "India foreign exchange reserves, trade deficit and rupee latest",
    max_results: int = 4,
) -> RealtimeIntelligenceRecord:
    """Fetch live web intelligence via Tavily search."""
    api_key = external_settings.TVLY_KEY_1
    if not api_key:
        raise ValueError("TVLY_KEY_1 is not configured in backend/.env.")

    now = datetime.now(timezone.utc)
    raw_data = await _execute_tavily_search(query=query, api_key=api_key, max_results=max_results)

    summary = str(raw_data.get("answer") or "Real-time external news retrieved.").strip()
    raw_results = raw_data.get("results", [])
    news_items: list[dict[str, Any]] = []
    source_urls: list[str] = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        url = item.get("url", "")
        content = item.get("content", "")
        if url:
            source_urls.append(url)
        news_items.append({
            "title": title,
            "url": url,
            "snippet": content[:300] if content else "",
            "score": item.get("score"),
        })

    citation = Citation(
        source_agent="external_sector",
        source_authority="Tavily AI Real-Time Search & News Intelligence",
        document_title=f"Live Web Intelligence: {query[:80]}",
        table_reference="tavily.web_search",
        retrieval_url=source_urls[0] if source_urls else "https://tavily.com",
        observation_period=now.strftime("%Y-%m-%d"),
        fetched_at=now,
        freshness=DataFreshness.LIVE,
    )

    return RealtimeIntelligenceRecord(
        query=query,
        summary=summary,
        news_items=news_items,
        source_urls=source_urls,
        fetched_at=now.isoformat(),
        citation=citation,
    )
