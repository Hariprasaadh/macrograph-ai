"""NetworkX engine contract tests."""
from __future__ import annotations

import networkx as nx

from core.data.schema import CausalRelationship, CausalRelationType
from core.knowledge_graph.networkx_engine import NetworkXGraphEngine, graph_engine
from core.knowledge_graph.ontology import MacroeconomicOntology

BRENT = "in.macro.prices.brent_crude"
GDP = "in.macro.real.gdp_growth"
WPI = "in.macro.prices.wpi_all"
CPI = "in.macro.prices.cpi_headline"
REPO = "in.macro.monetary.repo_rate"
CREDIT = "in.macro.monetary.bank_credit_growth"
IIP = "in.macro.real.iip_growth"


def test_graph_type_and_counts():
    assert isinstance(graph_engine.graph, nx.MultiDiGraph)
    assert graph_engine.graph.number_of_nodes() == 20
    assert graph_engine.graph.number_of_edges() == 12
    assert graph_engine.graph.nodes[BRENT]["sector"] == "prices_inflation"


def test_brent_to_gdp_is_six_hops_in_order():
    path = graph_engine.get_shortest_transmission_path(BRENT, GDP)
    assert len(path) == 6
    chain = [path[0].source_indicator_id] + [r.target_indicator_id for r in path]
    assert chain == [BRENT, WPI, CPI, REPO, CREDIT, IIP, GDP]


def test_unknown_and_missing_paths_return_empty():
    assert graph_engine.get_shortest_transmission_path("foo", GDP) == []
    assert graph_engine.get_shortest_transmission_path(BRENT, "bar") == []
    assert graph_engine.get_shortest_transmission_path(GDP, BRENT) == []


def test_parallel_edges_pick_highest_confidence():
    onto = MacroeconomicOntology()
    extra = CausalRelationship(
        source_indicator_id=BRENT, target_indicator_id=WPI,
        relation_type=CausalRelationType.THEORY, elasticity_sign="+", confidence_score=0.99,
        mechanism_description="Alternative parallel mechanism.", documented_assumptions=["test"],
    )
    onto.relationships.append(extra)
    engine = NetworkXGraphEngine(onto)
    assert engine.graph.number_of_edges() == 13
    assert engine.get_shortest_transmission_path(BRENT, WPI)[0].relation_id == extra.relation_id


def test_impacts_contract_and_sorting():
    impacts = graph_engine.get_downstream_impacts(BRENT)
    ids = {i["target_indicator_id"] for i in impacts}
    assert {CPI, REPO, "in.macro.external.usd_inr"} <= ids
    keys = [(i["path_length_hops"], -i["cumulative_confidence"]) for i in impacts]
    assert keys == sorted(keys)
    gdp = next(i for i in impacts if i["target_indicator_id"] == GDP)
    path = graph_engine.get_shortest_transmission_path(BRENT, GDP)
    expected = 1.0
    for r in path:
        expected *= r.confidence_score
    assert gdp["cumulative_confidence"] == round(expected, 2)
    assert gdp["total_lag_months"] == sum(r.transmission_lag_months for r in path)
    assert gdp["transmission_chain"] == [r.mechanism_description for r in path]
    assert set(gdp) == {
        "target_indicator_id", "target_name", "sector", "path_length_hops",
        "total_lag_months", "cumulative_confidence", "transmission_chain",
    }


def test_impacts_unknown_node():
    assert graph_engine.get_downstream_impacts("foo") == []


def test_neighborhood_shape_known_and_unknown():
    unknown = graph_engine.get_causal_neighborhood("foo")
    assert unknown == {
        "indicator_id": "foo", "upstream": [], "downstream": [], "upstream_drivers": [], "downstream_impacts": [],
    }
    known = graph_engine.get_causal_neighborhood(CPI)
    assert set(known) == set(unknown)
    assert [r["source_indicator_id"] for r in known["upstream"]] == [WPI]
    assert [r["target_indicator_id"] for r in known["downstream"]] == [REPO]


def test_mermaid_full_and_focus():
    full = graph_engine.generate_mermaid_diagram()
    assert full.startswith("graph LR")
    focused = graph_engine.generate_mermaid_diagram([CPI])
    assert focused.startswith("graph LR")
    assert "in_macro_prices_wpi_all" in focused and "in_macro_monetary_repo_rate" in focused
    assert "in_macro_real_gdp_growth" not in focused
    assert '-->|"+ (2M) [GRANGER_PREDICTIVE]"|' in focused
