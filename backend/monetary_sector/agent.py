"""Monetary Sector LangGraph Agent Node."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sector_reasoning import (
    record_to_dict,
    reason_over_sector_data,
    select_relevant_services_with_llm,
)
from monetary_sector import client
from monetary_sector.config import monetary_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Senior Monetary Policy & Liquidity Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You evaluate India's monetary conditions across the sector's data services:
  - Policy Rates & Reserve Ratios: repo, reverse repo, SDF, MSF, bank rate, CRR, SLR, and the LAF corridor width.
  - Money Supply: M0/M1/M2/M3 stocks and M3 YoY growth.
  - System Liquidity: reported LAF operation components and the reported liquidity condition.
  - Monetary Stance: the MPC stance label in its policy-rate context.
  - Real-Time MPC Context (only when supplied under realtime_mpc_news): latest MPC news items, clearly labelled as Real-Time Intelligence — never as official statistics.

RESPONSE CONTRACT — ANALYZE AND EXPLAIN IN DETAIL:
Do NOT simply dump raw numbers or paste a table into the response. Provide an insightful, highly professional analysis that directly addresses the user's inquiry:
1. Direct Executive Answer:
   - Answer the user's specific query first with clarity and precision (1-3 sentences): current repo rate, corridor width, stance, and the M3/liquidity headline.
2. Detailed Mechanism Analysis:
   - Thoroughly explain *why* the indicators read as observed and what monetary mechanisms drive them.
   - For the rate corridor: explain the repo rate as the policy anchor with SDF as the floor and MSF as the ceiling; interpret the corridor width in basis points and what it implies for overnight money-market volatility.
   - For the stance: explain what the MPC stance label signals about the future direction of rates; discuss the real policy rate (repo minus inflation) ONLY when headline CPI evidence is supplied — never compute or imply it otherwise.
   - For money supply: interpret the M3 stock and YoY growth — monetary expansion, credit impulse, and consistency with inflation control.
   - For liquidity: read ONLY the reported operation components and the reported liquidity condition; never derive a net LAF total or a surplus/deficit label the records do not state.
3. Structured Observations Table:
   - Provide a compact Markdown table: Columns: [Indicator, Observation / Value, Unit, Period, Source & Freshness]. Keep cells concise.
4. Strategic Implications & Key Takeaways:
   - Detail 3-5 bullet points covering: Rate Outlook, Liquidity & Funding Conditions, Money/Credit Growth vs Inflation, and Policy Transmission.
5. Limitations & Data Provenance:
   - Explicitly state data freshness (live vs upstream snapshot vs cached) and identify any missing or unavailable metrics.

STRICT ANTI-HALLUCINATION & PROVENANCE RULES:
- Cite only data present in the supplied records (source authority, document reference, period, freshness).
- Never invent numbers or guess unretrieved metrics. If an indicator is missing, explicitly note it as "Unavailable".
- Never infer a real policy rate without headline CPI, a net LAF aggregate, or a stance label beyond what the policy-rate table states.
- TABLE & PROVENANCE INTEGRITY: NEVER use placeholder phrases such as "Same as above", "ditto", "as above", or quotation marks to indicate repetition in the 'Source & Freshness' column. Every individual row in the Observations Table must explicitly state the exact source authority and freshness status.
"""

_SERVICE_KEYWORDS = {
    "policy_rates": ("repo", "sdf", "msf", "bank rate", "reverse repo", "crr", "slr", "policy rate", "rate corridor"),
    "money_supply": ("money supply", "money stock", "m0", "m1", "m2", "m3", "currency in circulation"),
    "system_liquidity": ("liquidity", "laf", "absorption", "injection", "liquidity operations", "wacr"),
    "monetary_stance": ("monetary stance", "mpc stance", "policy stance", "real policy rate", "restrictive", "accommodative", "neutral stance"),
}

_FETCHERS = {
    "policy_rates": lambda: client.fetch_policy_rates(lookback_months=6),
    "money_supply": lambda: client.fetch_money_supply(lookback_months=6),
    "system_liquidity": lambda: client.fetch_system_liquidity(lookback_months=6),
    "monetary_stance": lambda: client.fetch_monetary_stance_snapshot(),
}

_NEWS_KEYWORDS = (
    "news",
    "latest",
    "recent",
    "mpc meeting",
    "mpc decision",
    "announcement",
    "governor",
    "speech",
    "press release",
    "minutes",
)


_FORCE_LIVE_KEYWORDS = (
    "live",
    "real-time",
    "real time",
    "realtime",
    "up to date",
    "up-to-date",
    "fresh",
)


def _wants_force_live(query: str) -> bool:
    """Detect an explicit live-data request (e.g. 'fetch live rates').

    Forced queries bypass the DuckDB cache entirely: live MCP failure raises
    instead of silently serving cached rows.
    """
    lowered = query.casefold()
    return any(keyword in lowered for keyword in _FORCE_LIVE_KEYWORDS)


async def _fetch_forced_live(name: str) -> Any:
    """Fetch one service with the cache fallback disabled."""
    if name == "policy_rates":
        return await client.fetch_policy_rates(lookback_months=6, force_live=True)
    if name == "money_supply":
        return await client.fetch_money_supply(lookback_months=6, force_live=True)
    if name == "system_liquidity":
        return await client.fetch_system_liquidity(lookback_months=6, force_live=True)
    if name == "monetary_stance":
        return await client.fetch_monetary_stance_snapshot(force_live=True)
    raise ValueError(f"Unknown monetary service: {name}")


def _needs_mpc_news(query: str, selected: set[str]) -> bool:
    """Fetch Tavily MPC news only for stance questions or recency-seeking queries.

    Keeps ordinary data queries fast by skipping the remote-search round trip.
    """
    if "monetary_stance" in selected:
        return True
    lowered = query.casefold()
    return any(keyword in lowered for keyword in _NEWS_KEYWORDS)


async def monetary_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", "")).strip()[:500]
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected, selection_error = await select_relevant_services_with_llm(
            query=query,
            service_keywords=_SERVICE_KEYWORDS,
            api_key=monetary_settings.MONETARY_LLM_KEY,
            model=monetary_settings.MONETARY_LLM_MODEL,
        )
    names = list(_FETCHERS)
    force_live = _wants_force_live(query)
    if force_live:
        results = await asyncio.gather(
            *(_fetch_forced_live(name) for name in names if name in selected),
            return_exceptions=True,
        )
    else:
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

    news_items: list[dict[str, Any]] = []
    if _needs_mpc_news(query, selected):
        try:
            news_items = await client.fetch_mpc_news_via_tavily_mcp(query)
        except Exception as exc:
            logger.warning("Monetary MPC news enrichment failed: %s", exc)
            errors.append(f"realtime_mpc_news: {exc}")
    if news_items:
        evidence_context["realtime_mpc_news"] = news_items

    analysis = ""
    try:
        analysis = await reason_over_sector_data(
            query=query,
            sector_name="Monetary & Liquidity",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=monetary_settings.MONETARY_LLM_KEY,
            model=monetary_settings.MONETARY_LLM_MODEL,
            temperature=monetary_settings.MONETARY_LLM_TEMPERATURE,
            max_tokens=monetary_settings.MONETARY_LLM_MAX_TOKENS,
        )
    except Exception as exc:
        logger.exception("Monetary-sector reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "monetary_sector_analysis": analysis,
        "monetary_sector_data": data_context,
        "monetary_sector_news": news_items,
        "monetary_sector_force_live": force_live,
        "monetary_sector_errors": errors,
        "monetary_sector_citations": citations,
        "monetary_sector_freshness": freshness,
    }
