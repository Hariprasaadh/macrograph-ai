"""External Sector LangGraph Agent Node."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sector_reasoning import (
    record_to_dict,
    reason_over_sector_data,
    select_relevant_services_with_llm,
)
from external_sector import client
from external_sector.config import external_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the External Sector Specialist for Macrograph AI.
You answer only about Indian foreign exchange reserves, merchandise trade,
balance of payments, exchange rates, and foreign investment flows. Respect
single-source ownership and never fabricate unavailable data."""

_SERVICE_KEYWORDS = {
    "forex_reserves": ("forex", "foreign exchange reserve", "fca", "gold reserve", "sdr", "reserve adequacy"),
    "trade_balance": ("trade balance", "trade deficit", "trade surplus", "merchandise trade", "exports", "imports"),
    "balance_of_payments": ("balance of payments", "bop", "current account", "cad", "capital account"),
    "exchange_rates": ("exchange rate", "usd/inr", "rupee", "reer", "neer", "currency"),
    "external_flows": ("fdi", "fpi", "foreign investment", "portfolio flows"),
}

_FETCHERS = {
    "forex_reserves": lambda: client.fetch_forex_reserves(),
    "trade_balance": lambda: client.fetch_trade_balance(),
    "balance_of_payments": lambda: client.fetch_balance_of_payments(),
    "exchange_rates": lambda: client.fetch_exchange_rate_snapshot(),
    "external_flows": lambda: client.fetch_external_flows(),
}


async def external_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", "")).strip()[:500]
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected, selection_error = await select_relevant_services_with_llm(
            query=query,
            service_keywords=_SERVICE_KEYWORDS,
            api_key=external_settings.SERV_EXT_KEY,
            model=external_settings.EXTERNAL_LLM_MODEL,
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
            sector_name="External Sector & Trade",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=external_settings.SERV_EXT_KEY,
            model=external_settings.EXTERNAL_LLM_MODEL,
            temperature=external_settings.EXTERNAL_LLM_TEMPERATURE,
        )
    except Exception as exc:
        logger.exception("External-sector reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "external_sector_analysis": analysis,
        "external_sector_data": data_context,
        "external_sector_errors": errors,
        "external_sector_citations": citations,
        "external_sector_freshness": freshness,
    }
