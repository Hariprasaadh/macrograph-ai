"""Maps KG indicator ids to the histories that already exist in the dashboard helpers (no new SQL)."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

Series = List[Tuple[str, float]]
_TTL_SECONDS = 300
_cache: Dict[str, Any] = {"t": 0.0, "data": None}
_lock = threading.Lock()

# Non-KG series that can still be z-scored (they become UNLINKED in the radar).
EXTRA_IDS = {
    "in.macro.fiscal.gst_collections": "Gross GST Collections",
    "in.macro.capmarkets.gsec_10y": "10Y G-Sec Yield",
    "in.macro.labour.unemployment_rate": "Unemployment Rate",
}


def _num(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pairs(rows: Any, key: str, scale: float = 1.0) -> Series:
    out: Series = []
    for row in rows or []:
        value = _num(row.get(key))
        period = row.get("period")
        if value is None or period is None:
            continue
        out.append((str(period), value * scale))
    return out


def _load() -> Dict[str, Series]:
    from api import dashboard_helpers as dh

    data: Dict[str, Series] = {}

    def put(indicator_id: str, series: Series) -> None:
        if series:
            data[indicator_id] = series

    try:
        ext = dh.query_external_telemetry()
        put("in.macro.external.usd_inr", _pairs(ext.get("fx_history"), "usd_inr_rate"))
        put("in.macro.external.forex_reserves", _pairs(ext.get("reserves_history"), "total_reserves_usd_mn", 0.001))
        # Dashboard stores deficit = imports - exports (positive); the KG node is exports - imports.
        put("in.macro.external.trade_balance", _pairs(ext.get("trade_history"), "trade_deficit_usd_bn", -1.0))
    except Exception:  # noqa: BLE001
        logger.exception("external series unavailable")
    try:
        fin = dh.query_finance_telemetry()
        put("in.macro.monetary.bank_credit_growth",
            _pairs(fin.get("timeseries", {}).get("credit"), "non_food_credit_yoy_pct"))
    except Exception:  # noqa: BLE001
        logger.exception("finance series unavailable")
    try:
        cap = dh.query_capmarkets_telemetry()
        put("in.macro.capmarkets.india_vix", _pairs(cap.get("vix_history"), "vix_close"))
        put("in.macro.capmarkets.gsec_10y", _pairs(cap.get("gsec_history"), "ten_year_gsec_yield_pct"))
    except Exception:  # noqa: BLE001
        logger.exception("capital markets series unavailable")
    try:
        fisc = dh.query_fiscal_telemetry()
        put("in.macro.fiscal.gst_collections", _pairs(fisc.get("gst_history"), "gross_gst_cr"))
    except Exception:  # noqa: BLE001
        logger.exception("fiscal series unavailable")
    try:
        lab = dh.query_labour_telemetry()
        put("in.macro.labour.unemployment_rate", _pairs(lab.get("unemp_history"), "unemployment_rate_pct"))
    except Exception:  # noqa: BLE001
        logger.exception("labour series unavailable")
    return data


def _macro_store_series(indicator_id: str) -> Series:
    try:
        from core.database.macro_store import macro_store

        df = macro_store.get_canonical_series(indicator_id)
        return [(str(r.date), float(r.value)) for r in df.itertuples() if r.value is not None]
    except Exception:  # noqa: BLE001
        return []


def _snapshot() -> Dict[str, Series]:
    with _lock:
        if _cache["data"] is None or time.time() - _cache["t"] > _TTL_SECONDS:
            _cache["data"] = _load()
            _cache["t"] = time.time()
        return _cache["data"]


def get_series(indicator_id: str) -> Optional[Series]:
    series = _snapshot().get(indicator_id)
    if series:
        return list(series)
    fallback = _macro_store_series(indicator_id)
    return fallback or None


def all_series() -> Dict[str, Series]:
    """Every series known to the lab, including sparse macro_store fallbacks for KG nodes."""
    from core.knowledge_graph.networkx_engine import graph_engine

    merged = {k: list(v) for k, v in _snapshot().items()}
    for node_id in graph_engine.graph.nodes:
        if node_id not in merged:
            fallback = _macro_store_series(node_id)
            if fallback:
                merged[node_id] = fallback
    return merged
