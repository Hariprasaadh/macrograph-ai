"""Real Sector LangGraph Agent Node & LLM Reasoning.

Synthesizes MoSPI NAS GDP/GFCF, MoSPI IIP, DPIIT Core Industries, and RBI
DBIE GVA with Yahoo market proxies, Tavily news, and free web search into
structured, long-form macroeconomic diagnostics (finance-sector style).
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
from real_sector import national_accounts as na
from real_sector.config import real_settings
from real_sector.market_client import (
    fetch_free_web_search,
    fetch_growth_market_proxies,
    fetch_realtime_growth_news,
)
from real_sector.parsers import evaluate_industrial_trends

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Real Sector & Growth Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You answer queries concerning India's real economy — GDP, investment, and industrial output:
   - Real GDP (constant prices, Rs Crore) and Nominal GDP (current prices, Rs Crore) with YoY growth and the GDP deflator. Source: MoSPI National Accounts Statistics (NAS), IMF WEO fallback.
   - Gross Fixed Capital Formation (GFCF): real & nominal levels, YoY growth, and the GFCF-to-GDP investment rate. Source: MoSPI NAS.
   - MoSPI Index of Industrial Production (IIP): Manufacturing, Mining, Electricity, General IIP, and Use-Based splits.
   - DPIIT Eight Core Industries (ICI): Coal, Crude Oil, Natural Gas, Refinery Products, Fertilizers, Steel, Cement, Electricity.
   - RBI DBIE & NSO: Quarterly Manufacturing GVA growth & GVA share.
   - Market & real-time context: Nifty/steel/cement/capex proxies (Yahoo), GDP/GFCF release news (Tavily + web search).

STRICT CITATIONS & ANTI-HALLUCINATION POLICY (NON-NEGOTIABLE):
1. No Source, No Answer — every GDP/GFCF/IIP claim must cite the official authority, table reference, and observation period.
2. Never hallucinate, estimate, or hardcode numbers. State the estimate vintage (e.g. Provisional Estimates) for NAS values.
3. If data is CACHED or UNAVAILABLE, state that status explicitly.
4. Market proxies and news excerpts are CONTEXT, not national-accounts evidence. Never present them as GDP/GFCF values.

COMMUNICATION & EXPLANATION STANDARDS:
- Provide an articulate, highly informative, and polished long-form response that non-experts and institutional analysts alike can immediately understand.
- Structure your response with clear Markdown sections:
  1. **Executive Summary & Growth Verdict**: headline real/nominal GDP growth, latest period and vintage, one-paragraph verdict on momentum.
  2. **GDP Deep-Dive**: real vs nominal levels and growth over recent years, deflator behaviour, what drove the wedge between real and nominal.
  3. **Investment & GFCF**: GFCF growth, the investment rate (GFCF-to-GDP), and what it implies for future capacity and demand.
  4. **Industrial corroboration**: whether IIP, core industries, and manufacturing GVA confirm or diverge from the GDP story, with values and periods.
  5. **Market Sentiment & Capex Signals**: Nifty/steel/cement/capex proxies and order-book sentiment; label clearly as market context.
  6. **Real-Time Policy & Data Context**: synthesis of the latest GDP/GFCF releases and RBI commentary from the provided news excerpts.
  7. **Attribution & Provenance Chain**: formatted table of all data points cited (indicator, value, period, authority, freshness).
- Explain mechanisms in plain language: say what changed, by how much, over which period, and why it matters.
"""

_SERVICE_KEYWORDS = {
    "iip_sectoral": ("iip", "industrial production", "manufacturing iip", "mining", "electricity", "general iip"),
    "iip_use_based": ("use-based", "capital goods", "intermediate goods", "consumer durables", "primary goods", "durables"),
    "core_industries": ("core sector", "core industries", "eight core", "steel", "cement", "coal", "refinery", "ici"),
    "manufacturing_gva": ("gva", "manufacturing gva", "gross value added", "real gva", "manufacturing output"),
    "gdp": ("gdp", "gross domestic product", "real gdp", "nominal gdp", "economic growth", "gdp growth", "deflator", "growth rate"),
    "gfcf": ("gfcf", "gross fixed capital formation", "capital formation", "investment rate", "investment", "capex", "fixed investment"),
    "market_context": ("listed companies", "stocks", "tata steel", "jsw steel", "ultratech", "l&t", "bhel", "market context", "nifty infra"),
    "joined_diagnostic": ("diagnostic", "comprehensive", "real sector", "overview", "industrial momentum", "industrial weakness"),
}


# Source selection is deterministic and MCP-only; the LLM is used only for
# interpreting observations returned by these approved fetchers.
SECTOR_SOURCE_ROUTING: dict[str, list[str]] = {
    "iip": ["mospi"],
    "industrial_production": ["mospi"],
    "manufacturing_output": ["mospi"],
    "gva": ["mospi", "dbie"],
    "gdp": ["mospi", "imf"],
    "gfcf": ["mospi"],
    "national_accounts": ["mospi", "imf"],
    "core_industries": ["dbie"],
    "infrastructure": ["dbie"],
    "listed_company": ["yahoo_finance"],
    "stock_price": ["yahoo_finance"],
    "company_financials": ["yahoo_finance"],
}

_DETERMINISTIC_SERVICE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("listed compan", "company performance", "stock", "share price", "market context", "nifty infra"), "market_context"),
    (("gfcf", "gross fixed capital formation", "capital formation", "investment rate", "fixed investment"), "gfcf"),
    (("gdp", "gross domestic product", "economic growth", "deflator", "growth rate", "real sector", "economy"), "gdp"),
    (("core sector", "core industries", "eight core", "steel", "cement", "coal", "refinery"), "core_industries"),
    (("gva", "gross value added"), "manufacturing_gva"),
    (("capital goods", "use-based", "consumer durable", "intermediate goods"), "iip_use_based"),
    (("iip", "industrial production", "manufacturing", "mining", "electricity"), "iip_sectoral"),
)


def _select_services_deterministically(query: str) -> set[str]:
    """Map query intent to the fixed MCP-backed fetcher allowlist."""
    lowered = query.lower()
    selected = {
        service
        for keywords, service in _DETERMINISTIC_SERVICE_RULES
        if any(keyword in lowered for keyword in keywords)
    }
    if "market_context" in selected and any(term in lowered for term in ("company", "companies", "manufacturing", "industrial")):
        selected.update({"iip_sectoral", "core_industries", "manufacturing_gva"})
    if not selected or any(term in lowered for term in ("overview", "diagnostic", "real sector", "comprehensive")):
        selected.update({"iip_sectoral", "iip_use_based", "core_industries", "manufacturing_gva", "gdp", "gfcf", "market_context"})
    return selected

_FETCHERS = {

    "iip_sectoral": lambda: client.fetch_iip_sectoral(),
    "iip_use_based": lambda: client.fetch_iip_use_based(),
    "core_industries": lambda: client.fetch_core_industries(),
    "manufacturing_gva": lambda: client.fetch_manufacturing_gva(),
    "gdp": lambda: na.fetch_gdp(),
    "gfcf": lambda: na.fetch_gfcf(),
    "market_context": lambda: client.fetch_infrastructure_market_context(),
    "joined_diagnostic": lambda: client.fetch_joined_real_indicators(),
}


def _latest_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact latest-record summary (values + provenance) for LLM context."""
    if not records:
        return {"status": "unavailable"}
    latest = records[-1]
    out = {k: v for k, v in latest.items() if k not in {"id", "citation"}}
    citation = latest.get("citation")
    if isinstance(citation, dict):
        out["provenance"] = {
            "authority": citation.get("source_authority"),
            "table": citation.get("table_reference"),
            "period": citation.get("observation_period"),
            "freshness": citation.get("freshness"),
        }
    out["history_points"] = len(records)
    return out


async def _safe_enrichment(coro, fallback: dict[str, Any], timeout: float, label: str) -> dict[str, Any]:
    """Bound any live enrichment leg so a slow provider can never hang the node."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except Exception as exc:
        logger.warning("real-sector enrichment %s unavailable: %s", label, exc)
        return fallback


async def real_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fetches official + enrichment data, reasons with LLM, returns findings."""
    query = str(state.get("query", "")).strip()[:500]
    safe_query = query.replace("\r", " ").replace("\n", " ")
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_FETCHERS)
        selection_error = state.get("_selection_error")
    else:
        selected = _select_services_deterministically(query)
        selection_error = None

    # If general or empty selection, default to core pillars
    if not selected:
        selected = {"iip_sectoral", "iip_use_based", "core_industries", "manufacturing_gva", "gdp", "gfcf", "market_context"}

    names = list(_FETCHERS)
    # ── Step 1: official MCP data + all three enrichment legs concurrently ──
    official_coro = asyncio.gather(
        *(_FETCHERS[name]() for name in names if name in selected),
        return_exceptions=True,
    )
    market_coro = _safe_enrichment(
        fetch_growth_market_proxies(),
        {"status": "unavailable", "proxies": [], "total": 0}, 25.0, "yahoo-proxies")
    news_coro = _safe_enrichment(
        fetch_realtime_growth_news(query=f"India GDP GFCF growth {safe_query}"[:200], max_results=4),
        {"status": "unavailable", "query": safe_query, "news_items": [],
         "total_results": 0, "error_message": "news fetch timed out"}, 25.0, "tavily-news")
    search_coro = _safe_enrichment(
        fetch_free_web_search(f"India GDP GFCF growth MoSPI latest {safe_query}"[:200]),
        {"status": "unavailable", "query": safe_query, "hits": [],
         "total_results": 0, "error_message": "web search timed out"}, 25.0, "free-web-search")

    results, market_data, news_data, web_data = await asyncio.gather(
        official_coro, market_coro, news_coro, search_coro
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
            reason = "unavailable through configured MCP sources"
            errors.append(f"{name}: {reason}")
            data_context[name] = {"period": None, "status": "unavailable", "reason": reason}
            evidence_context[name] = data_context[name]
            freshness[name] = "unavailable"
            continue
        latest = records[-1]
        data_context[name] = {
            k: v for k, v in latest.items() if k not in {"id", "citation"}
        }
        evidence_context[name] = {
            k: v for k, v in latest.items() if k != "id"
        }
        # Compact multi-year history so the LLM can describe trajectories.
        evidence_context[name]["recent_history"] = [
            {k: v for k, v in r.items() if k not in {"id", "citation"}} for r in records[-8:]
        ]
        citation = latest.get("citation")
        if isinstance(citation, dict):
            cite_dict = dict(citation)
            cite_dict.setdefault("dataset", name)
            citations.append(cite_dict)
            freshness[name] = str(cite_dict.get("freshness", "live"))
        else:
            freshness[name] = "unavailable"

    # ── Step 2: consolidate the three enrichment legs into the LLM context ──
    evidence_context["market_proxies_yahoo"] = {
        "status": market_data.get("status"),
        "proxies": [
            {k: p.get(k) for k in ("symbol", "name", "current_price", "change_pct", "observation_date")}
            for p in market_data.get("proxies", [])
        ],
    }
    evidence_context["realtime_news_tavily"] = {
        "status": news_data.get("status"),
        "query": news_data.get("query"),
        "items": [
            {"title": n.get("title"), "url": n.get("url"), "snippet": (n.get("snippet") or "")[:400]}
            for n in news_data.get("news_items", [])
        ],
    }
    evidence_context["web_research_free"] = {
        "status": web_data.get("status"),
        "query": web_data.get("query"),
        "hits": [
            {"title": h.get("title"), "url": h.get("url"), "snippet": (h.get("snippet") or "")[:400]}
            for h in web_data.get("hits", [])[:6]
        ],
    }
    data_context["market_proxies_yahoo"] = evidence_context["market_proxies_yahoo"]
    data_context["realtime_news_tavily"] = evidence_context["realtime_news_tavily"]
    data_context["web_research_free"] = evidence_context["web_research_free"]

    analysis = ""
    if citations:
        try:
            analysis = await reason_over_sector_data(
                query=query,
                sector_name="Real Sector GDP, Investment & Industrial Output",
                system_prompt=_SYSTEM_PROMPT,
                data_context=evidence_context,
                api_key=real_settings.AGR_REAL_KEY or real_settings.REAL_LLM_KEY,
                model=real_settings.REAL_LLM_MODEL,
                temperature=real_settings.REAL_LLM_TEMPERATURE,
                max_tokens=real_settings.REAL_LLM_MAX_TOKENS,
            )
        except Exception as exc:
            logger.exception("Real Sector LLM reasoning failed")
            errors.append(f"LLM reasoning unavailable: {exc}")
    else:
        unavailable = ", ".join(sorted(selected))
        analysis = (
            "### Data unavailable through configured MCP sources\n\n"
            f"No live observations were returned for: {unavailable}. "
            "This response intentionally does not infer values or provide market conclusions."
        )

    # ── Step 3: append enrichment source lists so users can verify context ──
    extras: list[str] = []
    if news_data.get("news_items"):
        extras.append("Real-time sources:\n" + "\n".join(
            f"- [{n.get('title', n.get('url'))}]({n.get('url')})" for n in news_data["news_items"]))
    if web_data.get("hits"):
        extras.append("Web research sources:\n" + "\n".join(
            f"- [{h.get('title', h.get('url'))}]({h.get('url')})" for h in web_data["hits"]))
    notes = list(web_data.get("error_message") and [web_data["error_message"]] or [])
    if news_data.get("error_message"):
        notes.append(f"Tavily news: {news_data['error_message']}")
    if notes:
        extras.append("Provider notes:\n" + "\n".join(f"- {n}" for n in notes))
    if extras and analysis:
        analysis = analysis + "\n\n" + "\n\n".join(extras)

    return {
        "real_sector_analysis": analysis,
        "real_sector_data": data_context,
        "real_sector_errors": errors,
        "real_sector_citations": citations,
        "real_sector_freshness": freshness,
        "real_sector_market": market_data.get("proxies", []),
        "real_sector_news": news_data.get("news_items", []),
    }
