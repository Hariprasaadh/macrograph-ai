"""Deterministic rules for monthly YoY observations and within-series comparisons."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any

from .models import ObservationClaim, PriceDirectionClaim, RateChangeClaim, VerificationResult


def finite(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def verify_numeric(claim: ObservationClaim | PriceDirectionClaim | RateChangeClaim,
                   evidence: dict[str, Any]) -> VerificationResult:
    ids = ([claim.earlier_observation_id, claim.later_observation_id]
           if isinstance(claim, RateChangeClaim) else [claim.observation_id])
    outcome = VerificationResult(claim_id=claim.claim_id, claim_type=claim.claim_type,
                                 status='insufficient_evidence', verification_method='deterministic', evidence_ids=ids)
    registry = evidence['observations']
    if any(key not in registry for key in ids):
        outcome.failed_checks = ['unknown_observation']
        return outcome
    rows = [registry[key] for key in ids]
    values = [finite(row.get('value')) for row in rows]
    if any(value is None for value in values):
        outcome.failed_checks = ['missing_or_nonfinite_value']
        return outcome
    for row in rows:
        identity = ('indicator_id', 'series_code', 'country', 'geography', 'sector', 'base_year',
                    'unit', 'source_authority', 'observation_period')
        if any(all(other.get(k) == row.get(k) for k in identity) and
               finite(other.get('value')) != finite(row.get('value')) for other in registry.values()):
            outcome.failed_checks = ['conflicting_observations_for_period']
            return outcome
        scope = evidence.get('request_scope')
        if scope and (row.get('geography') not in scope['geographies'] or
                      not any(row.get('request_id', '').endswith(r) for r in scope['request_ids'])):
            outcome.status, outcome.failed_checks = 'rejected', ['outside_requested_scope']
            return outcome
        if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', str(row.get('observation_period', ''))):
            outcome.failed_checks = ['invalid_monthly_period']
            return outcome
        if row.get('unit') not in ('% YoY', '% MoM', 'index'):
            outcome.status, outcome.failed_checks = 'rejected', ['unsupported_input_unit']
            return outcome
        if any(not row.get(k) for k in ('indicator_id', 'series_code', 'geography', 'sector',
                                        'source_authority', 'url', 'mcp_tool', 'dataset_reference')):
            outcome.failed_checks = ['missing_dimensions_or_provenance']
            return outcome
    row, value = rows[-1], values[-1]
    scope = f"{row['geography']}: {row['indicator']} ({row['sector']})"
    period = row['observation_period']
    if isinstance(claim, RateChangeClaim):
        dimensions = ('indicator_id', 'series_code', 'country', 'geography', 'sector', 'base_year',
                      'unit', 'source_authority', 'dataset_reference')
        mismatches = [f'mismatched_{k}' for k in dimensions if rows[0].get(k) != rows[1].get(k)]
        if rows[0]['observation_period'] >= period:
            mismatches.append('invalid_period_order')
        if not row.get('base_year'):
            outcome.failed_checks = ['unknown_index_base']
            return outcome
        if mismatches:
            outcome.status, outcome.failed_checks = 'rejected', mismatches
            return outcome
        value = values[1] - values[0]
        movement = 'declined' if value < 0 else 'increased' if value > 0 else 'was unchanged'
        text = (f"{scope} inflation {movement} from {values[0]:.2f}% YoY in {rows[0]['observation_period']} "
                f"to {values[1]:.2f}% YoY in {period}; the change was {value:+.2f} percentage points.")
        outcome.unit = 'percentage_points'
        outcome.details['calculation'] = f'{values[1]} - {values[0]}'
    elif isinstance(claim, PriceDirectionClaim):
        direction = 'higher' if value > 0 else 'lower' if value < 0 else 'unchanged'
        if claim.direction != direction:
            outcome.status, outcome.failed_checks = 'rejected', ['incorrect_price_direction']
            return outcome
        change = (f'{abs(value):.2f}% {direction} than in the same month one year earlier' if value
                  else 'unchanged compared with the same month one year earlier')
        text = (f"For {scope} in {period}, prices were {change}. "
                'This does not establish the change from the immediately preceding month. '
                f'As a hypothetical illustration, a representative basket costing 100 a year earlier '
                f'would cost {Decimal(100) + value:.2f}; this is not an individual product price.')
        outcome.unit = '% YoY'
    else:
        text = f'{scope} inflation was {value:.2f}% YoY in {period}.'
        outcome.unit = '% YoY'
    outcome.computed_value = float(value)
    if not isinstance(claim, PriceDirectionClaim):
        # Compare at the displayed precision, avoiding hidden float-rounding tolerances.
        proposed = finite(claim.proposed_value)
        if proposed is None or proposed.quantize(Decimal('.01')) != value.quantize(Decimal('.01')):
            outcome.status, outcome.failed_checks = 'rejected', ['incorrect_arithmetic_or_value']
            return outcome
    outcome.status, outcome.rendered_text = 'verified', text
    outcome.details.update(periods=[r['observation_period'] for r in rows],
                           values=[r['value'] for r in rows], base_year=row.get('base_year'))
    return outcome
