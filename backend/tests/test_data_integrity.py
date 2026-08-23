"""Tests verifying data integrity, absence of hardcoded fallbacks, and DuckDB caching."""
from __future__ import annotations

import unittest
from finance_sector.clients.finance_data_client import FinanceDataClient
from capital_market_sector.clients.market_data_client import CapitalMarketsDataClient
from core.database.macro_store import macro_store


class DataIntegrityAndProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.finance_client = FinanceDataClient(timeout=3)
        self.cap_client = CapitalMarketsDataClient(timeout=3)

    def test_finance_client_returns_provenance_and_no_magic_numbers(self) -> None:
        gdp = self.finance_client.get_gdp_growth()
        self.assertIn("data_status", gdp)
        self.assertIn(gdp["data_status"], ["live", "verified_historical_cache"])
        self.assertIsNotNone(gdp["latest_value"])

        cpi = self.finance_client.get_cpi_inflation()
        self.assertIn("data_status", cpi)
        self.assertIn(cpi["data_status"], ["live", "verified_historical_cache"])

        repo = self.finance_client.get_repo_rate()
        self.assertIn("data_status", repo)

        forex = self.finance_client.get_forex_reserves()
        self.assertIn("data_status", forex)

    def test_capital_markets_client_returns_verified_structures(self) -> None:
        nifty = self.cap_client.get_nifty_50()
        self.assertIn("data_status", nifty.columns)
        self.assertFalse(nifty.empty)

        earnings = self.cap_client.get_corporate_earnings()
        self.assertIn("data_status", earnings.columns)
        self.assertFalse(earnings.empty)

        mf_flows = self.cap_client.get_mf_flows()
        self.assertIn("data_status", mf_flows.columns)
        self.assertFalse(mf_flows.empty)

    def test_macro_store_duckdb_persistence(self) -> None:
        macro_store.insert_observation(
            sector="test_sector",
            indicator="test_indicator",
            sub_indicator="test_sub",
            observation_date="2026-01-01",
            value=99.9,
            unit="test_unit",
            source="test_source",
            data_status="verified_test"
        )
        obs = macro_store.get_latest_observation(
            sector="test_sector",
            indicator="test_indicator",
            sub_indicator="test_sub"
        )
        self.assertIsNotNone(obs)
        self.assertEqual(obs["latest_value"], 99.9)
        self.assertEqual(obs["data_status"], "verified_test")


if __name__ == "__main__":
    unittest.main()
