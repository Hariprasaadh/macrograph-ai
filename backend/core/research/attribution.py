"""Idea 3: base vs shocked world with per-hop log-attenuation attribution."""
from __future__ import annotations

import math
from typing import Any, Dict, List

from ..econometrics.causal_engine import causal_engine
from ..knowledge_graph.networkx_engine import graph_engine
from . import ATTENUATION, SCALE
from .edge_audit import edge_note
from .trajectory import path_multiplier


def _shares(relations: List[Any]) -> List[float]:
    logs = [math.log(max(abs(ATTENUATION * rel.confidence_score), 1e-9)) for rel in relations]
    total = sum(logs)
    if total == 0:
        return [1.0 / len(relations)] * len(relations) if relations else []
    return [round(value / total, 6) for value in logs]


def compare(shock_variable: str, shock_magnitude: float) -> Dict[str, Any]:
    base_res = causal_engine.simulate_scenario("Twin baseline", shock_variable, 0.0)
    shocked_res = causal_engine.simulate_scenario("Twin shocked", shock_variable, float(shock_magnitude))
    lags = {i["target_indicator_id"]: i["total_lag_months"] for i in graph_engine.get_downstream_impacts(shock_variable)}

    base: Dict[str, float] = {}
    shocked: Dict[str, float] = {}
    delta: Dict[str, float] = {}
    gain: Dict[str, float] = {}
    pct: Dict[str, float] = {}
    attribution: Dict[str, Any] = {}
    names: Dict[str, str] = {}

    for node_id, forecast in shocked_res.forecasted_impacts.items():
        base_fc = base_res.forecasted_impacts.get(node_id, {})
        baseline = float(base_fc.get("baseline", forecast.get("baseline", 0.0)))
        is_shock = node_id == shock_variable
        shocked_value = forecast["shocked_period_1"] if is_shock else forecast["shocked_peak"]
        base[node_id] = baseline
        shocked[node_id] = shocked_value
        delta[node_id] = forecast["delta"]
        names[node_id] = graph_engine.graph.nodes[node_id].get("name", node_id) if graph_engine.has_node(node_id) else node_id
        if is_shock:
            gain[node_id] = 1.0
        else:
            relations = graph_engine.get_shortest_transmission_path(shock_variable, node_id)
            gain[node_id] = path_multiplier(relations) * SCALE
            shares = _shares(relations)
            attribution[node_id] = {
                "path": [r.relation_id for r in relations],
                "edges": [{"relation_id": r.relation_id, "from": r.source_indicator_id, "to": r.target_indicator_id,
                           "sign": r.elasticity_sign, "confidence": r.confidence_score, "lag_months": r.transmission_lag_months,
                           "note": edge_note(r.source_indicator_id, r.target_indicator_id)} for r in relations],
                "share": shares,
                "sign_flips": sum(1 for r in relations if r.elasticity_sign == "-"),
                "weakest_link": relations[shares.index(max(shares))].relation_id if relations else None,
            }
        pct[node_id] = round(forecast["delta"] / abs(baseline) * 100, 4) if baseline else 0.0

    return {"shock_variable": shock_variable, "shock_magnitude": shock_magnitude,
            "names": names, "base": base, "shocked": shocked, "delta": delta, "gain_per_unit": gain,
            "lag_months": lags, "pct_of_baseline": pct, "attribution": attribution,
            "labels": {"data": "SIM", "baseline_source": "DEFAULT"}}
