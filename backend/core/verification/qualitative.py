"""Reviewed mechanisms and literal attribution, never model-certified causation."""
from __future__ import annotations

import html
import re
from urllib.parse import quote, urlsplit

from .models import GeneralMechanismClaim, ReportedExplanationClaim, StatisticalFindingClaim, VerificationResult

MECHANISMS = {
    'cpi_definition': 'CPI tracks a basket of goods and services bought by households; individual spending patterns differ.',
    'wpi_definition': 'WPI (Wholesale Price Index) tracks goods prices at the wholesale stage, not a household shopping bill.',
    'yoy_interpretation': 'Year-on-year compares the same month across two years, not this month with last month. A lower positive inflation rate means slower price growth relative to a year earlier, not deflation.',
    'wholesale_pass_through': 'Higher wholesale costs can affect business margins or retail prices. This is a general economic mechanism, not a finding about the current period: pass-through depends on firms and market conditions.',
}


def plain(text: str) -> str:
    text = html.escape(' '.join(text.split()))
    return re.sub(r'([\\`*_{}\[\]()#+!|>])', r'\\\1', text)


def verify_qualitative(claim, evidence: dict) -> VerificationResult:
    result = VerificationResult(claim_id=claim.claim_id, claim_type=claim.claim_type,
                                 status='insufficient_evidence', verification_method='not_established')
    if isinstance(claim, GeneralMechanismClaim):
        result.status = 'general_mechanism'
        result.verification_method = 'reviewed_template_v1'
        result.rendered_text = MECHANISMS[claim.mechanism_id]
        result.details = {'mechanism_id': claim.mechanism_id, 'current_period_finding': False}
    elif isinstance(claim, StatisticalFindingClaim):
        result.failed_checks = ['no_registered_statistical_analysis']
    elif isinstance(claim, ReportedExplanationClaim):
        result.evidence_ids = [claim.passage_id]
        passage = evidence['passages'].get(claim.passage_id)
        if not passage:
            result.failed_checks = ['unknown_passage']
            return result
        text, excerpt = passage['text'], claim.supporting_quote
        start = text.find(excerpt)
        end = start + len(excerpt)
        # Require sentence boundaries, avoiding deletion of a preceding negation.
        before = text[:start].rstrip() if start >= 0 else ''
        after = text[end:].lstrip()
        bounded = (not before or before[-1] in '.!?') and (not after or excerpt.rstrip()[-1:] in '.!?')
        if start < 0 or not bounded:
            result.status, result.failed_checks = 'rejected', ['quote_not_complete_source_sentence']
            return result
        try:
            url = urlsplit(passage['url'])
            valid_url = url.scheme in ('http', 'https') and url.hostname and not url.username and not url.password
        except ValueError:
            valid_url = False
        if not valid_url:
            result.status, result.failed_checks = 'rejected', ['invalid_source_url']
            return result
        result.status, result.verification_method = 'source_attributed', 'exact_passage_match'
        result.details = {'supporting_quote': excerpt, 'scope_verified': False,
                          'semantic_support_verified': False, 'evidence_type': passage['evidence_type']}
        link = quote(passage['url'], safe=':/?=&%+#@~')
        result.rendered_text = (f'Retrieved source excerpt: "{plain(excerpt)}" '
                                f'[Source]({link}). Attribution checked; this does not verify causation '
                                'or establish that the excerpt explains the requested period.')
    return result
