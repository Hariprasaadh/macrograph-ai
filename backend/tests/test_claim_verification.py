"""Synthetic evidence tests: correctness, rejection and reproducible audit replay.

Note: claim verification was removed from the prices sector; the tests below
cover the shared core verification pipeline only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import pytest

from core.verification.audit import load_audit, save_audit
from core.verification.evidence import build_evidence
from core.verification.pipeline import render_report, verify_claims
from prices_sector.models import PriceObservation


def observation(value=6, period='2025-01', **changes):
    return PriceObservation(**{
        'source_authority': 'Synthetic NSO', 'dataset_reference': 'CPI', 'indicator_id': 'cpi_headline',
        'indicator': 'CPI headline', 'series_code': 'CPI:TEST:combined', 'request_id': 'cpi:headline:combined',
        'observation_period': period, 'country': 'India', 'base_year': 'TEST', 'value': value,
        'unit': '% YoY', 'url': 'https://example.org/cpi', 'mcp_server': 'https://example.org/mcp',
        'mcp_tool': 'get_data', 'retrieved_at': datetime.now(timezone.utc), **changes})


def registry(*rows):
    return build_evidence([r.model_dump(mode='json') for r in rows], [])


def change(evidence, value=-2, **overrides):
    first, last = evidence['observations']
    return {'claim_id': 'comparison', 'claim_type': 'rate_change', 'operation': 'subtract',
            'earlier_observation_id': first, 'later_observation_id': last,
            'proposed_value': value, 'output_unit': 'percentage_points', **overrides}


def verify(proposal, evidence):
    return verify_claims([proposal], evidence)['results'][0]


def test_disinflation_is_percentage_points_not_falling_prices():
    evidence = registry(observation(), observation(4, '2025-02'))
    result = verify(change(evidence), evidence)
    assert result['status'] == 'verified' and result['computed_value'] == -2
    assert 'declined' in result['rendered_text'] and '-2.00 percentage points' in result['rendered_text']
    assert 'prices fell' not in result['rendered_text'].lower()
    assert result['details']['calculation'] == '4.0 - 6.0'


@pytest.mark.parametrize('overrides', [
    {'proposed_value': 2}, {'output_unit': '%'}, {'operation': 'eval'},
    {'text': 'Prices fell by 2%.'}, {'later_observation_id': 'fabricated'},
])
def test_bad_proposals_never_render(overrides):
    evidence = registry(observation(), observation(4, '2025-02'))
    result = verify(change(evidence, **overrides), evidence)
    assert result['status'] in ('rejected', 'insufficient_evidence')
    assert not result['rendered_text']


@pytest.mark.parametrize('dimension,value', [('geography', 'Tamil Nadu'), ('sector', 'rural'),
    ('base_year', 'OTHER'), ('unit', 'index'), ('indicator_id', 'wpi'), ('country', 'China')])
def test_incompatible_observations(dimension, value):
    evidence = registry(observation(), observation(4, '2025-02', **{dimension: value}))
    assert verify(change(evidence), evidence)['status'] == 'rejected'


def test_order_unknown_base_and_unknown_evidence():
    evidence = registry(observation(6, '2025-02'), observation(4, '2025-01'))
    assert verify(change(evidence), evidence)['failed_checks'] == ['invalid_period_order']
    evidence = registry(observation(base_year=None), observation(4, '2025-02', base_year=None))
    assert verify(change(evidence), evidence)['failed_checks'] == ['unknown_index_base']


@pytest.mark.parametrize('value,direction', [(4, 'higher'), (0, 'unchanged'), (-2, 'lower')])
def test_yoy_direction_does_not_claim_monthly_movement(value, direction):
    evidence = registry(observation(value))
    claim = {'claim_id': 'direction', 'claim_type': 'price_direction_yoy',
             'observation_id': next(iter(evidence['observations'])), 'direction': direction,
             'comparison': 'same_month_previous_year'}
    result = verify(claim, evidence)
    assert result['status'] == 'verified'
    assert 'does not establish' in result['rendered_text']
    assert verify({**claim, 'comparison': 'previous_month'}, evidence)['status'] == 'rejected'
    wrong = 'lower' if direction != 'lower' else 'higher'
    assert verify({**claim, 'direction': wrong}, evidence)['status'] == 'rejected'


def test_ids_are_stable_but_revisions_and_scope_change_them():
    first = observation()
    assert first.observation_id == observation().observation_id
    assert first.observation_id != observation(5.9).observation_id
    assert first.observation_id != observation(metadata={'revision_status': 'revised'}).observation_id
    assert first.observation_id != observation(metadata={'geography': 'Tamil Nadu'}).observation_id
    assert first.observation_id == observation(observation_id='invented').observation_id
    assert first.observation_id == observation(metadata={'latest_available_period': '2026-01',
                                                        'comparison_period': '2025-01'}).observation_id


def test_boolean_is_not_a_number():
    with pytest.raises(ValueError, match='Boolean'):
        observation(True)


def test_conflicting_same_period_values_are_withheld():
    evidence = registry(observation(6), observation(7))
    claim = {'claim_id': 'obs', 'claim_type': 'observation', 'observation_id': next(iter(evidence['observations'])),
             'proposed_value': 6, 'output_unit': '% YoY'}
    assert verify(claim, evidence)['failed_checks'] == ['conflicting_observations_for_period']


def test_exact_passage_proves_only_attribution():
    text = 'The report does not establish that fuel caused inflation.'
    evidence = build_evidence([], [{'url': 'https://example.org/report', 'snippet': text}])
    claim = {'claim_id': 'web', 'claim_type': 'reported_explanation',
             'passage_id': next(iter(evidence['passages'])), 'supporting_quote': text}
    result = verify(claim, evidence)
    assert result['status'] == 'source_attributed'
    assert not result['details']['semantic_support_verified']
    assert 'does not verify causation' in result['rendered_text']
    assert verify({**claim, 'supporting_quote': 'fuel caused inflation.'}, evidence)['status'] == 'rejected'
    assert verify({**claim, 'supporting_quote': 'Food prices caused inflation.'}, evidence)['status'] == 'rejected'
    assert verify({**claim, 'text': 'Fuel definitely caused inflation.'}, evidence)['status'] == 'rejected'


def test_unsupported_statistical_claim_and_general_template():
    evidence = registry()
    claim = {'claim_id': 'stat', 'claim_type': 'statistical_finding', 'analysis_id': 'made-up'}
    assert verify(claim, evidence)['status'] == 'insufficient_evidence'
    assert verify({'claim_id': 'm', 'claim_type': 'general_mechanism',
                   'mechanism_id': 'wholesale_pass_through'}, evidence)['status'] == 'general_mechanism'


@pytest.mark.asyncio
async def test_persisted_audit_replays_without_network(tmp_path):
    evidence = registry(observation(), observation(4, '2025-02'))
    report = verify_claims([change(evidence)], evidence)
    path = tmp_path / 'audit.sqlite3'
    audit_id = await save_audit(report, path)
    loaded = load_audit(audit_id, path)
    replay = verify_claims(loaded['proposals'], loaded['evidence'])
    assert replay == report
    assert render_report(replay) == render_report(report)
