"""Bounded Tavily and free DDGS research, separate from official observations."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .config import prices_settings
from .models import PricesIntent, PricesResult


def safe_url(value: str) -> str | None:
    try:
        parts = urlsplit(value)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query)
                           if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')])
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, query, ''))
    except ValueError:
        return None


async def search_tavily(query: str) -> list[dict]:
    key = prices_settings.TVLY_KEY_3.get_secret_value()
    if not key:
        raise RuntimeError('Tavily key is not configured')
    async with httpx.AsyncClient(timeout=prices_settings.PRICES_SEARCH_TIMEOUT) as client:
        response = await client.post('https://api.tavily.com/search',
            headers={'Authorization': f'Bearer {key}'}, json={
                'query': query, 'search_depth': 'basic', 'topic': 'general',
                'max_results': prices_settings.PRICES_SEARCH_MAX_RESULTS,
                'include_answer': False, 'include_raw_content': False})
        response.raise_for_status()
        rows = response.json().get('results', [])
        if not isinstance(rows, list):
            raise ValueError('Invalid search results')
        return rows


async def search_ddgs(query: str) -> list[dict]:
    def search():
        from ddgs import DDGS
        return list(DDGS(timeout=prices_settings.PRICES_SEARCH_TIMEOUT).text(
            query, max_results=prices_settings.PRICES_SEARCH_MAX_RESULTS, backend='auto'))
    return await asyncio.to_thread(search)


async def gather_research(intent: PricesIntent, result: PricesResult) -> dict:
    if not prices_settings.PRICES_WEB_SEARCH_ENABLED or intent.errors:
        return {'status': 'disabled', 'sources': [], 'errors': [], 'providers': {}}
    # Use parsed economic scope, never forward arbitrary chat text or credentials.
    subjects = ' '.join(dict.fromkeys(f'{r.indicator.upper()} {r.category}' for r in intent.requests))
    countries = ' '.join(intent.countries) or intent.geography
    periods = sorted({o.observation_period for o in result.observations})
    period = ' to '.join([periods[0], periods[-1]]) if len(periods) > 1 else (
        periods[0] if periods else intent.end_period or datetime.now(timezone.utc).strftime('%Y-%m'))
    query = f'{countries} {subjects} inflation {period} official release drivers explanation'

    async def run(provider, search):
        try:
            rows = await asyncio.wait_for(search(query), timeout=prices_settings.PRICES_SEARCH_TIMEOUT + 1)
            return provider, rows, None
        except Exception as exc:
            # Provider exceptions may contain request headers or key-bearing URLs.
            return provider, [], f'{provider} search unavailable ({type(exc).__name__}).'

    results = await asyncio.gather(run('tavily', search_tavily), run('ddgs', search_ddgs))
    sources, errors, providers = {}, [], {}
    retrieved = datetime.now(timezone.utc).isoformat()
    for provider, rows, error in results:
        accepted = 0
        for row in rows[:prices_settings.PRICES_SEARCH_MAX_RESULTS]:
            if not isinstance(row, dict):
                continue
            url = safe_url(str(row.get('url') or row.get('href') or ''))
            snippet = str(row.get('content') or row.get('body') or '').strip()
            if not url or not snippet:
                continue
            # Some engines silently broaden a query to geography alone.
            subject_text = f"{row.get('title', '')} {snippet} {url}"
            if not re.search(r'\b(?:cpi|wpi|inflation|consumer price|wholesale price)\b', subject_text, re.I):
                continue
            accepted += 1
            if url in sources:
                sources[url]['providers'].append(provider)
                continue
            sources[url] = {'title': str(row.get('title') or url)[:250], 'url': url,
                'snippet': snippet[:1800], 'published_at': row.get('published_date'),
                'retrieved_at': retrieved, 'providers': [provider], 'evidence_type': 'search_excerpt'}
        if not accepted and error is None:
            error = f'{provider} returned no usable search results.'
        providers[provider] = {'status': 'unavailable' if error else 'available', 'results': accepted}
        if error:
            errors.append(error)
    return {'status': 'partial' if sources and errors else 'available' if sources else 'unavailable',
            'query': query, 'sources': list(sources.values()), 'providers': providers, 'errors': errors}
