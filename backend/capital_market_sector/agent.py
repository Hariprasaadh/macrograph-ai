"""Capital Markets Sector LangGraph Agent Node.

Coordinates empirical data retrieval across all 10 domain responsibilities
and performs deep, citation-grounded macroeconomic reasoning.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from capital_market_sector import client
from capital_market_sector.config import capital_settings
from core.sector_reasoning import (
    reason_over_sector_data,
    record_to_dict,
    select_relevant_services_with_llm,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Senior Capital Markets & Financial Macroeconomics Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You evaluate India's capital markets across 10 core domain responsibilities:
  1. Equity Market Performance: NIFTY 50, SENSEX, index price action, and returns.
  2. Market Volatility & Sentiment: India VIX, volatility regimes, market sentiment.
  3. Market Liquidity & Breadth: Advances/declines, turnover, market breadth ratio.
  4. Government Securities (G-Sec) Yields: RBI monthly SGL yields (10Y, 5Y, 2Y) and 2s10s yield curve slope.
  5. Mutual Fund Flows: AMFI equity inflows, monthly SIP contributions, industry AUM.
  6. Foreign Portfolio Investment (FPI) & Institutional Activity: FPI equity purchases, sales, net investment, DII counter-flows.
  7. Corporate Earnings & Valuations: Listed company EPS, P/E ratio, P/B ratio, dividend yield, and corporate PAT growth.
  8. Sectoral Market Performance: NIFTY Bank, NIFTY IT, Auto, Pharma, FMCG rotation and relative performance.
  9. Primary Capital Markets: IPO proceeds mobilized, issue counts, and equity fundraising (QIP, rights).
  10. Market Structure & Investor Participation: Active Demat accounts (NSDL + CDSL), retail participation share.
  11. Market-Economy Linkages: Equity Risk Premium (Earnings Yield minus 10Y G-Sec), Buffett Indicator (Market Cap to GDP).

RESPONSE CONTRACT — ANALYZE AND EXPLAIN IN DETAIL:
Do NOT simply dump raw numbers or paste a table into the response. Provide an insightful, highly professional analysis that directly addresses the user's inquiry:
1. Direct Executive Answer:
   - Answer the user's specific query first with clarity and precision (1-3 sentences).
2. Detailed Macro & Market Mechanism Analysis:
   - Thoroughly explain *why* the indicators behave as observed and what economic mechanisms drive them.
   - For equity indices: Discuss valuation multiples (P/E relative to historical 21x median), liquidity drivers, and risk appetite.
   - For volatility (India VIX): Interpret the volatility regime (<13 Low, 13-18 Normal, 18-24 Elevated, >24 Panic) and what it implies for options pricing and equity risk premia.
   - For institutional flows: Analyze the interplay between FPI flows (currency-sensitive, global risk-off/risk-on) and domestic institutional/SIP flows (structural domestic liquidity cushion).
   - For G-Sec yields & macro linkages: Analyze how the 10Y sovereign yield affects the corporate cost of capital, discounting rates for equity valuations, and the Equity Risk Premium (ERP).
3. Structured Observations Table:
   - Provide a compact Markdown table: Columns: [Indicator, Observation / Value, Unit, Period, Source & Freshness]. Keep cells concise.
4. Strategic Implications & Key Takeaways:
   - Detail 3-5 bullet points covering: Valuation Environment, Liquidity & Capital Supply, Volatility & Risk Skew, and Macro Transmission.
5. Limitations & Data Provenance:
   - Explicitly state data freshness (e.g., provider snapshot vs monthly regulatory release) and identify any missing or unavailable metrics.

STRICT ANTI-HALLUCINATION & PROVENANCE RULES:
- Cite only data present in the supplied records (source authority, document reference, period, freshness).
- Never invent numbers or guess unretrieved metrics. If an indicator is missing, explicitly note it as "Unavailable".
- Distinguish provider snapshots (Yahoo Finance) from official exchange/regulatory releases (NSE, RBI DBIE, SEBI, AMFI).
- RBI G-Sec figures are month-end SGL transaction yields, not continuous intraday benchmark bond quotes.
- TABLE & PROVENANCE INTEGRITY: NEVER use placeholder phrases such as "Same as above", "ditto", "as above", or quotation marks to indicate repetition in the 'Source & Freshness' column. Every individual row in the Observations Table must explicitly state the exact source authority and freshness status (e.g., "Yahoo Finance (^NSEI) (upstream_snapshot)").
"""

_SERVICE_KEYWORDS = {
    "nifty_snapshot": ("nifty", "sensex", "index", "equity index", "market level", "market close", "equity market"),
    "market_history": ("historical", "history", "returns", "valuation", "p/e", "price earnings", "dividend yield"),
    "india_vix": ("vix", "volatility", "risk regime", "market sentiment"),
    "market_breadth": ("market breadth", "advances", "declines", "advance/decline", "turnover", "liquidity"),
    "gsec_yields": ("g-sec", "gsec", "government security yield", "bond yield", "yield curve", "10-year yield"),
    "mutual_fund_flows": ("mutual fund", "mf flows", "sip", "equity inflows", "amfi", "dii inflows"),
    "fpi_flows": ("fpi", "fii", "foreign portfolio", "foreign institutional", "foreign investment", "fii flows"),
    "corporate_earnings": ("earnings", "eps", "pat", "corporate profit", "earnings growth", "pe ratio", "valuations"),
    "sectoral_performance": ("sector", "sectoral", "bank nifty", "nifty it", "pharma", "auto", "fmcg", "sector rotation"),
    "primary_market": ("ipo", "fpo", "qip", "primary market", "fundraising", "listing", "equity issuance"),
    "investor_participation": ("demat", "retail participation", "investor accounts", "market structure", "cdsl", "nsdl"),
    "market_economy_linkages": ("equity risk premium", "market cap to gdp", "buffett indicator", "macro linkage", "earnings yield"),
}

_FETCHERS = {
    "nifty_snapshot": lambda: client.fetch_nifty_snapshot(),
    "market_history": lambda: client.fetch_market_history(),
    "india_vix": lambda: client.fetch_india_vix(),
    "market_breadth": lambda: client.fetch_market_breadth(),
    "gsec_yields": lambda: client.fetch_gsec_yield_snapshot(),
    "mutual_fund_flows": lambda: client.fetch_mutual_fund_flows(),
    "fpi_flows": lambda: client.fetch_fpi_equity_flows(),
    "corporate_earnings": lambda: client.fetch_corporate_earnings_valuation(),
    "sectoral_performance": lambda: client.fetch_sectoral_performance(),
    "primary_market": lambda: client.fetch_primary_market_ipos(),
    "investor_participation": lambda: client.fetch_investor_participation(),
    "market_economy_linkages": lambda: client.fetch_market_economy_linkages(),
}


async def capital_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Return a detailed, evidence-grounded Capital Markets analytical report."""
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
