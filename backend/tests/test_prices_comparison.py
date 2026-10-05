"""Four Prices country-routing regressions; all values below are synthetic."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from prices_sector import client
from prices_sector.agent import prices_agent_node
from prices_sector.intent import parse_prices_intent, is_direct_prices_query
from prices_sector.metadata import shift_month
from prices_sector.models import PriceObservation

LATEST = shift_month(datetime.now(timezone.utc).strftime('%Y-%m'), -1)
COMMON = shift_month(LATEST, -1)


@pytest.fixture
def sources(monkeypatch):
    state = {'calls': [], 'china_periods': [COMMON, shift_month(COMMON, -1)], 'imf_failure': False}

    class Source:
        def __init__(self, url, **kwargs):
            self.url = url

        async def __aenter__(self):
            state['calls'].append((self.url, 'connect'))
            return self

        async def __aexit__(self, *args):
            return False

        async def call_tool(self, name, args):
            assert self.url == client.IMF_URL
            state['calls'].append((self.url, name, args))
            if state['imf_failure']:
                raise RuntimeError('Synthetic IMF unavailable')
            if name == 'imf_get_database':
                assert args['dimension_id'] == 'COUNTRY' and args['codelist_filter'] == 'China'
                return {'key_format': 'COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY',
                        'dimensions': [{'id': 'COUNTRY', 'codelist': [
                            {'id': 'CHN', 'name': "China, People's Republic of"},
                            {'id': 'HKG', 'name': "Hong Kong Special Administrative Region, People's Republic of China"}]}]}
            assert args['key'] in ('CHN.CPI._T.YOY_PCH_PA_PT.M', client.IMF_CPI_KEY)
            periods = state['china_periods'] if args['key'].startswith('CHN.') else [LATEST, COMMON]
            return {'observations': [{'series_key': args['key'], 'time_period': p.replace('-', '-M'), 'value': 2.0} for p in periods]}

    async def discover(call, dataset, base):
        state['calls'].append(('mospi', 'discover'))
        return 'TEST', {}

    async def india(call, intent, request, base, metadata, start, end):
        assert intent.geography in ('India', 'Tamil Nadu')
        state['calls'].append(('mospi', 'india'))
        records = [PriceObservation(source_authority='NSO / MoSPI', dataset_reference='CPI',
            indicator_id='in.macro.prices.cpi_headline_combined_yoy', indicator='CPI (General)',
            series_code='CPI:TEST:headline:combined', request_id=request.key, observation_period=p,
            value=3.0, unit='% YoY', url=client.MOSPI_URL, mcp_server=client.MOSPI_URL,
            mcp_tool='get_data', retrieved_at=datetime.now(timezone.utc)) for p in [LATEST, COMMON, shift_month(COMMON, -1)]]
        return records, [], {'dataset': 'CPI'}

    monkeypatch.setattr(client, 'Client', Source)
    monkeypatch.setattr(client.mospi, 'discover', discover)
    monkeypatch.setattr(client.mospi, 'fetch_request', india)
    return state


@pytest.mark.asyncio
async def test_india_china_comparison(sources):
    aliases = ['compare indian cpi with china', "compare India's inflation with China's",
               'India vs China inflation', 'India China CPI comparison', 'compare CPI of India and China']
    for query in aliases:
        intent = parse_prices_intent(query)
        assert intent.operation == 'comparison' and intent.countries == ['India', 'China']
        assert is_direct_prices_query(query)
    mixed = parse_prices_intent('Compare India CPI from MoSPI with China CPI from IMF')
    assert mixed.source == 'mospi' and not mixed.errors
    result = await prices_agent_node({'query': aliases[0]})
    data = result['prices_sector_data']
    assert data['status'] == 'available' and data['diagnostics']['comparison_complete']
    assert {o['country'] for o in data['observations']} == {'India', 'China'}
    assert {o['observation_period'] for o in data['observations']} == {COMMON}
    assert {o['country']: o['mcp_server'] for o in data['observations']} == {'India': client.MOSPI_URL, 'China': client.IMF_URL}
    assert '| India |' in result['prices_sector_analysis'] and '| China |' in result['prices_sector_analysis']
    assert 'mermaid' not in result['prices_sector_analysis'].lower()
    sources['china_periods'] = [shift_month(COMMON, -4)]
    unaligned = await prices_agent_node({'query': aliases[0]})
    assert unaligned['prices_sector_data']['status'] == 'partial'
    assert 'periods are shown and differ' in unaligned['prices_sector_analysis']
    sources['calls'].clear()
    await prices_agent_node({'query': 'compare India and China CPI from IMF'})
    assert all(c[0] == client.IMF_URL for c in sources['calls'])


@pytest.mark.asyncio
async def test_india_latest_still_mospi(sources):
    result = await prices_agent_node({'query': "What is India's latest CPI inflation?"})
    assert result['prices_sector_data']['source'] == 'MoSPI'
    assert result['prices_sector_data']['observations'][0]['observation_period'] == LATEST
    await client.fetch_cpi_inflation(geography='Tamil Nadu')
    assert all(c[0] != client.IMF_URL for c in sources['calls'])


@pytest.mark.asyncio
async def test_china_explicit_imf(sources):
    result = await prices_agent_node({'query': "What is China's CPI inflation according to IMF?"})
    data = result['prices_sector_data']
    assert data['status'] == 'available' and data['source'] == 'IMF'
    assert len(data['observations']) == 1 and data['observations'][0]['country'] == 'China'
    assert data['observations'][0]['series_code'] == 'CHN.CPI._T.YOY_PCH_PA_PT.M'
    assert all(c[0] == client.IMF_URL for c in sources['calls'])
    assert 'China price inflation' in result['prices_sector_analysis']


@pytest.mark.asyncio
async def test_imf_unavailable_preserves_india(sources):
    sources['imf_failure'] = True
    result = await prices_agent_node({'query': 'compare indian cpi with china'})
    data = result['prices_sector_data']
    assert data['status'] == 'partial' and not data['diagnostics']['comparison_complete']
    assert data['missing'] == ['China']
    assert [o['country'] for o in data['observations']] == ['India']
    assert '| China | Unavailable | Unavailable | IMF |' in result['prices_sector_analysis']
    assert 'Synthetic IMF unavailable' in result['prices_sector_analysis']
    assert 'IMF did not return a valid China CPI observation' in result['prices_sector_analysis']
