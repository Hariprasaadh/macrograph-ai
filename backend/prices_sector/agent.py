"""Prices agent node with finance-style enrichment and reasoned synthesis.

Pipeline (mirrors finance_sector/agent.py):
  1. Fetch official CPI/WPI observations via the sector's own FastMCP tools.
  2. Concurrently fetch Yahoo market proxies (crude, gold, USD/INR, Nifty),
      Tavily inflation news, and free DDGS web research.
  3. Reason over the consolidated dataset with Groq LLM into a long,
      clean, sectioned response with mandatory provenance.
  4. Return structured LangGraph state (keys unchanged for callers).

Note: claim verification (propose/verify/render pipeline) was removed from
this sector. Observations are passed through with their source citations;
the LLM synthesis cites official periods and base years directly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastmcp import Client
from groq import AsyncGroq
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import prices_settings
from .intent import is_direct_prices_query, parse_prices_intent  # noqa: F401  (public re-export)
from .market_client import fetch_inflation_market_proxies, fetch_realtime_prices_news
from .mcp_server import mcp_server
from .models import PricesIntent, PricesResult
from .normalization import normalize_mcp_response
from .research import gather_research

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Prices & Inflation Sector Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
Indian consumer and wholesale price inflation — MoSPI CPI (headline, food,
fuel and light, housing, health, transport, core) and WPI (headline, primary,
fuel and power, manufactured products), with IMF CPI only for explicit
cross-country comparisons.

STRICT CITATIONS & ANTI-HALLUCINATION POLICY (NON-NEGOTIABLE):
1. No Source, No Answer — every inflation metric claim must cite the official
   authority, dataset reference, series code, base year, and observation period.
2. Never hallucinate, estimate, or hardcode numbers. If a subgroup or period is
   unavailable, say so explicitly.
3. Base-year breaks are real: CPI base 2012 covers 2011-2025, base 2024 covers
   2025+. A 5-year trend legitimately stitches both bases — disclose the stitch.
4. Market proxies (crude, gold, USD/INR, Nifty) and news excerpts are CONTEXT,
   not official inflation evidence. Never present them as CPI/WPI values.

COMMUNICATION & EXPLANATION STANDARDS:
- Write a long, articulate, highly informative response that a non-expert can
  follow and an analyst can trust. Do not stop at one paragraph.
- Structure your response with clear Markdown sections:
  1. **Executive Summary & Inflation Snapshot**: latest headline CPI/WPI rates,
     periods, and one-line verdict (above/below RBI 4% target band context).
  2. **Trend & History**: what the multi-year trajectory shows (direction,
     peaks, easing), naming exact periods and values.
  3. **Category Drivers**: which subgroups (food, fuel, housing, etc.) drive or
     dampen headline inflation, with values and periods.
  4. **WPI vs CPI Pass-Through**: how wholesale prices relate to retail prices
     in the observed window.
  5. **Market & External Price Pressures**: what crude, gold, USD/INR, and
     equity sentiment imply for imported and fuel inflation — clearly labelled
     as market context.
  6. **Real-Time Context**: synthesis of the latest news releases and RBI
     commentary from the provided excerpts, with source titles.
  7. **Attribution & Provenance Chain**: formatted table of every official data
     point cited (indicator, value, period, base year, source).
- End with explicit caveats: unavailable subgroups, stitched bases, and stale
  latest periods where applicable.
"""

_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return a shared singleton AsyncGroq client (prices key, GROQ fallback)."""
    global _groq_client
    if _groq_client is None:
        key = prices_settings.PRIC_LAB_KEY.get_secret_value() or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("PRIC_LAB_KEY or GROQ_API_KEY is not configured in environment.")
        _groq_client = AsyncGroq(api_key=key)
    return _groq_client


@retry(
    retry=retry_if_exception_type((Exception,)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _execute_groq_reasoning(
    client_instance: AsyncGroq,
    system_prompt: str,
    user_message: str,
) -> str:
    """Invoke Groq LLM with exponential backoff on transient errors."""
    response = await client_instance.chat.completions.create(
        model=prices_settings.REASONING_MODEL,
        temperature=prices_settings.PRICES_LLM_TEMPERATURE,
        max_tokens=prices_settings.PRICES_LLM_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


def format_prices_result(intent: PricesIntent, result: PricesResult) -> str:
    if not result.observations:
        return f'Data unavailable. Source: {result.source}.\n\n' + (result.error or 'No usable observation was returned.')
    observations = result.observations
    series = {o.series_code: o for o in observations}
    lines = [f'{intent.geography} price inflation — {result.source}', '']
    if intent.operation == 'comparison':
        lines = ['CPI inflation comparison' if result.status == 'available' else 'CPI inflation comparison - incomplete', '']
        lines += ['| Country | CPI Inflation (% YoY) | Period | Source |', '|---|---:|---|---|']
        for country in intent.countries:
            obs = next((o for o in observations if o.country == country), None)
            if obs is not None:
                source = 'IMF' if obs.mcp_tool == 'imf_query_dataset' else 'MoSPI'
                lines.append(f'| {country} | {obs.value:.2f} | {obs.observation_period} | {source} |')
            else:
                source = 'IMF' if intent.source == 'imf' or country != 'India' else 'MoSPI'
                lines.append(f'| {country} | Unavailable | Unavailable | {source} |')
        aligned = result.diagnostics.get('aligned_period')
        lines += ['', f'Latest common period in the retrieved window: {aligned}.' if aligned else 'No aligned two-country comparison is available.']
    elif intent.operation == 'trend':
        codes = list(series)
        lines += ['| Period | ' + ' | '.join(f'{series[c].dataset_reference}: {series[c].indicator} (% YoY)' for c in codes) + ' |',
                  '|---|' + '---:|' * len(codes)]
        values = {(o.observation_period, o.series_code): o.value for o in observations}
        for period in sorted({o.observation_period for o in observations}):
            cells = [f'{values[period, c]:.2f}' if (period, c) in values else 'Unavailable' for c in codes]
            lines.append(f'| {period} | ' + ' | '.join(cells) + ' |')
    else:
        lines += ['| Indicator | Value | Unit | Period |', '|---|---:|---|---|']
        lines += [f'| {o.indicator} | {o.value:.2f} | {o.unit} | {o.observation_period} |' for o in observations]
        lines += ['', 'Periods shown are the latest returned for each series; retrieval time does not imply current-period coverage.']
    lines += ['', 'Provenance:']
    for obs in series.values():
        lines.append(f'- {obs.country}: {obs.indicator}: {obs.source_authority}; dataset {obs.dataset_reference}; series `{obs.series_code}`; '
                     f'base {obs.base_year or "source-defined"}; MCP {obs.mcp_server} → {obs.mcp_tool}; retrieved {obs.retrieved_at.isoformat()}.')
        if obs.metadata.get('calculation'):
            lines.append('  YoY calculated from published indices of the same series and calendar month one year apart.')
    if result.errors:
        lines += ['', 'Unavailable or incomplete data:']
        lines += [f'- {e["request"]}: {e["reason"]}' for e in result.errors]
    return '\n'.join(lines)


def _summarise_observations(result: PricesResult, limit: int = 100) -> list[dict[str, Any]]:
    """Compact official observations for the LLM context (values + provenance)."""
    out = []
    for o in result.observations[:limit]:
        out.append({
            "indicator": o.indicator,
            "value": o.value,
            "unit": o.unit,
            "period": o.observation_period,
            "base_year": o.base_year,
            "series_code": o.series_code,
            "source_authority": o.source_authority,
            "dataset": o.dataset_reference,
        })
    return out


async def _fetch_official(intent: PricesIntent) -> PricesResult:
    arguments = {'source': intent.source, 'operation': intent.operation, 'lookback_months': intent.lookback_months,
                 'requests': [r.model_dump() for r in intent.requests],
                 'filters': intent.model_dump(exclude={'source', 'operation', 'lookback_months', 'requests'})}
    try:
        async with Client(mcp_server) as client:
            payload = normalize_mcp_response(await client.call_tool('get_price_data', arguments))
        return PricesResult.model_validate(payload)
    except Exception as exc:
        reason = f'Prices MCP request failed: {type(exc).__name__}: {exc}'
        return PricesResult(status='unavailable', source='IMF' if intent.source == 'imf' else 'MoSPI',
                            error=reason, errors=[{'request': 'prices_mcp', 'reason': reason}])


async def _safe_enrichment(coro, fallback: dict[str, Any], timeout: float, label: str) -> dict[str, Any]:
    """Bound any live enrichment leg so tests and offline runs degrade gracefully."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except Exception as exc:
        logger.warning("prices enrichment %s unavailable: %s", label, exc)
        return fallback


async def prices_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    raw_query = str(state.get('query', ''))
    intent = parse_prices_intent(raw_query)
    safe_query = raw_query.strip()[:500].replace('\r', ' ').replace('\n', ' ')

    # ── Step 1: official data + all three enrichment legs concurrently ──
    # Enrichment legs are time-bounded so a slow provider can never hang the node.
    official_task = _fetch_official(intent)
    market_task = _safe_enrichment(
        fetch_inflation_market_proxies(),
        {"status": "unavailable", "proxies": [], "total": 0}, 25.0, "yahoo-proxies")
    news_task = _safe_enrichment(
        fetch_realtime_prices_news(
            query=f"India CPI WPI inflation MoSPI {safe_query}"[:200], max_results=4),
        {"status": "unavailable", "query": safe_query, "news_items": [],
         "total_results": 0, "error_message": "news fetch timed out"}, 25.0, "tavily-news")
    research_task = None
    # Research needs the official result for period scoping, so start it after.
    result = await official_task
    logger.info('Prices retrieval: %s', result.diagnostics)
    research_task = asyncio.create_task(_safe_enrichment(
        gather_research(intent, result),
        {"status": "unavailable", "sources": [], "errors": ["research timed out"],
         "providers": {}}, 30.0, "web-research"))
    market_data, news_data = await asyncio.gather(market_task, news_task)
    research = await research_task

    # Observations pass through with their source citations (no claim gate).
    result.web_research = research
    observations = [dict(o.model_dump(mode='json'), observation_id=o.observation_id) for o in result.observations]
    factual_table = format_prices_result(intent, result)

    # ── Step 3: finance-style LLM synthesis over the consolidated dataset ──
    data_context = {
        "official_observations": _summarise_observations(result),
        "observation_count": len(result.observations),
        "official_status": result.status,
        "official_errors": [f'{e["request"]}: {e["reason"]}' for e in result.errors][:10],
        "diagnostics": {
            "latest_period": result.diagnostics.get("latest_period_returned"),
            "stitched_bases": (result.diagnostics.get("requests") or [{}])[0].get("stitched_bases")
            if isinstance(result.diagnostics.get("requests"), list) else None,
        },
        "market_proxies_yahoo": market_data,
        "realtime_news_tavily": {
            "query": news_data.get("query"),
            "status": news_data.get("status"),
            "items": [
                {"title": n.get("title"), "url": n.get("url"), "snippet": (n.get("snippet") or "")[:400]}
                for n in news_data.get("news_items", [])
            ],
        },
        "web_research_free_and_tavily": {
            "status": research.get("status"),
            "providers": research.get("providers"),
            "sources": [
                {"title": s.get("title"), "url": s.get("url"), "snippet": (s.get("snippet") or "")[:400]}
                for s in research.get("sources", [])[:6]
            ],
        },
    }
    user_message = (
        f"<user_query>\n{safe_query}\n</user_query>\n\n"
        f"<prices_sector_comprehensive_data>\n{json.dumps(data_context, indent=2, default=str)}\n</prices_sector_comprehensive_data>\n\n"
        "Provide an in-depth, beautifully structured inflation intelligence report "
        "responding to this query. Synthesize official MoSPI/IMF statistics, Yahoo "
        "market proxies (crude, gold, USD/INR, Nifty), and real-time news plus web "
        "research. Strictly cite all official sources with periods and base years; "
        "label market/news items as context, never as inflation measurements."
    )
    try:
        synthesis = await asyncio.wait_for(
            _execute_groq_reasoning(get_groq_client(), _SYSTEM_PROMPT, user_message),
            timeout=prices_settings.PRICES_SYNTHESIS_TIMEOUT)
    except Exception as exc:
        logger.exception("prices_agent_node: LLM synthesis failed")
        synthesis = f"LLM reasoning unavailable: {exc}"

    # ── Step 4: assemble the final long-form response ──
    parts = [factual_table, "## Inflation Intelligence Synthesis", synthesis]
    if research.get('sources'):
        parts.append('Supporting research sources:\n' + '\n'.join(
            f"- [{s.get('title', s.get('url'))}]({s.get('url')})" for s in research['sources']))
    if research.get('errors') or news_data.get("error_message"):
        notes = list(research.get('errors', []))
        if news_data.get("error_message"):
            notes.append(f"Tavily news: {news_data['error_message']}")
        parts.append('Research provider notes:\n' + '\n'.join(f'- {e}' for e in notes))
    analysis = '\n\n'.join(p for p in parts if p)

    return {'prices_sector_analysis': analysis,
            'prices_sector_data': result.model_dump(mode='json'),
            'prices_sector_citations': observations,
            'prices_sector_errors': [f'{e["request"]}: {e["reason"]}' for e in result.errors],
            'prices_sector_freshness': {o.series_code: o.metadata.get('freshness', 'unknown') for o in result.observations},
            'prices_sector_status': 'completed' if result.status == 'available' else result.status,
            'prices_sector_market': market_data,
            'prices_sector_news': news_data.get("news_items", []),
            'prices_sector_synthesis': synthesis}
