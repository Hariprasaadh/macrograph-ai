"""Services Sector LangGraph Agent Node.

This node:
  1. Reasons the user prompt to the appropriate MoSPI MCP dataset
     (ISP for production, NAS for structural GVA) and supporting tools
     (PMI sentiment, transport/freight volumes).
  2. Calls its own FastMCP tools (via direct Python import — within same sector).
  3. Fetches services equity context (Nifty IT + IT stocks, yfinance).
  4. Uses Tavily AI Search (TVLY_KEY_1) at the end for real-time services news.
  5. Consumes peer data from A2A (services credit, services CPI) — never fetches those independently.
  6. Uses SERV_EXT_KEY (Groq) to reason over the comprehensive dataset.
  7. Returns structured, polished findings with mandatory citation chains.

Rules:
  - No hardcoded economic values.
  - Strict Anti-Hallucination & Provenance citation policy.
  - Module length strictly under 400 lines.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from groq import AsyncGroq
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from services_sector import client
from services_sector.config import services_settings
from services_sector.market_client import (
    fetch_realtime_services_news,
    fetch_services_market_indicators,
)
from services_sector.models import DataFreshness, ServiceSubSector

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Services Sector Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You answer queries concerning India's services production and activity:
  - Index of Service Production (ISP, MoSPI, base 2024-25): General services index
    and 19 broad sub-sectors (wholesale/retail trade, transport, warehousing,
    telecom, IT & computer services, banking, insurance, real estate,
    professional/scientific/technical, administrative/support, arts/recreation).
  - Services GVA (NAS Statements 8.9-8.14): structural annual Output/GVA for
    trade & hotels, transport, communication, financial services, real estate,
    and other services.
  - Services sentiment: PMI headline business activity, new orders, input costs, employment.
  - High-frequency volumes: aviation passengers, railway freight, port cargo, telecom subscriptions.
  - IT services momentum: ISP IT sub-sector + Nifty IT / IT-stock market cross-check.

HIGH-FREQUENCY vs STRUCTURAL DISTINCTION (ALWAYS RESPECT):
  - ISP = monthly production/activity (high-frequency measure).
  - NAS Services GVA = annual structural/macroeconomic measure.
  Never present ISP as GVA or vice versa.

STRICT CITATIONS & ANTI-HALLUCINATION POLICY (NON-NEGOTIABLE):
1. No Source, No Answer — every services metric claim must cite the official authority, dataset reference, and observation period.
2. Never hallucinate, estimate, or hardcode numbers.
3. If data is CACHED or UNAVAILABLE, state that status explicitly.

COMMUNICATION & EXPLANATION STANDARDS:
- Provide an articulate, highly informative, and polished response that non-experts and institutional analysts alike can immediately understand.
- NEVER return a bare data dump. Every retrieved value must be accompanied by
  plain-language explanation: what the indicator measures, what the current
  reading means, how it changed versus the prior period (acceleration vs
  deceleration), and why it matters for the user's query.
- For each key metric, explain in this mini-pattern:
  1. **What this means**: one sentence in plain language (e.g. what an ISP
     index level vs its YoY growth each tell you; what PMI above/below 50
     signals; what a GVA share implies).
  2. **Why it moved**: link the change to visible drivers in the data
     (sub-sector leaders/laggards, orders vs costs, base effects).
  3. **Cross-check**: confirm or question the signal with a second source
     (ISP production vs PMI sentiment vs Nifty IT market pricing vs news).
- Distinguish levels from growth rates explicitly whenever both appear.
- COMPLETENESS CONTRACT (you have a generous output budget — use it to
  FINISH): always complete every section through the attribution table.
  Keep each metric explanation tight (2-4 sentences) so nothing is squeezed
  out. Never end mid-sentence, mid-table, or mid-section. If space runs
  short, compress earlier prose — never trail off at the end.
- Structure your response with clear Markdown sections:
  1. **Executive Summary & Services Momentum**: Overall ISP impulse, leading/lagging verticals.
  2. **Production Detail (ISP)**: General index, IT/telecom/professional sub-sector trajectories.
  3. **Structural Context (NAS GVA)**: Services GVA composition and annual growth.
  4. **Sentiment & Demand (PMI)**: Headline PMI vs 50, orders, costs, hiring.
  5. **Volumes & Market Cross-Check**: Transport/freight/telecom volumes, Nifty IT context.
  6. **Real-Time Developments**: Synthesis of the latest news and releases.
  7. **Attribution & Provenance Chain**: Formatted table of all data points cited.
"""

# Prompt → tool routing keywords (mirrors _SERVICE_KEYWORDS pattern of peer sectors).
_SERVICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "isp_growth": ("isp", "service production", "services output", "it services",
                   "telecom", "sub-sector", "subsector", "general index"),
    "services_gva": ("gva", "national accounts", "nas", "statement 8",
                     "structural", "services share", "gdp services"),
    "services_pmi": ("pmi", "sentiment", "business activity", "new orders",
                     "hsbc", "s&p global"),
    "transport_freight": ("aviation", "passenger traffic", "freight", "railway",
                          "port cargo", "telecom subscribers", "broadband", "volumes"),
    "market_context": ("nifty it", "it stocks", "tcs", "infosys", "market",
                       "equities", "valuations"),
    "services_news": ("news", "latest", "rbi", "policy", "release", "announcement"),
}

_DETERMINISTIC_SERVICE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("pmi", "sentiment", "business activity", "new orders", "hsbc", "s&p"), "services_pmi"),
    (("gva", "national accounts", "nas", "structural", "statement 8"), "services_gva"),
    (("telecom subscribers", "broadband", "internet facility", "mobile phone",
       "nss80", "penetration", "% of households"), "transport_freight"),
    (("aviation", "passenger traffic", "railway", "freight", "port cargo"), "transport_freight"),
    (("nifty it", "it stocks", "tcs", "infosys", "hcl", "wipro", "equities",
       "stock market", "valuations"), "market_context"),
    (("news", "developments", "announcement", "policy decision"), "services_news"),
    (("isp", "service production", "services output", "sub-sector", "subsector",
       "general index", "production index"), "isp_growth"),
    (("it services", "software services", "telecom services", "trade services",
       "transport services", "real estate services", "professional services",
       "financial services", "services growth", "services momentum"), "isp_growth"),
)

_OVERVIEW_TRIGGERS: tuple[str, ...] = (
    "overview", "comprehensive", "overall", "state of", "entire sector",
    "all services", "all pillars", "complete picture",
)


def _select_services_deterministically(query: str) -> set[str]:
    """Map query intent to the fixed MCP-backed fetcher allowlist.

    Narrow queries resolve to only the pillars they name; broad overview
    queries resolve to the full set. Never returns a partial accident:
    unmatched specific queries fall back to ISP (headline production).
    """
    lowered = query.lower()
    if any(trigger in lowered for trigger in _OVERVIEW_TRIGGERS):
        return set(_SERVICE_KEYWORDS)
    selected = {
        service
        for keywords, service in _DETERMINISTIC_SERVICE_RULES
        if any(keyword in lowered for keyword in keywords)
    }
    if not selected:
        selected = {"isp_growth"}
    return selected

# Deterministic prompt → sub-sector routing for ISP queries.
_SUB_SECTOR_RULES: tuple[tuple[tuple[str, ...], ServiceSubSector], ...] = (
    (("it ", "it services", "software", "tcs", "infosys", "computer"), ServiceSubSector.IT_COMPUTER),
    (("telecom", "broadband", "mobile", "5g"), ServiceSubSector.TELECOMMUNICATIONS),
    (("bank", "financial services"), ServiceSubSector.BANKING),
    (("insurance",), ServiceSubSector.INSURANCE),
    (("real estate", "housing services"), ServiceSubSector.REAL_ESTATE),
    (("professional", "scientific", "technical", "r&d", "business services"), ServiceSubSector.PROFESSIONAL_TECHNICAL),
    (("transport", "aviation", "railway", "logistics", "freight"), ServiceSubSector.ROAD_TRANSPORT),
    (("trade", "retail", "wholesale"), ServiceSubSector.RETAIL_TRADE),
    (("hotel", "tourism", "accommodation", "restaurant"), ServiceSubSector.ACCOMMODATION_FOOD),
)


def select_isp_sub_sector(query: str) -> ServiceSubSector | None:
    """Deterministically map a prompt to one ISP sub-sector, or None for General/all."""
    lowered = query.lower()
    for keywords, sector in _SUB_SECTOR_RULES:
        if any(k in lowered for k in keywords):
            return sector
    return None


_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return a shared singleton AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        key = services_settings.SERV_EXT_KEY or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("SERV_EXT_KEY or GROQ_API_KEY is not configured in environment.")
        _groq_client = AsyncGroq(api_key=key)
    return _groq_client


@retry(
    retry=retry_if_exception_type((Exception,)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _execute_groq_reasoning(
    client_instance: AsyncGroq,
    system_prompt: str,
    user_message: str,
) -> str:
    """Invoke Groq LLM with exponential backoff on transient errors.

    Guards against mid-answer truncation: if the model stops at the token
    cap (finish_reason='length'), bounded continuation calls resume exactly
    where the text stopped until a clean stop or the continuation budget
    is exhausted.
    """
    max_tokens = services_settings.SERVICES_LLM_MAX_TOKENS
    max_continuations = services_settings.SERVICES_LLM_MAX_CONTINUATIONS
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    parts: list[str] = []
    for _ in range(1 + max_continuations):
        response = await client_instance.chat.completions.create(
            model=services_settings.SERVICES_LLM_MODEL,
            temperature=services_settings.SERVICES_LLM_TEMPERATURE,
            max_tokens=max_tokens,
            messages=messages,
        )
        choice = response.choices[0]
        parts.append(choice.message.content or "")
        if choice.finish_reason != "length":
            break
        logger.warning(
            "services reasoning hit the token cap; requesting continuation "
            "(%d remaining).",
            max_continuations,
        )
        messages.append({"role": "assistant", "content": parts[-1]})
        messages.append({
            "role": "user",
            "content": "Continue exactly where you stopped. Do not repeat completed "
                       "sections — finish the remaining sections and the "
                       "attribution table, then stop.",
        })
        max_continuations -= 1
    return "".join(parts)


async def services_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: reasons prompt to tools, fetches MoSPI data, news, LLMs."""
    raw_query: str = state.get("query", "Analyse the current state of India's services sector.")
    safe_query = raw_query.strip()[:500].replace("\r", " ").replace("\n", " ")
    services_credit: float | None = state.get("services_credit_from_finance")
    services_cpi: float | None = state.get("services_cpi_from_prices")

    # ── Step 1: Reason prompt → appropriate tools (ISP sub-sector focus) ──
    isp_focus = select_isp_sub_sector(safe_query)

    # ── Step 2: Honor query-selected services; narrow by default ──────────
    # The generic chat path passes _selected_services (see
    # core/sector_reasoning.select_relevant_services_with_llm). Fetch ONLY
    # the selected pillars so progress UI, cost, and relevance stay honest.
    # An explicit empty selection (no pillar applies) fetches nothing;
    # a failed selection falls back to deterministic prompt routing.
    preselected = state.get("_selected_services")
    if isinstance(preselected, (list, set, tuple)):
        selected = set(preselected) & set(_SERVICE_KEYWORDS)
        selection_error = state.get("_selection_error")
        if not selected and selection_error:
            selected = _select_services_deterministically(safe_query)
            if selected:
                selection_error = None
    else:
        selected = _select_services_deterministically(safe_query)
        selection_error = None
    errors: list[str] = [selection_error] if selection_error else []

    fetch_plan: dict[str, Any] = {}
    if "isp_growth" in selected:
        fetch_plan["isp"] = client.fetch_isp_growth(sub_sector=isp_focus, lookback_months=6)
    if "services_gva" in selected:
        fetch_plan["gva"] = client.fetch_services_gva()
    if "services_pmi" in selected:
        fetch_plan["pmi"] = client.fetch_services_pmi(lookback_months=6)
    if "transport_freight" in selected:
        fetch_plan["freight"] = client.fetch_transport_and_freight(lookback_months=6)
    if "market_context" in selected:
        fetch_plan["market"] = fetch_services_market_indicators()

    # ── Step 3: Concurrently fetch the selected pillars ────────────────────
    names = list(fetch_plan)
    results = await asyncio.gather(
        *(fetch_plan[name] for name in names),
        return_exceptions=True,
    )
    by_name: dict[str, Any] = dict(zip(names, results))

    isp_records = by_name.get("isp", [])
    gva_records = by_name.get("gva", [])
    pmi_records = by_name.get("pmi", [])
    freight_records = by_name.get("freight", [])
    market_response = by_name.get("market")
    if isinstance(market_response, Exception):
        market_response = None
    for name, result in by_name.items():
        if isinstance(result, Exception):
            errors.append(f"{name}: {result}")
    if not isinstance(isp_records, list):
        isp_records = []
    if not isinstance(gva_records, list):
        gva_records = []
    if not isinstance(pmi_records, list):
        pmi_records = []
    if not isinstance(freight_records, list):
        freight_records = []

    # ── Step 4: At the end, query Tavily for real-time news & context ──────
    news_query = f"India services sector PMI IT {safe_query}"[:200]
    if "services_news" in selected:
        news_response = await fetch_realtime_services_news(query=news_query, max_results=4)
    else:
        news_response = None

    if errors:
        logger.warning("services_agent_node: some data fetches failed: %s", errors)

    # ── Step 5: Format context for LLM reasoning ───────────────────────────
    def _latest(records: list, fields: list[str]) -> dict:
        if not records:
            return {"status": "unavailable"}
        r = records[-1]
        out = {"period": getattr(r, "period", "unknown"), "freshness": "unknown"}
        citation = getattr(r, "citation", None)
        if citation:
            out["freshness"] = citation.freshness.value
            out["source"] = citation.table_reference
        for f in fields:
            out[f] = getattr(r, f, None)
        return out

    general_latest = next(
        (r for r in reversed(isp_records) if r.sub_sector == ServiceSubSector.GENERAL),
        None,
    )
    # NOTE: the MoSPI MCP view publishes the 19 ISP sub-sectors only — no
    # separate General index row. Do NOT mislabel a sub-sector row as
    # General; report it unavailable when absent.
    it_latest = next(
        (r for r in reversed(isp_records) if r.sub_sector == ServiceSubSector.IT_COMPUTER),
        None,
    )

    def _rec_dict(r: Any, fields: list[str]) -> dict:
        if r is None:
            return {"status": "unavailable"}
        out = {"period": getattr(r, "period", "unknown")}
        citation = getattr(r, "citation", None)
        if citation:
            out["freshness"] = citation.freshness.value
            out["source"] = citation.table_reference
        for f in fields:
            out[f] = getattr(r, f, None)
        return out

    # Format market metrics
    market_data = {}
    if market_response and market_response.status == DataFreshness.LIVE:
        if market_response.benchmark_index:
            idx = market_response.benchmark_index
            market_data["nifty_it_index"] = {
                "symbol": idx.symbol,
                "current_price": idx.current_price,
                "change_pct": idx.change_pct,
                "observation_date": idx.citation.observation_period,
            }
        market_data["it_stocks"] = [
            {
                "symbol": s.symbol,
                "name": s.name,
                "price": s.current_price,
                "change_pct": s.change_pct,
                "pe_ratio": s.pe_ratio,
                "pb_ratio": s.pb_ratio,
                "market_cap_cr": f"Rs{s.market_cap_cr:,.2f} Cr" if s.market_cap_cr else None,
            }
            for s in market_response.top_stocks
        ]

    # Format real-time news items
    news_items = []
    if news_response and news_response.status == DataFreshness.LIVE:
        news_items = [
            {"title": n.title, "url": n.url, "snippet": n.content[:400]}
            for n in news_response.news_items
        ]

    # Full per-industry GVA table so the LLM can explain composition instead
    # of treating one industry's record as the whole services economy.
    # NOTE: services_gva_structural (single dict, chat-contract section) is
    # ONE industry's latest — always interpret it alongside this table.
    gva_by_industry: list[dict] = []
    _seen_industries: set[str] = set()
    for r in reversed(gva_records):
        if r.segment in _seen_industries:
            continue
        _seen_industries.add(r.segment)
        gva_by_industry.append({
            "segment": r.segment,
            "nas_statement": r.nas_statement,
            "period": r.period,
            "gva_current_cr": r.gva_current_cr,
            "gva_constant_cr": r.gva_constant_cr,
            "gva_yoy_pct": r.gva_yoy_pct,
            "freshness": r.citation.freshness.value,
        })

    data_context: dict[str, Any] = {
        "tool_routing": {
            "isp_sub_sector_focus": isp_focus.value if isp_focus else "GENERAL (all services)",
            "matched_keywords": [k for k, v in _SERVICE_KEYWORDS.items()
                                 if any(t in safe_query.lower() for t in v)],
            "selected_services": sorted(selected),
        },
    }
    # Emit ONLY selected pillars — unselected services must not appear as
    # "unavailable" sections downstream. Omitted keys are skipped by the
    # chat report formatter and freshness badges.
    if "isp_growth" in selected:
        data_context["isp_general"] = _rec_dict(
            general_latest, ["isp_index", "isp_yoy_pct", "isp_mom_pct"]
        )
        data_context["isp_it_computer"] = _rec_dict(
            it_latest, ["isp_index", "isp_yoy_pct", "isp_mom_pct"]
        )
    if "services_gva" in selected:
        data_context["services_gva_structural"] = _latest(
            gva_records, ["nas_statement", "segment", "gva_current_cr", "gva_constant_cr", "gva_yoy_pct"]
        )
        data_context["services_gva_by_industry"] = gva_by_industry
    if "services_pmi" in selected:
        data_context["services_pmi"] = _latest(
            pmi_records, ["headline_pmi", "new_orders_idx", "input_costs_idx", "employment_idx"]
        )
    if "transport_freight" in selected:
        data_context["transport_freight_telecom"] = _latest(
            freight_records, ["indicator", "value", "unit", "yoy_pct"]
        )
    if market_data:
        data_context["market_equity_indicators"] = market_data
    if news_items:
        data_context["realtime_news_and_releases"] = news_items
    data_context["a2a_inputs"] = {
        "services_credit_from_finance_sector": services_credit,
        "services_cpi_from_prices_sector": services_cpi,
    }

    # ── Step 6: LLM synthesis via Groq ─────────────────────────────────────
    user_message = (
        f"<user_query>\n{safe_query}\n</user_query>\n\n"
        f"<services_sector_comprehensive_data>\n{json.dumps(data_context, indent=2, default=str)}\n</services_sector_comprehensive_data>\n\n"
        "Provide an in-depth, beautifully structured services intelligence "
        "report responding to this query. Do not merely restate the retrieved "
        "numbers — explain what each one means, why it changed versus the prior "
        "period, which sub-sectors/industries drive the movement, and how the "
        "ISP, PMI, market, and news signals confirm or contradict each other. "
        "Use services_gva_by_industry (all industries) for composition — never "
        "present the single services_gva_structural row as the whole economy. "
        "Always distinguish monthly ISP production from structural NAS GVA. "
        "Strictly cite all sources and observation dates."
    )

    try:
        groq_client = get_groq_client()
        analysis = await _execute_groq_reasoning(groq_client, _SYSTEM_PROMPT, user_message)
    except Exception as exc:
        logger.exception("services_agent_node: LLM call failed")
        analysis = f"LLM reasoning unavailable: {exc}"

    # ── Step 7: Build citation list for chat/API consumers ──────────────────
    def _cit(record: Any, dataset: str) -> dict | None:
        citation = getattr(record, "citation", None)
        if citation is None:
            return None
        return {
            "source_agent": "services_sector",
            "source_authority": citation.source_authority,
            "document_title": citation.document_title,
            "table_reference": citation.table_reference,
            "retrieval_url": citation.retrieval_url,
            "observation_period": citation.observation_period,
            "freshness": citation.freshness.value,
            "dataset": dataset,
        }

    citations: list[dict] = []
    # Cite only selected pillars — unselected services stay invisible.
    if "isp_growth" in selected:
        for record, dataset in ((general_latest, "isp_general"), (it_latest, "isp_it_computer")):
            entry = _cit(record, dataset)
            if entry is not None:
                citations.append(entry)
    if "services_gva" in selected:
        latest_gva = _cit(gva_records[-1] if gva_records else None, "services_gva_structural")
        if latest_gva is not None:
            citations.append(latest_gva)
    if "services_pmi" in selected:
        pmi_cit = _cit(pmi_records[-1] if pmi_records else None, "services_pmi")
        if pmi_cit is not None:
            citations.append(pmi_cit)
    if "transport_freight" in selected:
        freight_cit = _cit(
            freight_records[-1] if freight_records else None, "transport_freight_telecom"
        )
        if freight_cit is not None:
            citations.append(freight_cit)
    # One citation per GVA industry so the composition table is fully sourced.
    cited_keys = {
        (c.get("document_title"), c.get("observation_period")) for c in citations
    }
    for r in gva_records:
        entry = _cit(r, "services_gva_structural")
        if entry is None:
            continue
        key = (entry["document_title"], entry["observation_period"])
        if key in cited_keys:
            continue
        cited_keys.add(key)
        citations.append(entry)

    # ── Return structured LangGraph state update ───────────────────────────
    def _fresh(records: list) -> str:
        return records[-1].citation.freshness.value if records else "unavailable"

    return {
        "services_sector_analysis": analysis,
        "services_sector_data": data_context,
        "services_sector_citations": citations,
        "services_sector_market": market_data,
        "services_sector_news": news_items,
        "services_sector_errors": errors,
        "services_sector_freshness": {
            **({"isp_general": _fresh(isp_records), "isp_it_computer": _fresh(isp_records)}
               if "isp_growth" in selected else {}),
            **({"services_gva_structural": _fresh(gva_records)} if "services_gva" in selected else {}),
            **({"services_pmi": _fresh(pmi_records)} if "services_pmi" in selected else {}),
            **({"transport_freight_telecom": _fresh(freight_records)} if "transport_freight" in selected else {}),
            **({"market": market_response.status.value} if market_response else {}),
            **({"news": news_response.status.value} if news_response else {}),
        },
    }
