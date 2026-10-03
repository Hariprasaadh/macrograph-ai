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

_SYSTEM_PROMPT = """You are the Monetary & Liquidity Sector Specialist for Macrograph AI.
You answer only about India's RBI policy rates, reserve ratios, money supply,
system liquidity, and MPC stance. The DBIE MCP returns upstream snapshots, not
real-time values. Never infer unpublished aggregates or invent missing values."""

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
            sector_name="Monetary & Liquidity",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=monetary_settings.MONETARY_LLM_KEY,
            model=monetary_settings.MONETARY_LLM_MODEL,
            temperature=monetary_settings.MONETARY_LLM_TEMPERATURE,
        )
    except Exception as exc:
        logger.exception("Monetary-sector reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "monetary_sector_analysis": analysis,
        "monetary_sector_data": data_context,
        "monetary_sector_errors": errors,
        "monetary_sector_citations": citations,
        "monetary_sector_freshness": freshness,
    }
