"""Idea 1: expand one simulate_scenario result into monthly series (default: step at the engine lag)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..econometrics.causal_engine import causal_engine
from ..knowledge_graph.networkx_engine import graph_engine
from . import ATTENUATION
from .edge_audit import audit_map, edge_note


def path_multiplier(relations: List[Any]) -> float:
    mult = 1.0
    for rel in relations:
        sign = 1.0 if rel.elasticity_sign == "+" else -1.0
        mult *= sign * ATTENUATION * rel.confidence_score
    return mult


def _node_meta(node_id: str) -> Dict[str, str]:
    data = graph_engine.graph.nodes[node_id] if graph_engine.has_node(node_id) else {}
    return {"name": data.get("name", node_id), "sector": data.get("sector", "")}


def _series(baseline: float, delta: float, lag: int, horizon: int, shape: str,
            half_life: Optional[float]) -> List[Dict[str, float]]:
    points: List[Dict[str, float]] = []
    for t in range(horizon + 1):
        if t < lag:
            value = baseline
        elif shape == "decay" and half_life and half_life > 0:
            value = baseline + delta * (0.5 ** ((t - lag) / half_life))
        else:
            value = baseline + delta
        points.append({"t": t, "value": round(value, 4)})
    return points


def build_trajectory(shock_variable: str, shock_magnitude: float, horizon_months: int = 12,
                     shape: str = "step", half_life_months: Optional[float] = None) -> Dict[str, Any]:
    horizon = max(1, min(int(horizon_months), 60))
    shape = shape if shape in ("step", "decay") else "step"
    notes = ["Deltas are in each indicator's own unit; model scaling is unit-blind.",
             "Heuristic graph-attenuation model; the +/-25% band is not a statistical CI."]
    if not graph_engine.has_node(shock_variable):
        return {"shock": {"id": shock_variable, "magnitude": shock_magnitude, "baseline_source": "DEFAULT"},
                "horizon_months": horizon, "nodes": [], "edges": [],
                "notes": notes + ["Shock variable is not in the knowledge graph: no downstream channels."],
                "labels": {"data": "SIM", "shape": shape}}

    result = causal_engine.simulate_scenario("Research trajectory", shock_variable, float(shock_magnitude))
    forecasts = result.forecasted_impacts
    audit = audit_map()
    nodes: List[Dict[str, Any]] = []
    edges: Dict[str, Dict[str, Any]] = {}

    shock_fc = forecasts.get(shock_variable, {})
    base0 = float(shock_fc.get("baseline", 0.0))
    nodes.append({**_node_meta(shock_variable), "id": shock_variable, "hops": 0, "lag_months": 0,
                  "cum_confidence": 1.0, "cum_multiplier": 1.0, "baseline": base0,
                  "delta_peak": float(shock_magnitude),
                  "delta_pct_of_baseline": round(shock_magnitude / abs(base0) * 100, 2) if base0 else None,
                  "series": _series(base0, float(shock_magnitude), 0, horizon, shape, half_life_months)})

    for impact in graph_engine.get_downstream_impacts(shock_variable):
        target = impact["target_indicator_id"]
        forecast = forecasts.get(target)
        relations = graph_engine.get_shortest_transmission_path(shock_variable, target)
        if not forecast or not relations:
            continue
        baseline = float(forecast["baseline"])
        delta = float(forecast["delta"])
        lag = int(impact["total_lag_months"])
        nodes.append({
            **_node_meta(target), "id": target, "hops": impact["path_length_hops"], "lag_months": lag,
            "cum_confidence": impact["cumulative_confidence"], "cum_multiplier": round(path_multiplier(relations), 6),
            "baseline": baseline, "delta_peak": delta,
            "delta_pct_of_baseline": round(delta / abs(baseline) * 100, 4) if baseline else None,
            "series": _series(baseline, delta, lag, horizon, shape, half_life_months),
        })
        for rel in relations:
            if rel.relation_id in edges:
                continue
            row = audit.get(rel.relation_id, {})
            edges[rel.relation_id] = {
                "relation_id": rel.relation_id, "from": rel.source_indicator_id, "to": rel.target_indicator_id,
                "lag_months": rel.transmission_lag_months, "confidence": rel.confidence_score,
                "sign": rel.elasticity_sign, "type": rel.relation_type.value,
                "mechanism": rel.mechanism_description,
                "evidence_class": row.get("evidence_class", "SEEDED"), "seeded_p": rel.empirical_p_value,
                "note": edge_note(rel.source_indicator_id, rel.target_indicator_id),
            }

    return {"shock": {"id": shock_variable, "magnitude": shock_magnitude, "baseline_source": "DEFAULT"},
            "horizon_months": horizon, "nodes": nodes, "edges": list(edges.values()),
            "notes": notes, "labels": {"data": "SIM", "shape": shape}}
