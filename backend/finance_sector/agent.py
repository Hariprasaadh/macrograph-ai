"""Finance Sector LangGraph Agent Node.

This node:
  1. Calls its own FastMCP tools (via direct Python import — within same sector).
  2. Fetches live banking equities & NIFTY Bank index from Yahoo Finance (yfinance).
  3. Uses Tavily AI Search (TVLY_KEY_1) at the end to retrieve real-time RBI & banking news.
  4. Consumes peer data from A2A (Repo rate, CPI) — never fetches those independently.
  5. Uses FIN_FIS_KEY (Groq) to reason over the comprehensive dataset.
  6. Returns structured, polished findings with mandatory citation chains.

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

from finance_sector import client
from finance_sector.config import finance_settings
from finance_sector.market_client import (
    fetch_banking_market_indicators,
    fetch_realtime_finance_news,
)
from finance_sector.models import BankGroup, DataFreshness

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Finance & Banking Sector Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You answer queries concerning India's Scheduled Commercial Banks (SCBs) and Financial Institutions:
  - Bank credit growth & sectoral deployment (Agriculture, Industry/MSME/Large, Services, Retail/Housing/Vehicles).
  - Asset quality: Gross NPA (GNPA), Net NPA (NNPA), Provision Coverage Ratio (PCR), and Capital Adequacy (CRAR, CET1).
  - Bank lending & deposit rates: WALR on fresh/outstanding rupee loans, 1-year median MCLR, WADTDR, and lending spreads.
  - Deposit mobilisation: Aggregate deposits, demand/time deposits, CASA ratio, and Credit-to-Deposit (CD) ratio.
  - Banking equity performance & market indicators: Nifty Bank index (^NSEBANK) and major bank valuations (SBI, HDFC Bank, ICICI Bank).
  - Real-time regulatory & banking developments: Latest RBI policy decisions, MPC stances, and credit announcements.

STRICT CITATIONS & ANTI-HALLUCINATION POLICY (NON-NEGOTIABLE):
1. No Source, No Answer — every banking metric claim must cite the official authority, table reference, and observation period.
2. Never hallucinate, estimate, or hardcode numbers.
3. If data is CACHED or UNAVAILABLE, state that status explicitly.

COMMUNICATION & EXPLANATION STANDARDS:
- Provide an articulate, highly informative, and polished response that non-experts and institutional analysts alike can immediately understand.
- Structure your response with clear Markdown sections:
  1. **Executive Summary & Banking Stability Overview**: Macro health, systemic resilience, credit impulse.
  2. **Credit Deployment & Intermediation**: Trajectory of non-food credit growth, leading credit drivers.
  3. **Asset Quality & Capital Solvency**: NPA ratios, provisioning buffers, and CRAR vs Basel III requirements.
  4. **Monetary Transmission & Lending Rates**: WALR, MCLR, deposit rates, and policy transmission spread.
  5. **Market Sentiment & Equity Indicators**: Nifty Bank benchmark, public vs private bank valuation metrics.
  6. **Real-Time Regulatory Context**: Synthesis of the latest news and RBI notifications.
  7. **Attribution & Provenance Chain**: Formatted table of all data points cited.
"""


_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return a shared singleton AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        key = finance_settings.FIN_FIS_KEY or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("FIN_FIS_KEY or GROQ_API_KEY is not configured in environment.")
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
    """Invoke Groq LLM with exponential backoff on transient errors."""
    response = await client_instance.chat.completions.create(
        model=finance_settings.FINANCE_LLM_MODEL,
        temperature=finance_settings.FINANCE_LLM_TEMPERATURE,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


async def finance_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fetches official data, market indicators, and real-time news."""
    raw_query: str = state.get("query", "Analyse the current state of India's banking sector.")
    safe_query = raw_query.strip()[:500].replace("\r", " ").replace("\n", " ")
    repo_rate: float | None = state.get("repo_rate_from_monetary")
    headline_cpi: float | None = state.get("headline_cpi_from_prices")

    # ── Step 1: Concurrently fetch official banking data + market indicators ───
    credit_task = client.fetch_bank_credit_growth(lookback_months=6)
    quality_task = client.fetch_asset_quality(BankGroup.ALL_SCB, lookback_quarters=4)
    rates_task = client.fetch_lending_rates(lookback_months=6)
    deposits_task = client.fetch_deposits_and_cd_ratio(lookback_months=6)
    market_task = fetch_banking_market_indicators()

    results = await asyncio.gather(
        credit_task, quality_task, rates_task, deposits_task, market_task,
        return_exceptions=True,
    )

    credit_records = results[0] if not isinstance(results[0], Exception) else []
    quality_records = results[1] if not isinstance(results[1], Exception) else []
    rates_records = results[2] if not isinstance(results[2], Exception) else []
    deposit_records = results[3] if not isinstance(results[3], Exception) else []
    market_response = results[4] if not isinstance(results[4], Exception) else None

    # ── Step 2: At the end, query Tavily for real-time news & context ──────────
    news_query = f"RBI Indian banking commercial banks {safe_query}"[:200]
    news_response = await fetch_realtime_finance_news(query=news_query, max_results=4)

    errors = [str(r) for r in results if isinstance(r, Exception)]
    if errors:
        logger.warning("finance_agent_node: some data fetches failed: %s", errors)

    # ── Step 3: Format macroeconomic context for LLM reasoning ────────────────
    def _format_cr(val: float | None) -> str:
        if not val:
            return "N/A"
        lakh_cr = val / 100000.0
        return f"₹{lakh_cr:.2f} Lakh Crore (₹{val:,.0f} Cr)"

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

    if repo_rate is not None and rates_records:
        for r in rates_records:
            if getattr(r, "repo_rate_pct", None) is None:
                r.repo_rate_pct = repo_rate
            if getattr(r, "lending_spread_over_repo_pct", None) is None and getattr(r, "walr_fresh_pct", None) is not None:
                r.lending_spread_over_repo_pct = round(r.walr_fresh_pct - repo_rate, 4)

    latest_credit = credit_records[-1] if credit_records else None
    latest_deposit = deposit_records[-1] if deposit_records else None

    # Format market metrics
    market_data = {}
    if market_response and market_response.status == DataFreshness.LIVE:
        if market_response.benchmark_index:
            idx = market_response.benchmark_index
            market_data["nifty_bank_index"] = {
                "symbol": idx.symbol,
                "current_price": idx.current_price,
                "change_pct": idx.change_pct,
                "observation_date": idx.citation.observation_period,
            }
        market_data["major_banks"] = [
            {
                "symbol": b.symbol,
                "name": b.name,
                "price": b.current_price,
                "change_pct": b.change_pct,
                "pe_ratio": b.pe_ratio,
                "pb_ratio": b.pb_ratio,
                "market_cap_cr": f"₹{b.market_cap_cr:,.2f} Cr" if b.market_cap_cr else None,
            }
            for b in market_response.top_banks
        ]

    # Format real-time news items
    news_items = []
    if news_response and news_response.status == DataFreshness.LIVE:
        news_items = [
            {"title": n.title, "url": n.url, "snippet": n.content[:400]}
            for n in news_response.news_items
        ]

    data_context = {
        "unit_reporting_rule": "Totals are in ₹ Crore. Report large aggregates as '₹X Lakh Crore'.",
        "credit_growth": {
            **_latest(
                credit_records,
                ["gross_credit_cr", "non_food_credit_cr", "non_food_credit_yoy_pct"],
            ),
            "gross_credit_scale": _format_cr(getattr(latest_credit, "gross_credit_cr", None)),
            "non_food_credit_scale": _format_cr(getattr(latest_credit, "non_food_credit_cr", None)),
        },
        "asset_quality": _latest(
            quality_records,
            ["gross_npa_pct", "net_npa_pct", "crar_pct", "provision_coverage_ratio_pct"],
        ),
        "lending_rates": _latest(
            rates_records,
            ["walr_fresh_pct", "mclr_1yr_median_pct", "wadtdr_fresh_pct", "repo_rate_pct", "lending_spread_over_repo_pct"],
        ),
        "deposits": {
            **_latest(
                deposit_records,
                ["aggregate_deposits_cr", "deposits_yoy_pct", "cd_ratio_pct", "casa_ratio_pct"],
            ),
            "aggregate_deposits_scale": _format_cr(getattr(latest_deposit, "aggregate_deposits_cr", None)),
        },
        "market_equity_indicators": market_data,
        "realtime_news_and_regulatory_updates": news_items,
        "a2a_inputs": {
            "repo_rate_from_monetary_sector": repo_rate,
            "headline_cpi_from_prices_sector": headline_cpi,
        },
    }

    # ── Step 4: LLM synthesis via Groq ────────────────────────────────────
    user_message = (
        f"<user_query>\n{safe_query}\n</user_query>\n\n"
        f"<finance_sector_comprehensive_data>\n{json.dumps(data_context, indent=2, default=str)}\n</finance_sector_comprehensive_data>\n\n"
        "Provide an in-depth, beautifully structured macroeconomic and banking intelligence "
        "report responding to this query. Synthesize official RBI DBIE statistics, live market "
        "sentiment (Nifty Bank, bank valuations), and latest real-time regulatory developments. "
        "Strictly cite all sources and observation dates."
    )

    try:
        groq_client = get_groq_client()
        analysis = await _execute_groq_reasoning(groq_client, _SYSTEM_PROMPT, user_message)
    except Exception as exc:
        logger.exception("finance_agent_node: LLM call failed")
        analysis = f"LLM reasoning unavailable: {exc}"

    # ── Step 5: Return structured LangGraph state update ───────────────────
    return {
        "finance_sector_analysis": analysis,
        "finance_sector_data": data_context,
        "finance_sector_market": market_data,
        "finance_sector_news": news_items,
        "finance_sector_errors": errors,
        "finance_sector_freshness": {
            "credit": credit_records[-1].citation.freshness.value if credit_records else "unavailable",
            "quality": quality_records[-1].citation.freshness.value if quality_records else "unavailable",
            "rates": rates_records[-1].citation.freshness.value if rates_records else "unavailable",
            "deposits": deposit_records[-1].citation.freshness.value if deposit_records else "unavailable",
            "market": market_response.status.value if market_response else "unavailable",
            "news": news_response.status.value if news_response else "unavailable",
        },
    }
