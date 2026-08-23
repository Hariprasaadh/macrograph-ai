"""Data Normalizer transforming raw vendor payloads into CanonicalObservation records."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats

from ..data.schema import CanonicalObservation, DataStatusEnum, RevisionStatusEnum
from .validators import ObservationValidator


class DataNormalizer:
    """Normalizes raw indicator readings, adds provenance hashes, and computes statistical features."""

    @classmethod
    def normalize_observation(
        cls,
        indicator_id: str,
        observation_period: str,
        value: Any,
        unit: str,
        history_values: Optional[List[float]] = None,
        data_status: DataStatusEnum = DataStatusEnum.LIVE,
        revision_status: RevisionStatusEnum = RevisionStatusEnum.FINAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CanonicalObservation:
        # 1. Validate period and numeric value
        valid_period = ObservationValidator.validate_period_format(observation_period)
        valid_val = ObservationValidator.validate_numeric(indicator_id, value) if value is not None else None

        # 2. Compute rolling Z-score and percentile rank if historical series provided
        z_score = None
        pct_rank = None
        if valid_val is not None and history_values and len(history_values) >= 5:
            arr = np.array(history_values, dtype=float)
            arr = arr[~np.isnan(arr)]
            if len(arr) >= 5 and np.std(arr) > 0:
                z_score = round(float((valid_val - np.mean(arr)) / np.std(arr)), 2)
                pct_rank = round(float(stats.percentileofscore(arr, valid_val)), 1)

        return CanonicalObservation(
            indicator_id=indicator_id,
            observation_period=valid_period,
            value=valid_val,
            unit=unit,
            revision_status=revision_status,
            data_status=data_status,
            z_score=z_score,
            percentile_rank=pct_rank,
            metadata=metadata or {}
        )
