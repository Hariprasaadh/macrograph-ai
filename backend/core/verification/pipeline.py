"""One entry point for validation, verification and deterministic rendering."""
from __future__ import annotations

from collections import Counter
from typing import Any
from pydantic import ValidationError

from .models import CLAIM_ADAPTER, ObservationClaim, PriceDirectionClaim, RateChangeClaim, VerificationResult
from .numeric import verify_numeric
from .qualitative import verify_qualitative


def verify_claims(proposals: list[Any], evidence: dict[str, Any]) -> dict[str, Any]:
    results = []
    seen = set()
    for index, proposal in enumerate(proposals):
        try:
            claim = CLAIM_ADAPTER.validate_python(proposal)
            if claim.claim_id in seen:
                raise ValueError('duplicate_claim_id')
            seen.add(claim.claim_id)
            result = (verify_numeric(claim, evidence) if isinstance(claim, (ObservationClaim, RateChangeClaim, PriceDirectionClaim))
                      else verify_qualitative(claim, evidence))
        except (ValidationError, ValueError, ArithmeticError) as exc:
            result = VerificationResult(claim_id=f'invalid_{index}', claim_type='invalid', status='rejected',
                verification_method='schema_validation', failed_checks=['invalid_claim_schema'],
                details={'error_type': type(exc).__name__})
        results.append(result.model_dump(mode='json'))
    return {'version': '1', 'scope': 'Prices claims only; verification is relative to retrieved evidence.',
            'evidence': evidence, 'proposals': proposals, 'results': results,
            'summary': dict(Counter(r['status'] for r in results))}


def render_report(report: dict[str, Any]) -> str:
    paragraphs = list(dict.fromkeys(r['rendered_text'] for r in report['results'] if r['rendered_text']))
    withheld = sum(r['status'] in ('rejected', 'insufficient_evidence') for r in report['results'])
    if withheld:
        paragraphs.append(f'{withheld} proposed claim(s) were withheld because verification failed or evidence was insufficient.')
    return '\n\n'.join(paragraphs)
