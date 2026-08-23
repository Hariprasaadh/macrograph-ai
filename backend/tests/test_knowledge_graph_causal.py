"""Tests for Knowledge Graph Ontology, NetworkX engine, Granger causality, and Scenario Simulation."""
from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from core.data.schema import CausalRelationType
from core.knowledge_graph.ontology import ontology
from core.knowledge_graph.networkx_engine import graph_engine
from core.knowledge_graph.neo4j_store import neo4j_store
from core.econometrics.causal_engine import causal_engine


class KnowledgeGraphAndCausalTests(unittest.TestCase):
    def test_ontology_contains_all_staged_sectors(self) -> None:
        self.assertGreaterEqual(len(ontology.indicators), 12)
        self.assertGreaterEqual(len(ontology.relationships), 8)
        
        # Verify 5-tier classification presence
        rel_types = {r.relation_type for r in ontology.relationships}
        self.assertIn(CausalRelationType.THEORY, rel_types)
        self.assertIn(CausalRelationType.GRANGER_PREDICTIVE, rel_types)
        self.assertIn(CausalRelationType.STRUCTURAL_CAUSAL_MODEL, rel_types)

    def test_networkx_shortest_transmission_path(self) -> None:
        # Path from Brent Crude to Real GDP
        path = graph_engine.get_shortest_transmission_path(
            source_id="in.macro.prices.brent_crude",
            target_id="in.macro.real.gdp_growth"
        )
        self.assertGreater(len(path), 0)
        self.assertEqual(path[0].source_indicator_id, "in.macro.prices.brent_crude")
        self.assertEqual(path[-1].target_indicator_id, "in.macro.real.gdp_growth")

    def test_networkx_causal_neighborhood(self) -> None:
        cpi_nbr = graph_engine.get_causal_neighborhood("in.macro.prices.cpi_headline")
        self.assertIn("upstream_drivers", cpi_nbr)
        self.assertIn("downstream_impacts", cpi_nbr)
        self.assertGreater(len(cpi_nbr["upstream_drivers"]), 0)
        self.assertGreater(len(cpi_nbr["downstream_impacts"]), 0)

    def test_networkx_mermaid_diagram_generation(self) -> None:
        mermaid = graph_engine.generate_mermaid_diagram(["in.macro.prices.brent_crude", "in.macro.prices.cpi_headline"])
        self.assertIn("graph LR", mermaid)
        self.assertIn("-->", mermaid)

    def test_granger_causality_statistical_computation(self) -> None:
        # Synthetic causal series: Y_t = 0.8 * X_{t-1} + noise
        np.random.seed(42)
        n = 50
        x = np.random.normal(0, 1, n)
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = 0.8 * x[t-1] + np.random.normal(0, 0.2)

        df = pd.DataFrame({"x_cause": x, "y_effect": y})
        res = causal_engine.test_granger_causality(df, cause_col="x_cause", effect_col="y_effect", max_lag=2)
        self.assertTrue(res["is_significant"])
        self.assertLess(res["p_value"], 0.05)

    def test_scenario_shock_simulation(self) -> None:
        # Simulate a +20 USD/barrel Brent Crude Oil shock
        sim = causal_engine.simulate_scenario(
            scenario_name="Global Crude Surge (+20 USD)",
            shock_variable="in.macro.prices.brent_crude",
            shock_magnitude=20.0,
            horizon_periods=4
        )
        self.assertEqual(sim.shock_variable, "in.macro.prices.brent_crude")
        self.assertIn("in.macro.prices.wpi_all", sim.forecasted_impacts)
        self.assertIn("in.macro.prices.cpi_headline", sim.forecasted_impacts)
        self.assertGreater(len(sim.provenance_chain), 0)


if __name__ == "__main__":
    unittest.main()
