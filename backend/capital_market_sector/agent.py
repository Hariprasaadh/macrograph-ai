"""Capital Markets Sector LangGraph Agent Node."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sector_reasoning import (
    record_to_dict,
    reason_over_sector_data,
    select_relevant_services_with_llm,
)
from capital_market_sector import client
from capital_market_sector.config import capital_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Capital Markets Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You ONLY answer queries concerning India's Capital Markets:
  - NIFTY 50 equity index levels and market performance.
  - India VIX volatility index.
  - Market breadth (advances/declines).
  - RBI month-end SGL transaction yields for 10Y, 5Y, and 2Y maturities.

RESPONSE CONTRACT:
- Answer the user's exact question first in one or two concise sentences. Do not
  begin with a generic market overview.
- Follow with an "Observations" table containing only relevant retrieved facts.
  Use columns: Indicator, Observation, Period, Source and freshness. Keep each
  cell short; never put raw JSON, long URLs, or multiple paragraphs in a cell.
- Follow with a compact "Take-aways" table using Insight and Implication.
  Explain what the observed move or spread means, but distinguish evidence from
  interpretation and do not give trading advice.
- Finish with one short limitation only when the data is cached, stale, a
  provider snapshot, partial, or unable to answer the question.
- Do not repeat the same observation in prose and in multiple tables. Do not
  return unrelated datasets just because they are available.

SOURCE AND DATA RULES:
- Cite only provenance present in the supplied records: authority, document or
  table reference, period, and freshness. The UI displays the full source link
  and metadata separately; do not invent, reconstruct, or guess citations.
- Do not present Yahoo Finance as an official NSE feed or a real-time tick.
- Describe RBI G-Sec values as month-end SGL transaction yields, not daily
  benchmark bond closing yields. Do not infer a tenor or spread from missing
  values.
- Label units explicitly (index points, percent, or basis points) and state the
  actual observation period. If a value is missing, say "Unavailable"; never
  render it as zero or calculate with it.
- If relevant records are absent or fail to answer the question, say exactly
  what is unavailable rather than filling gaps from prior knowledge.
"""

_SERVICE_KEYWORDS = {
    "nifty_snapshot": ("nifty", "sensex", "index", "equity index", "market level", "market close"),
    "market_history": ("historical", "history", "returns", "valuation", "p/e", "price earnings", "dividend yield"),
    "india_vix": ("vix", "volatility", "risk regime"),
    "market_breadth": ("market breadth", "advances", "declines", "advance/decline"),
    "gsec_yields": ("g-sec", "gsec", "government security yield", "bond yield", "yield curve"),
}

_FETCHERS = {
    "nifty_snapshot": lambda: client.fetch_nifty_snapshot(),
    "market_history": lambda: client.fetch_market_history(),
    "india_vix": lambda: client.fetch_india_vix(),
    "market_breadth": lambda: client.fetch_market_breadth(),
    "gsec_yields": lambda: client.fetch_gsec_yield_snapshot(),
}


async def capital_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Return a focused, evidence-grounded Capital Markets report.

    Responses begin with the answer, show only relevant observations in a
    compact source-aware table, then explain the supported implication. Keep
    periods, units, and freshness explicit; never invent missing data or
    provenance. Cached/provider snapshots must not be described as live quotes.
    """
    query = str(state.get("query", "")).strip()[:500]
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected, selection_error = await select_relevant_services_with_llm(
            query=query,
            service_keywords=_SERVICE_KEYWORDS,
            api_key=capital_settings.CAPITAL_LLM_KEY,
            model=capital_settings.CAPITAL_LLM_MODEL,
        )
    names = list(_FETCHERS)
    results = await asyncio.gather(
        *(_FETCHERS[name]() for name in names if name in selected),
        return_exceptions=True,
    )

    data_context: dict[str, Any] = {}
    evidence_context: dict[str, Any] = {}
    freshness: dict[str, str] = {}
    citations: list[dict[str, Any]] = []
    errors = [selection_error] if selection_error else []
    for name, result in zip((name for name in names if name in selected), results):
        if isinstance(result, Exception):
            errors.append(f"{name}: {result}")
            data_context[name] = {"period": None}
            evidence_context[name] = data_context[name]
            freshness[name] = "unavailable"
            continue
        records = [record_to_dict(item) for item in result]
        if not records:
            data_context[name] = {"period": None}
            evidence_context[name] = data_context[name]
            freshness[name] = "unavailable"
            continue
        latest = records[0]
        data_context[name] = {
            key: value for key, value in latest.items() if key not in {"id", "citation"}
        }
        evidence_context[name] = {
            key: value for key, value in latest.items() if key != "id"
        }
        citation = latest.get("citation")
        if isinstance(citation, dict):
            citations.append({"dataset": name, **citation})
            freshness[name] = str(citation.get("freshness", "unavailable"))
        else:
            freshness[name] = "unavailable"

    analysis = ""
    try:
        analysis = await reason_over_sector_data(
            query=query,
            sector_name="Capital Markets",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=capital_settings.CAPITAL_LLM_KEY,
            model=capital_settings.CAPITAL_LLM_MODEL,
        )
    except Exception as exc:
        logger.exception("Capital-markets reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "capital_market_sector_analysis": analysis,
        "capital_market_sector_data": data_context,
        "capital_market_sector_errors": errors,
        "capital_market_sector_citations": citations,
        "capital_market_sector_freshness": freshness,
    }
