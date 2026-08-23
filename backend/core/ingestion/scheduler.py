"""Ingestion Pipeline Runner and Refresh Scheduler."""
from __future__ import annotations

from typing import Dict, List, Optional
from ..data.schema import CanonicalObservation
from .registry import source_registry


class IngestionScheduler:
    """Coordinates automated and on-demand ingestion jobs across registered source adapters."""

    def __init__(self) -> None:
        self.registry = source_registry

    def run_ingestion_pipeline(self, indicator_ids: Optional[List[str]] = None) -> Dict[str, Optional[CanonicalObservation]]:
        targets = indicator_ids or list(self.registry._adapters.keys())
        results: Dict[str, Optional[CanonicalObservation]] = {}

        for ind_id in targets:
            adapter = self.registry.get_adapter(ind_id)
            if adapter:
                try:
                    obs = adapter()
                    results[ind_id] = obs
                except Exception as err:
                    results[ind_id] = None

        return results


ingestion_scheduler = IngestionScheduler()
