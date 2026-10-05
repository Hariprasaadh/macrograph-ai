"""Prices-only regressions. All numeric fixtures are synthetic, never fallback data."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from prices_sector import client as prices_client
from prices_sector.agent import prices_agent_node
from prices_sector.intent import is_direct_prices_query, parse_prices_intent
from prices_sector.metadata import shift_month
from prices_sector.normalization import normalize_mcp_response
from prices_sector.agents.executor import PricesSectorAgentExecutor
from core.protocols.a2a.models import RequestContext
from core.protocols.a2a.lifecycle import EventQueue

QUERIES = [
    "What is India's latest CPI inflation from MoSPI?",
    "Show India's latest CPI inflation for food, fuel and light, housing, health, and transport.",
    "Show India's CPI and WPI trend.",
    "Show India's CPI inflation from IMF for the latest available period.",
    "Show India's CPI food, rural, and urban inflation.",
]
END = shift_month(datetime.now(timezone.utc).strftime('%Y-%m'), -2)
PERIODS = [shift_month(END, -i) for i in range(12)]


class FakeSource:
    calls = []
    failed_category = None
    imf_empty = False

    def __init__(self, url, **kwargs):
        self.url = url

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def call_tool(self, name, args):
        self.calls.append((self.url, name, args))
        if name == 'imf_query_dataset':
            rows = [] if self.imf_empty else [dict(series_key=prices_client.IMF_CPI_KEY,
                time_period=p.replace('-', '-M'), value=i + 1) for i, p in enumerate(PERIODS)]
            return {'observations': rows}
        dataset = args['dataset']
        if name == 'get_indicators':
            return {'data': {'base_year': [{'base_year': 'TEST'}]}, 'current_base_year': 'TEST'}
        if name == 'get_metadata':
            if dataset == 'WPI':
                return {'data': {'major_group': [{'major_group_code': 'W', 'label': 'Wholesale price index'}]}}
            return {'data': [{
                'state': [{'state_code': 'INDIA', 'state_name': 'All India'}],
                'sector': [{'sector_code': s, 'sector_name': s.title()} for s in ['combined', 'rural', 'urban']],
                'division': [{'division_code': str(i), 'division_name': name} for i, name in enumerate(
                    ['CPI (General)', 'Food', 'Fuel and light', 'Housing', 'Health', 'Transport'])]}]}
        filters = args['filters']
        assert filters['limit'] == 30
        if filters['page'] > 1:
            return []
        if dataset == 'WPI':
            # Reverse-sorted source rows and prior-year pairs; a child row must not replace the aggregate.
            rows = [dict(base_year='TEST', period=p, majorgroup='Wholesale price index', index_value=110) for p in PERIODS]
            rows += [dict(base_year='TEST', period=shift_month(p, -12), majorgroup='Wholesale price index', index_value=100) for p in PERIODS]
            rows.append(dict(base_year='TEST', period=END, majorgroup='Wholesale price index', group='Child', index_value=999))
        else:
            code = filters['division_code']
            if code == self.failed_category:
                raise RuntimeError('Synthetic subgroup failure')
            rows = [dict(base_year='TEST', period=p, division_code=code, sector=filters['sector_code'].title(),
                         state='All India', inflation=i + 1) for i, p in enumerate(PERIODS)]
            rows.append(dict(base_year='OLD', period=END, division_code=code, inflation=999))
        # A bare list is deliberately returned to reproduce the original crash path.
        return rows


@pytest.mark.parametrize('case', range(5), ids=['latest_mospi', 'subgroups_partial', 'cpi_wpi_trend', 'explicit_imf', 'food_rural_urban'])
@pytest.mark.asyncio
async def test_requested_queries(case, monkeypatch):
    FakeSource.calls = []
    FakeSource.failed_category = '3' if case == 1 else None
    FakeSource.imf_empty = False
    monkeypatch.setattr(prices_client, 'Client', FakeSource)
    query = QUERIES[case]
    assert is_direct_prices_query(query)
    intent = parse_prices_intent(query)
    result = await prices_agent_node({'query': query})
    data = result['prices_sector_data']
    observations = data['observations']
    assert observations
    assert 'mermaid' not in result['prices_sector_analysis'].casefold()
    assert all(o['series_code'] and o['mcp_server'] and o['dataset_reference'] for o in observations)
    assert max(o['observation_period'] for o in observations) == END
    if case == 0:
        assert len(observations) == 1 and observations[0]['value'] == 1
        assert data['source'] == 'MoSPI' and data['status'] == 'available'
        executor = await PricesSectorAgentExecutor().execute(RequestContext(task_id='prices-test', query=query), EventQueue())
        assert executor.artifacts[0].content['observations'][0]['value'] == observations[0]['value']
    elif case == 1:
        assert data['status'] == 'partial'
        assert len(observations) == 4
        assert 'cpi:housing:combined' in data['missing']
        assert 'Synthetic subgroup failure' in result['prices_sector_analysis']
    elif case == 2:
        assert intent.operation == 'trend' and intent.lookback_months == 12
        assert len(observations) == 24
        assert {o['dataset_reference'] for o in observations} == {'CPI', 'WPI'}
        assert {o['observation_period'] for o in observations} == set(PERIODS)
        assert any(o['observation_period'].endswith('-12') for o in observations)
        assert all(o['value'] == pytest.approx(10) for o in observations if o['dataset_reference'] == 'WPI')
        assert '| Period | CPI:' in result['prices_sector_analysis'] and 'WPI:' in result['prices_sector_analysis']
    elif case == 3:
        assert data['source'] == 'IMF'
        assert all('start_period' not in args for _, _, args in FakeSource.calls)
        assert all(url == prices_client.IMF_URL for url, _, _ in FakeSource.calls)
        FakeSource.imf_empty = True
        unavailable = await prices_agent_node({'query': query})
        assert unavailable['prices_sector_data']['status'] == 'unavailable'
        assert all(url == prices_client.IMF_URL for url, _, _ in FakeSource.calls)
    else:
        assert {o['request_id'] for o in observations} == {'cpi:food:combined', 'cpi:headline:rural', 'cpi:headline:urban'}


ROW = {'period': '2025-12', 'inflation': 1}
ENVELOPE = {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': json.dumps([ROW])}]}}


@pytest.mark.parametrize('payload', [
    {'data': [ROW]}, [ROW], json.dumps([ROW]), json.dumps(json.dumps([ROW])),
    [{'type': 'text', 'text': json.dumps([ROW])}], ENVELOPE,
    'event: message\ndata: ' + json.dumps(ENVELOPE) + '\n\n',
    SimpleNamespace(is_error=False, structured_content=None, data=None,
                    content=[SimpleNamespace(model_dump=lambda **_: {'type': 'text', 'text': json.dumps([ROW])})]),
])
def test_mcp_normalization(payload):
    assert normalize_mcp_response(payload)['data'] == [ROW]


@pytest.mark.parametrize('payload', [None, '', [], {}, {'isError': True, 'content': 'failure'}])
def test_mcp_empty_or_error(payload):
    assert isinstance(normalize_mcp_response(payload), dict)
