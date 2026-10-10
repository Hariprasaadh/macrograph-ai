"""Idea 5: rolling z-score anomalies classified against the causal graph."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from ..knowledge_graph.networkx_engine import graph_engine
from .series_provider import EXTRA_IDS, all_series

WINDOW = 12
MIN_N = 8
Z_THRESHOLD = 2.0


def zscore(values: List[float]) -> Optional[float]:
    """z of the latest point against the trailing window, latest excluded from its own baseline."""
    n = len(values)
    if n < MIN_N:
        return None
    window = min(WINDOW, n - 1)
    base = values[-window - 1:-1]
    mean = sum(base) / len(base)
    sd = (sum((x - mean) ** 2 for x in base) / len(base)) ** 0.5
    if sd == 0:
        return None
    return (values[-1] - mean) / sd


def _name(indicator_id: str) -> str:
    if graph_engine.has_node(indicator_id):
        return graph_engine.graph.nodes[indicator_id].get("name", indicator_id)
    return EXTRA_IDS.get(indicator_id, indicator_id)


def _edge_lag(a: str, b: str) -> int:
    data = graph_engine.graph.get_edge_data(a, b) or {}
    return next((int(v.get("lag_months", 0)) for v in data.values()), 0)


def _neighbors(indicator_id: str) -> List[Dict[str, Any]]:
    graph = graph_engine.graph
    out = [{"id": p, "direction": "upstream", "lag_months": _edge_lag(p, indicator_id)}
           for p in graph.predecessors(indicator_id)]
    out += [{"id": s, "direction": "downstream", "lag_months": _edge_lag(indicator_id, s)}
            for s in graph.successors(indicator_id)]
    return out


def scan(inject: Optional[str] = None) -> Dict[str, Any]:
    series = all_series()
    sim_id: Optional[str] = None
    sim_note: Optional[str] = None
    if inject:
        try:
            inj_id, inj_z = inject.rsplit(":", 1)
            inj_z = float(inj_z)
            values = [v for _, v in series.get(inj_id, [])]
            if len(values) >= MIN_N:
                base = values[-WINDOW:]
                mean = sum(base) / len(base)
                sd = (sum((x - mean) ** 2 for x in base) / len(base)) ** 0.5 or 1.0
                series[inj_id] = series[inj_id] + [("SIM", mean + inj_z * sd)]
                sim_id = inj_id
            else:
                sim_note = f"cannot inject into {inj_id}: fewer than {MIN_N} points"
        except ValueError:
            sim_note = "inject must look like indicator_id:z"

    zmap: Dict[str, float] = {}
    skipped: List[Dict[str, Any]] = []
    for indicator_id, pairs in series.items():
        z = zscore([v for _, v in pairs])
        if z is None:
            skipped.append({"indicator_id": indicator_id, "reason": f"n<{MIN_N} or zero variance", "n": len(pairs)})
        else:
            zmap[indicator_id] = z

    items: List[Dict[str, Any]] = []
    for indicator_id, z in zmap.items():
        if abs(z) <= Z_THRESHOLD:
            continue
        in_graph = graph_engine.has_node(indicator_id)
        neighbors = _neighbors(indicator_id) if in_graph else []
        with_data = [dict(n, z=round(zmap[n["id"]], 3)) for n in neighbors if n["id"] in zmap]
        anomalous = [n for n in with_data if abs(n["z"]) > Z_THRESHOLD]
        culprit: List[str] = []
        if not with_data:
            klass, score = "UNLINKED", None
        elif anomalous:
            klass, score = "PROPAGATING", round(len(anomalous) / len(with_data), 3)
            for n in anomalous:
                path = (graph_engine.get_shortest_transmission_path(n["id"], indicator_id)
                        if n["direction"] == "upstream"
                        else graph_engine.get_shortest_transmission_path(indicator_id, n["id"]))
                culprit += [r.relation_id for r in path]
        else:
            klass, score = "ISOLATED", 0.0
        expected = [{"id": i["target_indicator_id"], "name": i["target_name"], "lag_months": i["total_lag_months"],
                     "confidence": i["cumulative_confidence"]}
                    for i in graph_engine.get_downstream_impacts(indicator_id)[:6]] if in_graph else []
        is_sim = indicator_id == sim_id
        items.append({
            "indicator_id": indicator_id, "name": _name(indicator_id), "z": round(z, 3),
            "period": series[indicator_id][-1][0], "class": klass, "propagation_score": score,
            "culprit_path": list(dict.fromkeys(culprit)), "neighbors": with_data,
            "expected_propagation": expected, "in_graph": in_graph,
            "freshness": "sim" if is_sim else "cached",
            "labels": {"data": "SIM" if is_sim else "CACHED"},
            "trust": "ok" if klass == "PROPAGATING" else "LOW - verify source",
        })
    items.sort(key=lambda r: -abs(r["z"]))
    return {"as_of": date.today().isoformat(), "window": WINDOW, "min_points": MIN_N, "threshold": Z_THRESHOLD,
            "scanned": len(series), "items": items, "skipped": skipped,
            "sim_injected": sim_id, "note": sim_note}
