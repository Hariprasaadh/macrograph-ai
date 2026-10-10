"""Search-provider isolation and teaching-response regressions (no network)."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import SecretStr

from prices_sector import research
from prices_sector.config import prices_settings, PricesSettings
from prices_sector.intent import parse_prices_intent, is_direct_prices_query
from prices_sector.models import PriceObservation, PricesResult


@pytest.fixture
def result():
    return PricesResult(status='available', source='MoSPI', observations=[PriceObservation(
        source_authority='MoSPI', dataset_reference='WPI', indicator_id='test', indicator='Wholesale price index',
        series_code='WPI:TEST', request_id='wpi:headline:combined', observation_period='2026-08',
        base_year='TEST', value=5, unit='% YoY', url='https://mcp.mospi.gov.in/',
        mcp_server='https://mcp.mospi.gov.in/', mcp_tool='get_data', retrieved_at=datetime.now(timezone.utc))])


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(prices_settings, 'PRICES_WEB_SEARCH_ENABLED', True)


def test_key_loaded_from_env_file_without_disclosure(tmp_path):
    env = tmp_path / '.env'
    env.write_text('TVLY_KEY_3=synthetic-secret\n')
    settings = PricesSettings(_env_file=env)
    assert settings.TVLY_KEY_3.get_secret_value() == 'synthetic-secret'
    assert 'synthetic-secret' not in repr(settings)


@pytest.mark.asyncio
async def test_both_providers_deduplicate_and_preserve_dates(monkeypatch, result):
    queries = []
    async def tavily(query):
        queries.append(query)
        return [{'title': 'Release', 'url': 'https://example.org/release?utm_source=tavily',
                 'content': 'Synthetic WPI evidence', 'published_date': '2026-09-01'}]
    async def ddgs(query):
        queries.append(query)
        return [{'title': 'Release', 'href': 'https://example.org/release', 'body': 'Synthetic WPI evidence'},
                {'href': 'javascript:alert(1)', 'body': 'Bad URL'},
                {'href': 'https://example.org/india', 'body': 'India is a country in South Asia.'}]
    monkeypatch.setattr(research, 'search_tavily', tavily)
    monkeypatch.setattr(research, 'search_ddgs', ddgs)
    data = await research.gather_research(parse_prices_intent('India WPI'), result)
    assert data['status'] == 'available' and len(data['sources']) == 1
    assert data['sources'][0]['providers'] == ['tavily', 'ddgs']
    assert data['sources'][0]['published_at'] == '2026-09-01'
    assert len(queries) == 2 and all('2026-08' in q and 'WPI' in q for q in queries)


@pytest.mark.asyncio
@pytest.mark.parametrize('failed_provider', ['search_tavily', 'search_ddgs'])
async def test_one_provider_failure_does_not_hide_other(monkeypatch, result, failed_provider):
    async def ok(query):
        return [{'url': 'https://example.org/a', 'content': 'WPI evidence'}]
    async def fail(query):
        raise RuntimeError('secret-that-must-not-leak')
    monkeypatch.setattr(research, 'search_tavily', ok)
    monkeypatch.setattr(research, 'search_ddgs', ok)
    monkeypatch.setattr(research, failed_provider, fail)
    data = await research.gather_research(parse_prices_intent('India WPI'), result)
    assert data['status'] == 'partial' and len(data['sources']) == 1
    assert 'secret-that-must-not-leak' not in str(data)
    assert result.status == 'available' and result.observations[0].value == 5


@pytest.mark.asyncio
async def test_empty_and_timeout_are_visible(monkeypatch, result):
    async def empty(query):
        return []
    async def timeout(query):
        raise asyncio.TimeoutError()
    monkeypatch.setattr(research, 'search_tavily', empty)
    monkeypatch.setattr(research, 'search_ddgs', timeout)
    data = await research.gather_research(parse_prices_intent('India WPI'), result)
    assert data['status'] == 'unavailable' and len(data['errors']) == 2


@pytest.mark.asyncio
async def test_tavily_request_uses_third_key(monkeypatch):
    monkeypatch.setattr(prices_settings, 'TVLY_KEY_3', SecretStr('synthetic-key'))
    real_client = httpx.AsyncClient
    def handler(request):
        assert request.headers['Authorization'] == 'Bearer synthetic-key'
        assert b'synthetic-key' not in request.content
        return httpx.Response(200, json={'results': [{'url': 'https://example.org', 'content': 'test'}]})
    monkeypatch.setattr(research.httpx, 'AsyncClient', lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))
    assert len(await research.search_tavily('India WPI')) == 1


@pytest.mark.asyncio
async def test_full_agent_preserves_official_status_and_adds_research(monkeypatch, result):
    from prices_sector import agent
    class MCP:
        def __init__(self, *args):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def call_tool(self, *args):
            return result.model_dump(mode='json')
    async def gather(*args):
        return {'status': 'partial', 'sources': [{'title': 'Release', 'url': 'https://example.org/release'}],
                'errors': ['ddgs search unavailable.']}
    async def synthesis(*args):
        return 'This synthesizes wholesale price changes.'
    async def market():
        return {'status': 'unavailable', 'proxies': [], 'total': 0}
    async def news(*args, **kwargs):
        return {'status': 'unavailable', 'query': 'q', 'news_items': [], 'total_results': 0}
    monkeypatch.setattr(agent, 'Client', MCP)
    monkeypatch.setattr(agent, 'gather_research', gather)
    monkeypatch.setattr(agent, '_execute_groq_reasoning', synthesis)
    monkeypatch.setattr(agent, 'fetch_inflation_market_proxies', market)
    monkeypatch.setattr(agent, 'fetch_realtime_prices_news', news)
    output = await agent.prices_agent_node({'query': 'Explain India WPI'})
    assert output['prices_sector_data']['status'] == 'available'
    assert output['prices_sector_data']['web_research']['status'] == 'partial'
    assert 'This synthesizes' in output['prices_sector_analysis']
    assert '[Release]' in output['prices_sector_analysis']
    assert 'ddgs search unavailable' in output['prices_sector_analysis']
    assert output['prices_sector_citations'][0]['value'] == 5


def test_explanation_queries_route_to_prices():
    assert is_direct_prices_query('Explain India WPI and its drivers')
    assert is_direct_prices_query('Why is CPI inflation rising?')
    assert not is_direct_prices_query('How does inflation affect GDP?')
