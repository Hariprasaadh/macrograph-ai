"""Idea 6: model-grounded provenance card built from a finished orchestrator state."""
from __future__ import annotations

from typing import Any, Dict, List

from ..knowledge_graph.networkx_engine import graph_engine
from . import ATTENUATION, BAND, SCALE, UNUSABLE_STATUSES
from .edge_audit import audit_map
from .trajectory import path_multiplier

CPI_ID = "in.macro.prices.cpi_headline"


def _formula(scenario: Dict[str, Any]) -> Dict[str, Any]:
    shock_var = scenario.get("shock_variable")
    magnitude = scenario.get("shock_magnitude")
    for target, impact in (scenario.get("forecasted_impacts") or {}).items():
        if target == shock_var:
            continue
        relations = graph_engine.get_shortest_transmission_path(shock_var, target)
        if not relations:
            continue
        hops = " x ".join(f"({'-' if r.elasticity_sign == '-' else ''}{ATTENUATION}*{r.confidence_score})" for r in relations)
        value = round(float(magnitude) * path_multiplier(relations) * SCALE, 2)
        return {"target": target, "text": f"{magnitude} x {hops} x {SCALE} = {value:+}", "value": value}
    return {}


def build_model_card(state: Dict[str, Any]) -> Dict[str, Any]:
    observations: List[Dict[str, Any]] = state.get("collected_observations") or []
    paths: List[Dict[str, Any]] = state.get("causal_paths") or []
    scenario = state.get("scenario_result")
    trace = state.get("a2a_trace") or []
    live_ids = list(state.get("live_baseline_ids") or [])

    live = sourced = unavailable = 0
    for obs in observations:
        status = obs.get("data_status")
        if status in UNUSABLE_STATUSES:
            unavailable += 1
        elif "live" in str(status).lower():
            live += 1
        else:
            sourced += 1
    total = len(observations)
    evidence_cover = ((live + sourced) / total) if total else 0.0

    relation_ids: List[str] = []
    confidences: List[float] = []
    for path in paths:
        for rel in path.get("relations", []):
            if rel.get("relation_id") not in relation_ids:
                relation_ids.append(rel.get("relation_id"))
                confidences.append(float(rel.get("confidence_score", 0.0)))
    for rid in (scenario or {}).get("provenance_chain", []):
        if rid not in relation_ids:
            relation_ids.append(rid)
    audit = audit_map()
    edges = [{"relation_id": rid, "evidence_class": audit.get(rid, {}).get("evidence_class", "SEEDED"),
              "seeded_p": audit.get(rid, {}).get("seeded_p")} for rid in relation_ids]
    mean_conf = (sum(confidences) / len(confidences)) if confidences else 0.0

    root = [n for n in trace if n.get("sender_agent") == "orchestrator"] or trace
    agent_success = (sum({"success": 1.0, "partial": 0.5}.get(n.get("status"), 0.0) for n in root) / len(root)) if root else 0.0
    trust = round(0.4 * evidence_cover + 0.3 * mean_conf + 0.3 * agent_success, 3)

    regime: List[str] = []
    for obs in observations:
        if obs.get("indicator_id") == CPI_ID and isinstance(obs.get("value"), (int, float)):
            cpi = float(obs["value"])
            band = "inside" if 2 <= cpi <= 6 else ("above" if cpi > 6 else "below")
            regime.append(f"CPI {cpi:g}% is {band} the 2-6% inflation-target band")
            break

    model: Dict[str, Any]
    if scenario:
        model = {"name": "graph-attenuation v1", "kind": "SIM", "scenario": scenario.get("scenario_name"),
                 "constants": {"attenuation": ATTENUATION, "scale": SCALE, "band": BAND},
                 "formula": _formula(scenario),
                 "baseline": "live for " + ", ".join(live_ids) if live_ids else "default (no live match)"}
    else:
        model = {"name": "none", "kind": "none"}

    return {
        "evidence": {"live": live, "sourced": sourced, "unavailable": unavailable, "total": total},
        "kg": {"paths": len(paths), "max_hops": max((p.get("hops", 0) for p in paths), default=0),
               "relations": edges},
        "model": model,
        "trust": {"score": trust, "label": "heuristic",
                  "parts": {"evidence_cover": round(evidence_cover, 3), "mean_edge_confidence": round(mean_conf, 3),
                            "agent_success": round(agent_success, 3)}},
        "regime": regime,
    }
