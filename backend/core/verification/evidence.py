"""Content-addressed evidence; revisions change IDs, repeated retrievals do not."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def content_id(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str, allow_nan=False)
    return prefix + '_' + hashlib.sha256(encoded.encode()).hexdigest()


def observation_identity(record: dict[str, Any]) -> str:
    # Keep revision/definition changes distinct; retrieval clock is not a revision.
    payload = {k: v for k, v in record.items() if k not in ('observation_id', 'retrieved_at', 'request_id')}
    payload['metadata'] = {k: v for k, v in payload.get('metadata', {}).items()
                           if k not in ('freshness', 'coverage_complete', 'latest_available_period',
                                        'comparison_period', 'country', 'geography', 'sector')}
    return content_id('obs', payload)


def build_evidence(observations: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    records, passages = {}, {}
    for raw in observations:
        record = dict(raw)
        record['observation_id'] = observation_identity(record)
        records[record['observation_id']] = record
    for source in sources:
        text = source.get('snippet')
        if not isinstance(text, str) or not text.strip() or not source.get('url'):
            continue
        source_id = content_id('src', {'url': source['url']})
        passage_id = content_id('passage', {'source_id': source_id, 'text': text,
                                          'published_at': source.get('published_at')})
        passages[passage_id] = {**source, 'source_id': source_id, 'passage_id': passage_id,
                               'text': text, 'evidence_type': source.get('evidence_type', 'search_excerpt')}
    return {'observations': records, 'passages': passages}
