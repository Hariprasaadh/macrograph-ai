"""Labour Sector LangGraph Agent Node."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sector_reasoning import (
    record_to_dict,
    reason_over_sector_data,
    select_relevant_services_with_llm,
)
from labour_sector import client
from labour_sector.config import labour_settings

_SYSTEM_PROMPT = """You are the Labour & Employment Specialist for Macrograph AI.
You answer only about India's PLFS labour indicators and employment conditions.
Use the reported period and provenance. Never invent missing rates, breakdowns,
wages, or payroll values.
"""

_SERVICE_KEYWORDS = {
    "unemployment": ("unemployment", "jobless", "unemployment rate"),
    "lfpr": ("lfpr", "labour force participation", "labor force participation", "female participation"),
    "wpr": ("wpr", "worker population ratio", "employment-to-population"),
    "labour_conditions": ("epfo", "payroll", "employment quality", "wage", "earnings", "self-employed", "casual labour", "salaried"),
}

_FETCHERS = {
    "unemployment": lambda: client.fetch_unemployment_snapshot(),
    "lfpr": lambda: client.fetch_labour_force_participation(),
    "wpr": lambda: client.fetch_worker_population_ratio(),
    "labour_conditions": lambda: client.fetch_labour_employment_conditions(),
}


async def labour_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", "")).strip()[:500]
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected, selection_error = await select_relevant_services_with_llm(
            query=query,
            service_keywords=_SERVICE_KEYWORDS,
            api_key=labour_settings.LABOUR_LLM_KEY,
            model=labour_settings.LABOUR_LLM_MODEL,
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
            sector_name="Labour & Employment",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=labour_settings.LABOUR_LLM_KEY,
            model=labour_settings.LABOUR_LLM_MODEL,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("Labour-sector reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "labour_sector_analysis": analysis,
        "labour_sector_data": data_context,
        "labour_sector_errors": errors,
        "labour_sector_citations": citations,
        "labour_sector_freshness": freshness,
    }
