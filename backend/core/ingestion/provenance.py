"""Cryptographic Data Provenance and Audit Trail Engine."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from ..data.schema import CanonicalObservation, Evidence


class ProvenanceTracker:
    """Computes cryptographic integrity fingerprints and manages audit trails for observations."""

    @classmethod
    def compute_hash(cls, payload: Dict[str, Any] | str) -> str:
        if isinstance(payload, dict):
            raw = json.dumps(payload, sort_keys=True, default=str)
        else:
            raw = str(payload)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def create_evidence(
        cls,
        source_authority: str,
        document_title: str,
        url: Optional[str] = None,
        publication_date: Optional[str] = None,
        verbatim_excerpt: Optional[str] = None,
        observations: Optional[list[CanonicalObservation]] = None
    ) -> Evidence:
        hashes = [obs.provenance_hash for obs in (observations or []) if obs.provenance_hash]
        return Evidence(
            source_authority=source_authority,
            document_title=document_title,
            publication_date=publication_date or datetime.now(timezone.utc).date().isoformat(),
            url=url,
            verbatim_excerpt=verbatim_excerpt,
            observation_hashes=hashes
        )
