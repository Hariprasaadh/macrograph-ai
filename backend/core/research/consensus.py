"""Idea 2: debate-DAG rollup and heuristic consensus score from a finished orchestrator state."""
from __future__ import annotations

from typing import Any, Dict, List

from ..knowledge_graph.networkx_engine import graph_engine
from . import UNUSABLE_STATUSES

_PREFIX_AGENTS = {
    "real": ["real_sector"], "prices": ["prices_sector"], "monetary": ["monetary_sector", "finance_sector"],
    "fiscal": ["fiscal_sector"], "external": ["external_sector"], "capmarkets": ["capital_market_sector"],
    "agri": ["agriculture_sector"], "labour": ["labour_sector"], "finance": ["finance_sector"],
    "services": ["services_sector"],
}
_STATUS_SCORE = {"success": 1.0, "partial": 0.5}


def _owner(indicator_id: str, routed: List[str]) -> str:
    parts = str(indicator_id).split(".")
    candidates = _PREFIX_AGENTS.get(parts[2], []) if len(parts) > 2 else []
    for agent in candidates:
        if agent in routed:
            return agent
    return candidates[0] if candidates else "unattributed"


def build_consensus(state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("a2a_trace") or []
    observations = state.get("collected_observations") or []
    routed = list(state.get("routed_agents") or [])
    sources = state.get("a2a_sources") or []
    errors = state.get("a2a_errors") or []

    agents: Dict[str, Dict[str, Any]] = {}

    def entry(agent_id: str) -> Dict[str, Any]:
        return agents.setdefault(agent_id, {
            "agent_id": agent_id, "status": "unknown", "duration_ms": None, "observations": 0, "usable": 0,
            "indicators": [], "sources": 0, "errors": [],
        })

    for agent_id in routed:
        entry(agent_id)
    peer_calls = 0
    for node in trace:
        if node.get("sender_agent") == "orchestrator":
            row = entry(node.get("receiver_agent", "unknown"))
            row["status"] = node.get("status", "unknown")
            row["duration_ms"] = node.get("duration_ms")
            row["errors"] += list(node.get("error_codes") or [])
        else:
            peer_calls += 1
    for src in sources:
        entry(src.get("agent", "unknown"))["sources"] += 1
    for err in errors:
        row = entry(err.get("agent", "unknown"))
        if err.get("code") and err["code"] not in row["errors"]:
            row["errors"].append(err["code"])

    usable_total = 0
    for obs in observations:
        owner = _owner(obs.get("indicator_id", ""), routed)
        row = entry(owner)
        row["observations"] += 1
        if obs.get("data_status") not in UNUSABLE_STATUSES:
            row["usable"] += 1
            usable_total += 1
        if obs.get("indicator_id") and obs["indicator_id"] not in row["indicators"]:
            row["indicators"].append(obs["indicator_id"])

    root_nodes = [n for n in trace if n.get("sender_agent") == "orchestrator"] or list(trace)
    agent_success = (sum(_STATUS_SCORE.get(n.get("status"), 0.0) for n in root_nodes) / len(root_nodes)) if root_nodes else 0.0
    evidence_cover = (usable_total / len(observations)) if observations else 0.0

    kg_ids = list(dict.fromkeys(o["indicator_id"] for o in observations
                                if o.get("indicator_id") and graph_engine.has_node(o["indicator_id"])))
    pairs_total = len(kg_ids) * (len(kg_ids) - 1) // 2
    connected = {frozenset((p.get("from"), p.get("to"))) for p in (state.get("causal_paths") or [])}
    kg_cover = (len(connected) / pairs_total) if pairs_total else 0.0
    kg_cover = min(kg_cover, 1.0)

    quality = agent_success * evidence_cover * (0.5 + 0.5 * kg_cover)
    return {
        "agents": list(agents.values()),
        "peer_calls": peer_calls,
        "routing_method": state.get("routing_method"),
        "kg": {"paths": len(state.get("causal_paths") or []), "scenario": bool(state.get("scenario_result")),
               "coverage": round(kg_cover, 3)},
        "scores": {"agent_success": round(agent_success, 3), "evidence_cover": round(evidence_cover, 3),
                   "kg_cover": round(kg_cover, 3), "consensus_quality": round(quality, 3),
                   "confidence_score": state.get("confidence_score")},
        "label": "heuristic",
    }
