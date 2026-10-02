"""Finance Sector LangGraph Agent Node.

This node:
  1. Calls its own FastMCP tools (via direct Python import — within same sector).
  2. Consumes peer data from A2A (Repo rate, CPI) — never fetches those independently.
  3. Uses FS_KEY (Groq) to reason over the fetched data.
  4. Returns structured findings with mandatory citation chains.

Rules:
  - No hardcoded economic values.
  - No imports from other sector packages.
  - Repo rate is only set if it arrives in the OrchestratorState from monetary_sector.
"""
from __future__ import annotations

import asyncio
import json
import logging
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
from finance_sector.client import FinanceDataUnavailableError
from finance_sector.models import BankGroup, DataFreshness

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Finance & Banking Sector Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You ONLY answer queries concerning India's Scheduled Commercial Banks (SCBs) and the Banking Sector:
  - Bank credit growth and sectoral deployment (Agriculture credit, Industry/MSME/Large, Services credit, Personal/Housing/Vehicle loans).
  - Asset quality: SCB Gross NPA (GNPA), Net NPA (NNPA), Provision Coverage Ratio (PCR), and Capital Adequacy (CRAR, CET1).
  - Bank lending & deposit rates: WALR on fresh/outstanding rupee loans, 1-year median MCLR, WADTDR on fresh/outstanding deposits, and lending spreads.
  - Deposit mobilisation: Aggregate deposits, demand/time deposits, CASA ratio, and Credit-to-Deposit (CD) ratio.

STRICT DOMAIN BOUNDARY ENFORCEMENT (CRITICAL):
- You are a specialized domain agent for Banking and Financial Institutions ONLY.
- If the user query is outside this domain (e.g. asking about agricultural crop production/MSP, national GDP/GVA calculation, CPI/WPI headline inflation index, central fiscal budget/deficit, external forex/trade balance, equity markets/NIFTY, weather, or non-economic topics):
  You MUST POLITELY DECLINE to answer that topic, and explicitly explain:
  "I am the **Finance & Banking Sector Specialist**. My analytical scope is strictly restricted to Scheduled Commercial Banks (SCBs), including bank credit deployment, asset quality (NPAs, CRAR), lending rates (WALR, MCLR), and deposits.
  Your query regarding this topic falls outside my domain scope.
  Please switch to the **Macrograph Orchestrator** (via the toggle in the top-right or left sidebar), which has the multi-agent routing capability to investigate across all 10 macroeconomic sectors."
- Do NOT attempt to answer or fabricate data for topics outside the banking and financial sector.

CITATIONS & PROVENANCE RULES:
1. No Source, No Answer — every banking metric claim must cite the official RBI DBIE table and observation period (e.g. Table r539 for credit, Table r330 for NPAs, Table r531 for lending rates, Table r689 for deposits).
2. Never hallucinate, estimate, or hardcode numbers.
3. If data is CACHED (not live), explicitly state that freshness in your analysis.
4. Keep analysis concise, factual, and formatted with clear Markdown headers and tables.
"""


class FinanceAnalysisOutput(BaseModel):
    """Structured analytical output produced by PydanticAI."""

    summary: str = Field(description="Executive analysis of banking system stability and performance")
    key_findings: list[str] = Field(default_factory=list, description="Key bullet points with data values")
    freshness_caveats: list[str] = Field(default_factory=list, description="Notes on data freshness, especially CACHED data")
    citations: list[str] = Field(default_factory=list, description="Official table references cited")


def create_pydantic_ai_agent(model: Any = None):
    """Factory to create a typed PydanticAI Agent for finance sector analysis."""
    import os
    from pydantic_ai import Agent
    if model is not None:
        return Agent(
            model=model,
            output_type=FinanceAnalysisOutput,
            system_prompt=_SYSTEM_PROMPT,
        )

    api_key = finance_settings.FS_KEY or os.getenv("GROQ_API_KEY", "dummy-init-key")
    try:
        from pydantic_ai.models.groq import GroqModel
        from pydantic_ai.providers.groq import GroqProvider
        provider = GroqProvider(api_key=api_key)
        groq_model = GroqModel(finance_settings.FINANCE_LLM_MODEL, provider=provider)
    except Exception:
        groq_model = None

    return Agent(
        model=groq_model,
        output_type=FinanceAnalysisOutput,
        system_prompt=_SYSTEM_PROMPT,
    )



_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return a shared singleton AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        if not finance_settings.FS_KEY:
            raise ValueError("FS_KEY is not configured in environment or finance_settings.")
        _groq_client = AsyncGroq(api_key=finance_settings.FS_KEY)
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
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


async def finance_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fetches data, reasons with Groq, returns sector findings.

    Expected keys in state:
      - query (str): The macroeconomic question being investigated.
      - repo_rate_from_monetary (float | None): Repo rate passed via A2A.
      - headline_cpi_from_prices (float | None): CPI passed via A2A.
    """
    raw_query: str = state.get("query", "Analyse the current state of India's banking sector.")
    safe_query = raw_query.strip()[:500].replace("\r", " ").replace("\n", " ")
    repo_rate: float | None = state.get("repo_rate_from_monetary")
    headline_cpi: float | None = state.get("headline_cpi_from_prices")

    # ── Step 1: Fetch all 4 pillars concurrently ───────────────────────────
    credit_task = client.fetch_bank_credit_growth(lookback_months=6)
    quality_task = client.fetch_asset_quality(BankGroup.ALL_SCB, lookback_quarters=4)
    rates_task = client.fetch_lending_rates(lookback_months=6)
    deposits_task = client.fetch_deposits_and_cd_ratio(lookback_months=6)

    results = await asyncio.gather(
        credit_task, quality_task, rates_task, deposits_task,
        return_exceptions=True,
    )

    credit_records = results[0] if not isinstance(results[0], Exception) else []
    quality_records = results[1] if not isinstance(results[1], Exception) else []
    rates_records = results[2] if not isinstance(results[2], Exception) else []
    deposit_records = results[3] if not isinstance(results[3], Exception) else []

    errors = [str(r) for r in results if isinstance(r, Exception)]
    if errors:
        logger.warning("finance_agent_node: some fetches failed: %s", errors)

    # ── Step 2: Build a data summary for the LLM ──────────────────────────
    def _format_cr(val: float | None) -> str:
        if not val:
            return "N/A"
        lakh_cr = val / 100000.0
        return f"₹{lakh_cr:.2f} Lakh Crore (₹{lakh_cr:.2f} Trillion INR / ₹{val:,.0f} Cr)"

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

    # If repo rate is available from monetary_sector, populate rates_records and derive spread
    if repo_rate is not None and rates_records:
        for r in rates_records:
            if getattr(r, "repo_rate_pct", None) is None:
                r.repo_rate_pct = repo_rate
            if getattr(r, "lending_spread_over_repo_pct", None) is None and getattr(r, "walr_fresh_pct", None) is not None:
                r.lending_spread_over_repo_pct = round(r.walr_fresh_pct - repo_rate, 4)

    latest_credit = credit_records[-1] if credit_records else None
    latest_deposit = deposit_records[-1] if deposit_records else None

    data_context = {
        "unit_reporting_rule": "Totals are in Rupees Crore (Cr). Report large aggregates as '₹X Lakh Crore' or '₹X Trillion'. Do not divide by 1,000 or call 17 million Cr '21,928 Cr'.",
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
        "a2a_inputs": {
            "repo_rate_from_monetary_sector": repo_rate,
            "headline_cpi_from_prices_sector": headline_cpi,
        },
    }

    # ── Step 3: LLM reasoning via Groq ────────────────────────────────────
    user_message = (
        f"<user_query>\n{safe_query}\n</user_query>\n\n"
        f"<finance_sector_data>\n{json.dumps(data_context, indent=2, default=str)}\n</finance_sector_data>\n\n"
        "Provide a concise, citation-backed analysis of the banking sector "
        "relevant to this query. Flag any CACHED data explicitly."
    )

    try:
        groq_client = get_groq_client()
        analysis = await _execute_groq_reasoning(groq_client, _SYSTEM_PROMPT, user_message)
    except Exception as exc:
        logger.exception("finance_agent_node: LLM call failed")
        analysis = f"LLM reasoning unavailable: {exc}"

    # ── Step 4: Build structured output ───────────────────────────────────
    return {
        "finance_sector_analysis": analysis,
        "finance_sector_data": data_context,
        "finance_sector_errors": errors,
        "finance_sector_freshness": {
            "credit": credit_records[-1].citation.freshness.value if credit_records else "unavailable",
            "quality": quality_records[-1].citation.freshness.value if quality_records else "unavailable",
            "rates": rates_records[-1].citation.freshness.value if rates_records else "unavailable",
            "deposits": deposit_records[-1].citation.freshness.value if deposit_records else "unavailable",
        },
    }
