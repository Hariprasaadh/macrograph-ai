"""WPI source-schema regressions; observation values are synthetic."""
import pytest

from prices_sector import mospi
from prices_sector.metadata import choose_base
from prices_sector.models import PriceRequest, PricesIntent


def indicators(note):
    return {'data': [{'label': '2022-23'}, {'label': '2011-12'}], '_note': note}


@pytest.mark.parametrize('declaration', [
    "Default base_year is '2022-23' (latest series, data from 2023 onwards).",
    "Current base_year='2022-23'.",
    'Latest base_year is "2022-23".',
])
def test_source_declared_base(declaration):
    assert choose_base(indicators(declaration), 'WPI', None) == '2022-23'


@pytest.mark.parametrize('note', ['', "Default base_year is '2099-00'."])
def test_does_not_guess_base(note):
    with pytest.raises(ValueError, match='could not be identified'):
        choose_base(indicators(note), 'WPI', None)


def test_explicit_base_overrides_default():
    payload = indicators("Default base_year is '2022-23'.")
    assert choose_base(payload, 'WPI', '2011-12') == '2011-12'
    with pytest.raises(ValueError, match='not supported'):
        choose_base(payload, 'WPI', '2099-00')


@pytest.mark.parametrize('field', ['major_group', 'majorgroup', 'major_group_name'])
def test_aggregate_name_aliases(field):
    assert mospi.matches_row({field: 'Wholesale Price Index'}, 'major_group', '100', 'Wholesale price index')


@pytest.mark.parametrize('field', ['group', 'sub_group', 'subgroup', 'sub_sub_group',
                                 'sub_subgroup', 'item', 'sub_sub_group_code'])
def test_rejects_children(field):
    assert not mospi.matches_row({'major_group': 'Wholesale Price Index', field: 'Child'},
                                'major_group', '100', 'Wholesale price index')


@pytest.mark.asyncio
async def test_live_shaped_wpi_discovery_and_yoy():
    calls = []

    async def call(tool, args):
        calls.append((tool, args))
        if tool == 'get_indicators':
            return indicators("Default base_year is '2022-23' (latest series, data from 2023 onwards).")
        assert args.get('base_year', args.get('filters', {}).get('base_year')) == '2022-23'
        if tool == 'get_metadata':
            return {'data': {'major_group': [{'major_group_code': '100', 'label': 'Wholesale price index'}],
                             'year': [{'year': 2025}, {'year': 2026}]}}
        assert args['filters']['major_group_code'] == '100'
        rows = [dict(base_year='2022-23', year=y, month='August', major_group='Wholesale Price Index',
                     group=None, sub_group=None, sub_sub_group=None, item=None, index_value=v)
                for y, v in [(2026, '110'), (2025, '100')]]
        rows.append({**rows[0], 'sub_group': 'Child', 'index_value': '999'})
        rows.append({**rows[0], 'base_year': '2011-12', 'index_value': '999'})
        return {'data': rows, 'meta_data': {'totalPages': 1}}

    base, meta = await mospi.discover(call, 'WPI', None)
    request = PriceRequest(indicator='wpi')
    observations, errors, _ = await mospi.fetch_request(
        call, PricesIntent(requests=[request]), request, base, meta, '2026-08', '2026-08')
    assert not errors
    assert len(observations) == 1
    assert observations[0].value == pytest.approx(10)
    assert observations[0].base_year == '2022-23'
    assert observations[0].observation_period == '2026-08'
    assert observations[0].metadata['previous_year_period'] == '2025-08'
    assert [tool for tool, _ in calls] == ['get_indicators', 'get_metadata', 'get_data']
