"""Real Sector LangGraph Agent Node & LLM Reasoning.

Synthesizes MoSPI IIP, DPIIT Core Industries, RBI DBIE GVA/OBICUS,
and listed industrial equity context into structured macroeconomic diagnostics.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sector_reasoning import (
    record_to_dict,
    reason_over_sector_data,
    select_relevant_services_with_llm,
)
from real_sector import client
from real_sector.config import real_settings
from real_sector.parsers import evaluate_industrial_trends

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Real Sector & Industrial Output Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You ONLY answer queries concerning India's Real Sector, Industrial Output, and Core Infrastructure:
  - MoSPI Index of Industrial Production (IIP): Manufacturing, Mining, Electricity, and General IIP.
  - MoSPI Use-Based IIP: Primary goods, Capital goods, Intermediate goods, Infrastructure goods, Consumer durables, Consumer non-durables.
  - DPIIT Eight Core Industries (ICI): Coal, Crude Oil, Natural Gas, Refinery Products, Fertilizers, Steel, Cement, Electricity.
  - RBI DBIE & NSO: Quarterly Manufacturing GVA growth & GVA share.
  - RBI OBICUS: Manufacturing Capacity Utilisation Ratio (%), Order books, and inventory-to-sales ratios.
  - Industrial & Infrastructure market context: Steel, Cement, Capital Goods listed companies and NIFTY Infra/Metal trends.

RESPONSE SYNTHESIS CONTRACT:
Structure your response clearly and concisely following this exact pattern:

1. Executive Diagnostic Conclusion:
   Start with a direct 1-2 sentence assessment of industrial momentum (e.g. "Industrial weakness appears concentrated rather than universal." or "Industrial activity exhibits broad-based capital goods expansion.").

2. Evidence (Bullet points with indicator, value, YoY direction, and period):
   • Manufacturing IIP: [Value]% YoY ([↑/↓/→], Period: [Period])
   • Capital-goods IIP: [Value]% YoY ([↑/↓/→], Period: [Period])
   • Core-sector steel: [Value]% YoY ([↑/↓/→], Period: [Period])
   • Cement: [Value]% YoY ([↑/↓/→], Period: [Period])
   • Manufacturing GVA: [Value]% YoY (Period: [Period])
   • Capacity utilisation (OBICUS): [Value]% (Period: [Period])

3. Market Context (Equity / Sectoral Impact):
   • Relevant listed companies (e.g. Steel: Tata Steel/JSW Steel, Cement: UltraTech, Capital Goods: L&T/BHEL).
   • NIFTY Infrastructure / Metal sector performance context.

4. Data Vintage & Citations:
   Compact observations & provenance table with columns: Indicator, Latest Observation, Period, Official Authority, and Freshness (LIVE/CACHED/SNAPSHOT).

STRICT ATTRIBUTION RULES:
- Never hallucinate, fabricate, or guess numbers.
- Explicitly flag any CACHED data.
"""

_SERVICE_KEYWORDS = {
    "iip_sectoral": ("iip", "industrial production", "manufacturing iip", "mining", "electricity", "general iip"),
    "iip_use_based": ("use-based", "capital goods", "intermediate goods", "consumer durables", "primary goods", "durables"),
    "core_industries": ("core sector", "core industries", "eight core", "steel", "cement", "coal", "refinery", "ici"),
    "manufacturing_gva": ("gva", "manufacturing gva", "gross value added", "real gva", "manufacturing output"),
    "obicus_capacity": ("obicus", "capacity utilisation", "capacity utilization", "order books", "utilization rate"),
    "market_context": ("listed companies", "stocks", "tata steel", "jsw steel", "ultratech", "l&t", "bhel", "market context", "nifty infra"),
    "joined_diagnostic": ("diagnostic", "comprehensive", "real sector", "overview", "industrial momentum", "industrial weakness"),
}

_FETCHERS = {
    "iip_sectoral": lambda: client.fetch_iip_sectoral(),
    "iip_use_based": lambda: client.fetch_iip_use_based(),
    "core_industries": lambda: client.fetch_core_industries(),
    "manufacturing_gva": lambda: client.fetch_manufacturing_gva(),
    "obicus_capacity": lambda: client.fetch_obicus_capacity(),
    "market_context": lambda: client.fetch_infrastructure_market_context(),
    "joined_diagnostic": lambda: client.fetch_joined_real_indicators(),
}


async def real_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fetches relevant real sector data, reasons with LLM, returns findings."""
    query = str(state.get("query", "")).strip()[:500]
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected, selection_error = await select_relevant_services_with_llm(
            query=query,
            service_keywords=_SERVICE_KEYWORDS,
            api_key=real_settings.REAL_LLM_KEY,
            model=real_settings.REAL_LLM_MODEL,
        )

    # If general or empty selection, default to core pillars
    if not selected:
        selected = {"iip_sectoral", "iip_use_based", "core_industries", "manufacturing_gva", "obicus_capacity", "market_context"}

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
            k: v for k, v in latest.items() if k not in {"id", "citation"}
        }
        evidence_context[name] = {
            k: v for k, v in latest.items() if k != "id"
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
            sector_name="Real Sector & Industrial Output",
            system_prompt=_SYSTEM_PROMPT,
            data_context=evidence_context,
            api_key=real_settings.AGR_REAL_KEY or real_settings.REAL_LLM_KEY,
            model=real_settings.REAL_LLM_MODEL,
            temperature=real_settings.REAL_LLM_TEMPERATURE,
        )
    except Exception as exc:
        logger.exception("Real Sector LLM reasoning failed")
        errors.append(f"LLM reasoning unavailable: {exc}")

    return {
        "real_sector_analysis": analysis,
        "real_sector_data": data_context,
        "real_sector_errors": errors,
        "real_sector_citations": citations,
        "real_sector_freshness": freshness,
    }
