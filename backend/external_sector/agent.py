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

_SYSTEM_PROMPT = """You are the Senior External Sector Macroeconomic Specialist for Macrograph AI.
Your goal is to provide deep, analytical, and authoritative answers to the user's specific economic questions about India's external accounts:
1. Foreign Exchange Reserves (stock, components, import cover, reserve adequacy benchmarks)
2. International Trade Balance (merchandise exports/imports, oil vs non-oil composition, terms of trade)
3. Balance of Payments & CAD (Current account balance % GDP, capital flows, BoP financing sustainability)
4. Exchange Rates & Competitiveness (USD/INR, EUR/INR, GBP/INR, JPY/INR spot rates, 40-currency REER/NEER)
5. Remittances & Invisibles (Private transfers, workers' remittances, services surplus offsetting goods deficit)
6. External Capital Flows & External Debt (FDI, FPI, external debt stock, short-term debt coverage)
7. Multilateral Benchmarks (IMF WEO medium-term projections for CAD/GDP and export volume growth)

Analytical Standards:
- DIRECTLY ANSWER THE SPECIFIC QUESTION in your opening paragraph. Do not start with generic boilerplate or a blind data dump.
- EXPLAIN THE ECONOMIC MECHANISM: Analyze *why* the metrics moved (e.g., how crude oil prices affect the trade deficit and CAD; why the RBI conducted dollar sales; why import cover of 13.2 months provides external stability; how services surplus cushions merchandise deficit).
- SYNTHESIZE EVIDENCE: Seamlessly integrate authoritative official data (RBI/MoSPI/IMF) with real-time market spot rates (Yahoo Finance) and breaking geopolitical news (Tavily).
- HIGHLIGHT RELEVANT DATA: Use a concise Markdown table only for the exact metrics relevant to the question.
- DRAW ACTIONABLE IMPLICATIONS: Provide 3-4 structured macroeconomic takeaways that interpret the systemic impact on rupee stability, sovereign solvency, and monetary policy.
- ZERO HALLUCINATION: Never invent or extrapolate unverified figures. Strictly cite the official source authority, table reference, and observation period for every data point."""

_SERVICE_KEYWORDS = {
    "forex_reserves": ("forex", "foreign exchange reserve", "fca", "gold reserve", "sdr", "reserve adequacy", "import cover"),
    "trade_balance": ("trade balance", "trade deficit", "trade surplus", "merchandise trade", "exports", "imports", "crude oil import"),
    "balance_of_payments": ("balance of payments", "bop", "current account", "cad", "capital account", "financing"),
    "exchange_rates": ("exchange rate", "usd/inr", "rupee", "reer", "neer", "currency", "depreciation", "appreciation"),
    "external_flows": ("fdi", "fpi", "foreign investment", "portfolio flows", "capital flows"),
    "remittances": ("remittance", "invisibles", "private transfer", "worker remittance", "secondary income", "nri deposit"),
    "external_debt": ("external debt", "sovereign debt", "refinancing", "short-term debt", "debt service", "external liability"),
    "live_market": ("spot rate", "live rate", "brent", "crude", "oil price", "current rate", "market price", "today", "live market"),
    "imf_weo_outlook": ("imf", "weo", "projection", "outlook", "forecast", "medium term", "world economic outlook"),
}

_FETCHERS = {
    "forex_reserves": lambda: client.fetch_forex_reserves(),
    "trade_balance": lambda: client.fetch_trade_balance(),
    "balance_of_payments": lambda: client.fetch_balance_of_payments(),
    "exchange_rates": lambda: client.fetch_exchange_rates(),
    "external_flows": lambda: client.fetch_external_flows(),
    "remittances": lambda: client.fetch_remittances_and_invisibles(),
    "external_debt": lambda: client.fetch_external_debt(),
    "live_market": lambda: client.fetch_live_market_rates(),
    "imf_weo_outlook": lambda: client.fetch_imf_external_outlook(),
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

    # Always ensure at least forex_reserves and trade_balance are fetched for broad queries
    if not selected:
        selected = {"forex_reserves", "trade_balance", "exchange_rates"}

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

        if isinstance(result, list):
            records = [record_to_dict(item) for item in result]
        else:
            records = [record_to_dict(result)]

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

    # Enrich with Tavily real-time macroeconomic news & context
    try:
        search_query = f"India macroeconomic external {query}" if query else "India foreign trade, forex reserves and rupee"
        tavily_rec = await client.fetch_realtime_intelligence(query=search_query, max_results=3)
        evidence_context["realtime_news_intelligence"] = {
            "summary": tavily_rec.summary,
            "articles": [item.get("title") for item in tavily_rec.news_items if isinstance(item, dict)],
            "source_urls": tavily_rec.source_urls[:3],
        }
        if tavily_rec.citation:
            citations.append({"dataset": "realtime_intelligence", **tavily_rec.citation.model_dump()})
    except Exception as exc:
        logger.debug("Tavily real-time enrichment skipped: %s", exc)

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
