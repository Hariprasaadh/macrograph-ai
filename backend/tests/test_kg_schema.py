"""Schema and ontology validation for the macroeconomic knowledge graph."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.data.schema import CanonicalIndicator, CausalRelationship, CausalRelationType, SectorEnum
from core.knowledge_graph.ontology import MacroeconomicOntology, ontology

SRC = "in.macro.prices.brent_crude"
TGT = "in.macro.prices.wpi_all"


def make_indicator(**overrides):
    base = dict(
        indicator_id=SRC, name="Brent", sector=SectorEnum.PRICES_INFLATION,
        unit="USD/barrel", frequency="daily", source_authority="EIA",
    )
    base.update(overrides)
    return CanonicalIndicator(**base)


def make_relation(**overrides):
    base = dict(
        source_indicator_id=SRC, target_indicator_id=TGT,
        relation_type=CausalRelationType.LAGGED_RELATIONSHIP, transmission_lag_months=1,
        elasticity_sign="+", empirical_p_value=0.01, confidence_score=0.9,
        mechanism_description="Crude passes into input costs.", documented_assumptions=["Taxes constant"],
    )
    base.update(overrides)
    return CausalRelationship(**base)


def test_valid_indicator():
    assert make_indicator().indicator_id == SRC


@pytest.mark.parametrize("bad_id", ["cpi", "in.macro.prices", "IN.macro.prices.cpi", "in.macro.Prices.cpi"])
def test_invalid_indicator_id(bad_id):
    with pytest.raises(ValidationError):
        make_indicator(indicator_id=bad_id)


def test_invalid_frequency():
    with pytest.raises(ValidationError):
        make_indicator(frequency="Monthly")


@pytest.mark.parametrize("sign", ["ambiguous", "positive", "", "+-"])
def test_invalid_sign(sign):
    with pytest.raises(ValidationError):
        make_relation(elasticity_sign=sign)


def test_negative_lag():
    with pytest.raises(ValidationError):
        make_relation(transmission_lag_months=-1)


@pytest.mark.parametrize("conf", [-0.1, 1.1])
def test_invalid_confidence(conf):
    with pytest.raises(ValidationError):
        make_relation(confidence_score=conf)


def test_short_mechanism():
    with pytest.raises(ValidationError):
        make_relation(mechanism_description="short")


@pytest.mark.parametrize("assumptions", [[], [" "]])
def test_empty_assumptions(assumptions):
    with pytest.raises(ValidationError):
        make_relation(documented_assumptions=assumptions)


def test_self_loop_rejected():
    with pytest.raises(ValidationError):
        make_relation(target_indicator_id=SRC)


def test_p_value_none_only_for_theory():
    assert make_relation(relation_type=CausalRelationType.THEORY, empirical_p_value=None)
    with pytest.raises(ValidationError):
        make_relation(empirical_p_value=None)


def test_default_relation_id_format():
    assert make_relation().relation_id.startswith("rel-")
    assert len(make_relation().relation_id) == 12


def test_unknown_endpoint_rejected_by_ontology():
    onto = MacroeconomicOntology()
    onto.relationships.append(make_relation(target_indicator_id="in.macro.prices.unknown_thing"))
    with pytest.raises(ValueError, match="unknown indicator"):
        onto.validate()


def test_seed_ontology_contents_and_stable_ids():
    assert len(ontology.indicators) == 20
    assert len(ontology.relationships) == 12
    again = MacroeconomicOntology()
    assert [r.relation_id for r in again.relationships] == [r.relation_id for r in ontology.relationships]
    assert len({r.relation_id for r in ontology.relationships}) == 12
