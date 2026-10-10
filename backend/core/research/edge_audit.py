"""Edge Evidence Audit: SEEDED (typed into the ontology) vs EMPIRICAL (Granger on real series)."""
from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from ..econometrics.causal_engine import causal_engine
from ..knowledge_graph.networkx_engine import graph_engine
from .series_provider import get_series

_MONTH = re.compile(r"^(\d{4})-(\d{2})")
_MIN_OVERLAP = 10
_TTL_SECONDS = 300
_cache: Dict[str, Any] = {"t": 0.0, "rows": None}
_lock = threading.Lock()

# Warnings attached to edges that need a human review (see blueprint finding P1).
EDGE_NOTES: Dict[tuple, str] = {
    ("in.macro.external.trade_balance", "in.macro.external.usd_inr"):
        "sign under review: mechanism says a wider deficit weakens INR but the edge sign is '+'",
}


def edge_note(source: str, target: str) -> Optional[str]:
    return EDGE_NOTES.get((source, target))


def _by_month(series: Optional[List[tuple]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for period, value in series or []:
        match = _MONTH.match(str(period))
        if match:
            out[f"{match.group(1)}-{match.group(2)}"] = float(value)
    return out


def _audit_one(rel: Any) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "relation_id": rel.relation_id,
        "source": rel.source_indicator_id,
        "target": rel.target_indicator_id,
        "relation_type": rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type),
        "lag_months": rel.transmission_lag_months,
        "confidence": rel.confidence_score,
        "sign": rel.elasticity_sign,
        "seeded_p": rel.empirical_p_value,
        "evidence_class": "SEEDED",
        "status": "UNTESTABLE_NO_DATA",
        "n": 0,
        "empirical": None,
        "note": edge_note(rel.source_indicator_id, rel.target_indicator_id),
    }
    src = _by_month(get_series(rel.source_indicator_id))
    tgt = _by_month(get_series(rel.target_indicator_id))
    if not src or not tgt:
        return row
    months = sorted(set(src) & set(tgt))
    row["n"] = len(months)
    if len(months) < _MIN_OVERLAP:
        row["status"] = "UNTESTABLE_N"
        return row
    frame = pd.DataFrame({"cause": [src[m] for m in months], "effect": [tgt[m] for m in months]})
    result = causal_engine.test_granger_causality(frame, "cause", "effect")
    if result.get("p_value") is None:
        row["status"] = "UNTESTABLE_N"
        return row
    row["status"] = "EMPIRICAL"
    row["evidence_class"] = "EMPIRICAL"
    row["empirical"] = {k: result.get(k) for k in ("p_value", "optimal_lag", "is_significant")}
    return row


def audit_edges() -> List[Dict[str, Any]]:
    with _lock:
        if _cache["rows"] is None or time.time() - _cache["t"] > _TTL_SECONDS:
            _cache["rows"] = [_audit_one(rel) for rel in graph_engine.ontology.relationships]
            _cache["t"] = time.time()
        return _cache["rows"]


def audit_map() -> Dict[str, Dict[str, Any]]:
    try:
        return {row["relation_id"]: row for row in audit_edges()}
    except Exception:  # noqa: BLE001 - audit is decorative; never block a caller
        return {}
