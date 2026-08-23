"""Tests for Canonical Data Layer, Ingestion Engine, and Data Provenance."""
from __future__ import annotations

import unittest
from core.data.schema import (
    CanonicalIndicator,
    CanonicalObservation,
    CausalRelationship,
    CausalRelationType,
    DataStatusEnum,
    Evidence,
    RevisionStatusEnum,
    ScenarioResult,
    SectorEnum,
)
from core.database.macro_store import macro_store
from core.ingestion.validators import ObservationValidator, ValidationError
from core.ingestion.normalizer import DataNormalizer
from core.ingestion.provenance import ProvenanceTracker
from core.ingestion.registry import source_registry


class CanonicalIngestionTests(unittest.TestCase):
    def test_canonical_indicator_creation(self) -> None:
        ind = CanonicalIndicator(
            indicator_id="in.macro.prices.cpi_headline",
            name="Headline CPI Inflation",
            sector=SectorEnum.PRICES_INFLATION,
            unit="% YoY",
            frequency="monthly",
            source_authority="MoSPI"
        )
        self.assertEqual(ind.sector, SectorEnum.PRICES_INFLATION)

    def test_canonical_observation_provenance_hash(self) -> None:
        obs = CanonicalObservation(
            indicator_id="in.macro.prices.cpi_headline",
            observation_period="2025-01-01",
            value=4.26,
            unit="% YoY"
        )
        self.assertIsNotNone(obs.provenance_hash)
        self.assertEqual(len(obs.provenance_hash), 16)

    def test_observation_validator_bounds(self) -> None:
        # Valid CPI
        val = ObservationValidator.validate_numeric("cpi_inflation", 5.2)
        self.assertEqual(val, 5.2)

        # Corrupted / Extreme value violation
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_numeric("cpi_inflation", 999.0)

    def test_data_normalizer_zscore_and_percentiles(self) -> None:
        history = [3.0, 4.0, 5.0, 6.0, 7.0]
        obs = DataNormalizer.normalize_observation(
            indicator_id="in.macro.prices.cpi_headline",
            observation_period="2025-01-01",
            value=5.0,
            unit="% YoY",
            history_values=history
        )
        self.assertEqual(obs.z_score, 0.0)
        self.assertEqual(obs.percentile_rank, 60.0)

    def test_causal_relationship_types(self) -> None:
        rel = CausalRelationship(
            source_indicator_id="in.macro.monetary.repo_rate",
            target_indicator_id="in.macro.monetary.bank_credit_growth",
            relation_type=CausalRelationType.GRANGER_PREDICTIVE,
            transmission_lag_months=3,
            elasticity_sign="-",
            empirical_p_value=0.012,
            confidence_score=0.92,
            mechanism_description="Policy rate hike raises marginal cost of lending, slowing credit demand."
        )
        self.assertEqual(rel.relation_type, CausalRelationType.GRANGER_PREDICTIVE)
        self.assertEqual(rel.transmission_lag_months, 3)

    def test_macro_store_canonical_observation_retrieval(self) -> None:
        obs = macro_store.get_latest_canonical_observation("in.macro.prices.cpi_headline")
        self.assertIsNotNone(obs)
        self.assertEqual(obs.indicator_id, "in.macro.prices.cpi_headline")
        self.assertGreater(obs.value, 0.0)

        series_df = macro_store.get_canonical_series("in.macro.prices.cpi_headline")
        self.assertFalse(series_df.empty)


if __name__ == "__main__":
    unittest.main()
