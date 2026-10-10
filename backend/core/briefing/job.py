"""Daily brief pipeline: telemetry + anomaly scan + cached news + ONE LLM call, with a deterministic fallback."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ..config import settings
from ..knowledge_graph.networkx_engine import graph_engine
from ..research.anomaly import scan
from . import store

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
_NEWS_QUERIES = {
    "Monetary": "RBI monetary policy repo rate India latest",
    "Fiscal": "India GST collections fiscal deficit latest",
    "External": "India rupee forex reserves trade deficit latest",
    "Markets": "India stock market Nifty bond yield latest",
}


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def _latest(rows: Any, key: str) -> Optional[Dict[str, Any]]:
    rows = rows or []
    return rows[-1] if rows and rows[-1].get(key) is not None else None


def _telemetry() -> Dict[str, Any]:
    from api import dashboard_helpers as dh

    out: Dict[str, Any] = {}
    for name, fn in (("monetary", dh.query_monetary_telemetry), ("fiscal", dh.query_fiscal_telemetry),
                     ("external", dh.query_external_telemetry), ("markets", dh.query_capmarkets_telemetry)):
        try:
            out[name] = fn()
        except Exception:  # noqa: BLE001
            logger.exception("brief telemetry %s failed", name)
            out[name] = {}
    return out


def _pillars(tel: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    flagged = {a["indicator_id"] for a in anomalies}
    rates = (tel["monetary"] or {}).get("latest_rates")
    gst = (tel["fiscal"] or {}).get("latest_gst")
    deficit = (tel["fiscal"] or {}).get("latest_deficit")
    fx = (tel["external"] or {}).get("latest_fx")
    reserves = (tel["external"] or {}).get("latest_reserves")
    vix = (tel["markets"] or {}).get("latest_vix")
    gsec = (tel["markets"] or {}).get("latest_gsec")

    def stance(has_data: bool, ids: List[str]) -> str:
        if not has_data:
            return "Unavailable"
        return "Watch" if flagged.intersection(ids) else "Stable"

    return [
        {"pillar": "Monetary", "stance": stance(bool(rates), []),
         "takeaway": f"Repo rate {rates['repo_rate_pct']}% (period {rates['period']})." if rates else "Policy rate data unavailable."},
        {"pillar": "Fiscal", "stance": stance(bool(gst or deficit), ["in.macro.fiscal.gst_collections"]),
         "takeaway": (f"Gross GST Rs {gst['gross_gst_cr']:,.0f} Cr (period {gst['period']})" if gst else "GST data unavailable")
                     + (f"; fiscal deficit {deficit['fiscal_deficit_gdp_pct']}% of GDP (period {deficit['period']})." if deficit else ".")},
        {"pillar": "External", "stance": stance(bool(fx or reserves), ["in.macro.external.usd_inr", "in.macro.external.trade_balance",
                                                                       "in.macro.external.forex_reserves"]),
         "takeaway": (f"USD/INR {fx['usd_inr_rate']:.2f} (period {fx['period']})" if fx else "USD/INR unavailable")
                     + (f"; reserves ${reserves['total_reserves_usd_mn'] / 1000:.1f} Bn (period {reserves['period']})." if reserves else ".")},
        {"pillar": "Markets", "stance": stance(bool(vix or gsec), ["in.macro.capmarkets.india_vix", "in.macro.capmarkets.gsec_10y"]),
         "takeaway": (f"India VIX {vix['vix_close']} (period {vix['period']})" if vix else "VIX unavailable")
                     + (f"; 10Y G-Sec {gsec['ten_year_gsec_yield_pct']}% (period {gsec['period']})." if gsec else ".")},
    ]


def _warnings(anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for a in anomalies[:6]:
        path = [graph_engine.graph.nodes[n["id"]].get("name", n["id"]) for n in a.get("neighbors", [])
                if abs(n.get("z", 0)) > 2 and graph_engine.has_node(n["id"])]
        out.append({
            "title": f"{a['name']} z={a['z']:+.1f} ({a['class']})",
            "severity": "WATCH" if a["class"] == "PROPAGATING" else "INFO",
            "causal_path": path + [a["name"]] if path else [a["name"]],
            "action": "Open the Anomaly Radar and verify the source table." if a["class"] != "PROPAGATING"
                      else "Neighbouring indicators moved too: treat as a real shock and review downstream impacts.",
            "indicator_id": a["indicator_id"], "period": a["period"],
        })
    return out


async def _news(provenance: Dict[str, Any]) -> Dict[str, Any]:
    news: Dict[str, Any] = {}
    try:
        from external_sector.tavily_client import fetch_realtime_intelligence
    except Exception:  # noqa: BLE001
        provenance["news_status"] = "unavailable"
        return news
    live = cached = failed = 0
    for pillar, query in _NEWS_QUERIES.items():
        key = hashlib.sha256(query.encode()).hexdigest()[:16]
        hit = await asyncio.to_thread(store.cached_news_get, key)
        if hit is not None:
            news[pillar], cached = hit, cached + 1
            continue
        try:
            rec = await fetch_realtime_intelligence(query=query, max_results=5)
            payload = {"summary": rec.summary, "titles": [i.get("title") for i in rec.news_items if isinstance(i, dict)][:5],
                       "urls": list(rec.source_urls[:3])}
            await asyncio.to_thread(store.cached_news_set, key, payload)
            news[pillar], live = payload, live + 1
        except Exception:  # noqa: BLE001
            failed += 1
    provenance["news_status"] = "unavailable" if (not news) else "ok"
    provenance["news_counts"] = {"live": live, "cached": cached, "failed": failed}
    return news


def _deterministic(pillars: List[Dict[str, str]], warnings: List[Dict[str, Any]]) -> Dict[str, Any]:
    watch = [w["title"] for w in warnings] or ["No statistical anomalies flagged in the available series."]
    movers = [p["pillar"] for p in pillars if p["stance"] == "Watch"]
    return {
        "headline": ("Early-warning brief: " + ", ".join(movers) + " flagged") if movers else "Early-warning brief: no pillar flagged",
        "executive_summary": " ".join(p["takeaway"] for p in pillars),
        "watch_today": watch,
    }


async def _llm_synthesis(pillars: List[Dict[str, str]], warnings: List[Dict[str, Any]],
                         news: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from ..orchestrator.llm_client import llm_client

    if not llm_client._get_api_key():
        return None
    prompt = (
        "Write a short early-warning brief for an Indian macro analyst. Use ONLY the facts below; "
        "if something is missing write 'unavailable'. Cite numbers as [value | period].\n"
        f"PILLARS: {json.dumps(pillars)}\nANOMALIES: {json.dumps(warnings)}\n"
        f"NEWS: {json.dumps({k: v.get('summary') for k, v in news.items()})}\n"
        'Reply with JSON only: {"headline":"...","executive_summary":"...","watch_today":["...","..."]}'
    )
    text = await llm_client.complete(prompt, "You are a careful macroeconomic analyst. Never invent numbers.", False)
    if text == llm_client._unavailable_notice():
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not all(isinstance(data.get(k), str) and data[k] for k in ("headline", "executive_summary")):
        return None
    watch = data.get("watch_today")
    data["watch_today"] = [str(x) for x in watch][:5] if isinstance(watch, list) else []
    return data


async def run_daily_brief(force: bool = False) -> Dict[str, Any]:
    date = today_ist()
    if not force:
        existing = await asyncio.to_thread(store.get_brief, date)
        if existing:
            return existing
    tel = await asyncio.to_thread(_telemetry)
    radar = await asyncio.to_thread(scan, None)
    anomalies = radar["items"]
    pillars = _pillars(tel, anomalies)
    warnings = _warnings(anomalies)
    provenance: Dict[str, Any] = {"mode": "deterministic", "scanned_series": radar["scanned"],
                                  "tavily_cap": len(_NEWS_QUERIES), "labels": {"data": "CACHED"}}
    news = await _news(provenance)
    synthesis = None
    try:
        synthesis = await _llm_synthesis(pillars, warnings, news)
    except Exception:  # noqa: BLE001
        logger.exception("brief LLM synthesis failed; using deterministic template")
    if synthesis:
        provenance["mode"] = "llm"
    body = synthesis or _deterministic(pillars, warnings)
    provenance["counts"] = {"available": sum(1 for p in pillars if p["stance"] != "Unavailable"),
                            "unavailable": sum(1 for p in pillars if p["stance"] == "Unavailable")}
    brief = {"date": date, "headline": body["headline"], "executive_summary": body["executive_summary"],
             "key_drivers": pillars, "warnings": warnings, "watch_today": body["watch_today"],
             "provenance": provenance, "llm_model": settings.FAST_MODEL if synthesis else "",
             "created_at": datetime.now(timezone.utc).isoformat()}
    await asyncio.to_thread(store.save_brief, brief)
    return brief


async def brief_cron_loop() -> None:
    """Sleeps until the next 08:15 Asia/Kolkata and runs the brief; started only when BRIEF_CRON_ENABLED=true."""
    while True:
        now = datetime.now(IST)
        target = now.replace(hour=8, minute=15, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await run_daily_brief(force=True)
        except Exception:  # noqa: BLE001
            logger.exception("scheduled brief failed")
