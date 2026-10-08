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
from monetary_sector import database as db
from monetary_sector import mcp_registry
from monetary_sector.config import monetary_settings

logger = logging.getLogger(__name__)

# Routing triggers live in the MCP registry (single source of truth). The
# _SERVICE_KEYWORDS alias preserves the gateway orchestrator's import contract.
_SERVICE_KEYWORDS = {
    name: spec.triggers for name, spec in mcp_registry.MONETARY_TOOLS.items()
}

# Prompt-intent predicates live in the registry; aliases keep call sites short.
_needs_mpc_news = mcp_registry.wants_news
_wants_force_live = mcp_registry.wants_force_live
_wants_cache_clear = mcp_registry.wants_cache_clear

async def _fetch_service(name: str, force_live: bool = False) -> Any:
    """Fetch one service with optional force_live cache bypass."""
    if name == "policy_rates":
        return await client.fetch_policy_rates(lookback_months=6, force_live=force_live)
    if name == "money_supply":
        return await client.fetch_money_supply(lookback_months=6, force_live=force_live)
    if name == "system_liquidity":
        return await client.fetch_system_liquidity(lookback_months=6, force_live=force_live)
    if name == "monetary_stance":
        return await client.fetch_monetary_stance_snapshot(force_live=force_live)
    raise ValueError(f"Unknown monetary service: {name}")


_FETCHERS = {
    name: (lambda n=name: _fetch_service(n, force_live=False))
    for name in ("policy_rates", "money_supply", "system_liquidity", "monetary_stance")
}

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
   - For CACHED rows, always compute and state the cache age from the citation
     fetched_at timestamp (e.g. "cached — pulled 4 minutes ago" versus
     "cached — pulled 6 hours ago after a live-fetch failure"), so readers can
     tell a fresh reuse from a stale fallback.

STRICT ANTI-HALLUCINATION & PROVENANCE RULES:
- Cite only data present in the supplied records (source authority, document reference, period, freshness).
- Never invent numbers or guess unretrieved metrics. If an indicator is missing, explicitly note it as "Unavailable".
- Never infer a real policy rate without headline CPI, a net LAF aggregate, or a stance label beyond what the policy-rate table states.
- TABLE & PROVENANCE INTEGRITY: NEVER use placeholder phrases such as "Same as above", "ditto", "as above", or quotation marks to indicate repetition in the 'Source & Freshness' column. Every individual row in the Observations Table must explicitly state the exact source authority and freshness status.
"""


async def _fetch_forced_live(name: str) -> Any:
    """Fetch one service with the cache fallback disabled."""
    return await _fetch_service(name, force_live=True)


def _ingest_dataset(
    name: str,
    records: list[dict[str, Any]],
    data_context: dict[str, Any],
    evidence_context: dict[str, Any],
    freshness: dict[str, str],
    citations: list[dict[str, Any]],
) -> None:
    """Fold one service's record list into the node maps.

    Shared by the direct, derived-stance, and fallback-stance paths so all
    three produce identical context, citation, and freshness shapes.
    """
    if not records:
        data_context[name] = {"period": None}
        evidence_context[name] = data_context[name]
        freshness[name] = "unavailable"
        return
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


async def monetary_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", "")).strip()[:500]
    if _wants_cache_clear(query):
        cleared = db.clear_cached_tables()
        total = sum(cleared.values())
        detail = ", ".join(f"{table}: {count}" for table, count in cleared.items())
        return {
            "monetary_sector_analysis": (
                f"Monetary sector cache cleared ({total} rows: {detail}). "
                "The fetch_log audit was preserved. Subsequent queries pull live "
                "MCP data; if all MCP servers are unreachable they now report "
                "unavailable instead of serving stale rows."
            ),
            "monetary_sector_data": {},
            "monetary_sector_news": [],
            "monetary_sector_force_live": False,
            "monetary_sector_errors": [],
            "monetary_sector_citations": [],
            "monetary_sector_freshness": {},
        }
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
        selection_via = "preselected"
    else:
        keyword_hits = mcp_registry.match_services(query)
        if keyword_hits:
            selected, selection_error = keyword_hits, None
            selection_via = "registry-keywords"
        else:
            selected, selection_error = await select_relevant_services_with_llm(
                query=query,
                service_keywords=_SERVICE_KEYWORDS,
                api_key=monetary_settings.MONETARY_LLM_KEY,
                model=monetary_settings.MONETARY_LLM_MODEL,
            )
            selection_via = "llm-router"
    selected = mcp_registry.expand_dependencies(selected)
    force_live = _wants_force_live(query)
    fetch_news = _needs_mpc_news(query, selected)
    logger.info(
        "monetary services selected=%s via=%s force_live=%s news=%s",
        sorted(selected), selection_via, force_live, fetch_news,
    )
    names = list(_FETCHERS)
    # The stance snapshot derives from the fetched policy rates, so it is
    # never fetched twice for one query; the standalone stance fetcher only
    # runs as a fallback when rate fetching fails.
    want_stance = "monetary_stance" in selected
    fetch_order = [name for name in names if name in selected and name != "monetary_stance"]
    if force_live:
        results = await asyncio.gather(
            *(_fetch_service(name, force_live=True) for name in fetch_order),
            return_exceptions=True,
        )
    else:
        results = await asyncio.gather(
            *(_FETCHERS[name]() for name in fetch_order),
            return_exceptions=True,
        )

    data_context: dict[str, Any] = {}
    evidence_context: dict[str, Any] = {}
    freshness: dict[str, str] = {}
    citations: list[dict[str, Any]] = []
    errors = [selection_error] if selection_error else []
    fetched_records: dict[str, list] = {}
    for name, result in zip(fetch_order, results):
        if isinstance(result, Exception):
            errors.append(f"{name}: {result}")
            data_context[name] = {"period": None}
            evidence_context[name] = data_context[name]
            freshness[name] = "unavailable"
            continue
        records = [record_to_dict(item) for item in result]
        fetched_records[name] = list(result)
        _ingest_dataset(
            name, records,
            data_context=data_context,
            evidence_context=evidence_context,
            freshness=freshness,
            citations=citations,
        )

    if want_stance:
        stance_record = client.derive_and_save_stance_snapshot(
            fetched_records.get("policy_rates", [])
        )
        if stance_record is None:
            try:
                fallback = await _fetch_service("monetary_stance", force_live=force_live)
                _ingest_dataset(
                    "monetary_stance",
                    [record_to_dict(item) for item in fallback],
                    data_context=data_context,
                    evidence_context=evidence_context,
                    freshness=freshness,
                    citations=citations,
                )
            except Exception as exc:
                errors.append(f"monetary_stance: {exc}")
                data_context["monetary_stance"] = {"period": None}
                evidence_context["monetary_stance"] = data_context["monetary_stance"]
                freshness["monetary_stance"] = "unavailable"
        else:
            _ingest_dataset(
                "monetary_stance",
                [record_to_dict(stance_record)],
                data_context=data_context,
                evidence_context=evidence_context,
                freshness=freshness,
                citations=citations,
            )

    news_items: list[dict[str, Any]] = []
    if fetch_news:
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
