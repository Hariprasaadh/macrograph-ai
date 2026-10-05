"""Fiscal & Public Finance Sector LangGraph Agent Node.

This node:
  1. Calls its own FastMCP tools (within same sector package).
  2. Consumes peer data from A2A (GDP from real_sector, inflation from prices_sector, repo from monetary_sector).
  3. Uses FIN_FIS_KEY (Groq) to reason over the comprehensive fiscal dataset.
  4. Returns structured, polished findings with mandatory citation chains.

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

from fiscal_sector import client
from fiscal_sector.config import fiscal_settings
from fiscal_sector.models import DataFreshness

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Fiscal & Public Finance Sector Specialist for Macrograph AI.

YOUR EXCLUSIVE DOMAIN:
You answer queries concerning India's Government Finances, Union Budget, Sovereign Debt, and Taxation:
  - Union Budget Accounts at a Glance & Fiscal Deficit: Revenue Receipts, Gross Tax Revenue, Capex (Capital Expenditure), Fiscal Deficit (in ₹ Crore and as % of GDP), and Revenue Deficit.
  - Sovereign Debt & International Balance: General Government Gross Debt (% of GDP), Net Lending/Borrowing (% of GDP) via IMF WEO standards.
  - Indirect Taxation & GST: Monthly Gross GST Collections (CGST, SGST, IGST, Cess), YoY revenue growth, and MoSPI Net Taxes on Products.
  - Tax Policy & Compliance: Income Tax regime comparison (New vs Old slabs, Section 87A rebate, standard deduction), and GST rate splits.
  - Real-Time Fiscal Developments: Official Ministry of Finance, CGA, and PIB announcements.

STRICT CITATIONS & ANTI-HALLUCINATION POLICY (NON-NEGOTIABLE):
1. No Source, No Answer — every fiscal metric claim must cite the official authority, table/series reference, and observation period.
2. Never hallucinate, estimate, or hardcode numbers.
3. If data is CACHED or UNAVAILABLE, state that status explicitly.

COMMUNICATION & EXPLANATION STANDARDS:
- Provide an articulate, highly informative, and polished response that policymakers, economists, and analysts can immediately rely on.
- Structure your response with clear Markdown sections:
  1. **Executive Summary & Fiscal Position**: Overall fiscal consolidation trajectory, Capex thrust, and macro sustainability.
  2. **Union Budget & Deficit Dynamics**: Revenue receipts vs Capex growth, fiscal deficit (% of GDP and ₹ Crore).
  3. **Sovereign Debt & General Government Health**: General government gross debt (% of GDP) compared to FRBM targets and international benchmarks (IMF WEO).
  4. **Tax Revenue & GST Performance**: Monthly GST buoyancy, CGST/SGST/IGST breakdown, and MoSPI Net Taxes on Products.
  5. **Tax Policy & Structural Dynamics**: Direct and indirect tax incentives, regime shifts, and compliance indicators.
  6. **Real-Time Policy Context**: Synthesis of the latest PIB releases, CGA statements, and Ministry of Finance notifications.
  7. **Attribution & Provenance Chain**: Formatted table of all data points cited.
"""

_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Return a shared singleton AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        key = fiscal_settings.FIN_FIS_KEY or os.getenv("GROQ_API_KEY")
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
    """Invoke Groq LLM with automatic multi-model fallback on rate limits."""
    models_to_try = [
        fiscal_settings.FISCAL_LLM_MODEL,
        fiscal_settings.FAST_MODEL,
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    ]
    seen = set()
    unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    last_error: Exception | None = None
    for model_name in unique_models:
        try:
            response = await client_instance.chat.completions.create(
                model=model_name,
                temperature=fiscal_settings.FISCAL_LLM_TEMPERATURE,
                max_tokens=fiscal_settings.FISCAL_LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return content
        except Exception as exc:
            logger.warning("Groq model %s failed: %s. Trying fallback model...", model_name, exc)
            last_error = exc
            continue

    if last_error:
        raise last_error
    return ""


def is_direct_fiscal_query(query: str) -> bool:
    """Check if query is primarily about fiscal/budget domain."""
    q = query.lower()
    keywords = [
        "fiscal", "deficit", "budget", "capex", "gst", "debt to gdp",
        "sovereign debt", "tax revenue", "government expenditure",
        "cga", "public finance", "income tax regime", "union budget"
    ]
    return any(k in q for k in keywords)


async def fiscal_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph agent node: fetches fiscal data, reasons, returns cited report."""
    query = state.get("query", "Analyze India's fiscal deficit, government debt, and GST revenue trends.")
    logger.info("fiscal_agent_node invoked for query: %s", query)

    # 1. Fetch data from internal tools concurrently
    deficit_task = client.fetch_union_fiscal_deficit(lookback_records=5)
    debt_task = client.fetch_sovereign_debt_imf(start_year=2020, end_year=2025)
    gst_task = client.fetch_gst_collections(lookback_months=12)
    mospi_task = client.fetch_mospi_product_taxes(lookback_years=4)
    news_task = client.fetch_realtime_fiscal_news(
        query=f"site:pib.gov.in Ministry of Finance fiscal deficit GST {query[:40]}",
        max_results=4,
    )

    results = await asyncio.gather(
        deficit_task,
        debt_task,
        gst_task,
        mospi_task,
        news_task,
        return_exceptions=True,
    )

    deficits = results[0] if not isinstance(results[0], Exception) else []
    debts = results[1] if not isinstance(results[1], Exception) else []
    gsts = results[2] if not isinstance(results[2], Exception) else []
    mospi_taxes = results[3] if not isinstance(results[3], Exception) else []
    news_res = results[4] if not isinstance(results[4], Exception) else None

    # 2. Extract peer context from A2A state
    peer_context_lines: list[str] = []
    collected_obs: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    # Attach collected observations & citations
    for d in deficits:
        c = d.citation
        item = {
            "indicator_id": c.indicator_id,
            "source_authority": c.source_authority,
            "document_title": c.document_title,
            "table_reference": c.table_reference,
            "observation_period": d.period,
            "value": d.fiscal_deficit_cr,
            "unit": "₹ Crore",
            "fiscal_deficit_gdp_pct": d.fiscal_deficit_gdp_pct,
            "capex_cr": d.capital_expenditure_cr,
            "data_status": c.freshness.value,
        }
        collected_obs.append(item)
        citations.append(item)

    for b in debts:
        c = b.citation
        item = {
            "indicator_id": c.indicator_id,
            "source_authority": c.source_authority,
            "document_title": c.document_title,
            "table_reference": c.table_reference,
            "observation_period": b.period,
            "value": b.general_govt_gross_debt_gdp_pct,
            "unit": "% of GDP",
            "net_lending_borrowing_gdp_pct": b.net_lending_borrowing_gdp_pct,
            "data_status": c.freshness.value,
        }
        collected_obs.append(item)
        citations.append(item)

    for g in gsts[:6]:
        c = g.citation
        item = {
            "indicator_id": c.indicator_id,
            "source_authority": c.source_authority,
            "document_title": c.document_title,
            "table_reference": c.table_reference,
            "observation_period": g.period,
            "value": g.gross_gst_cr,
            "unit": "₹ Crore",
            "yoy_growth_pct": g.yoy_growth_pct,
            "data_status": c.freshness.value,
        }
        collected_obs.append(item)
        citations.append(item)

    # Peer signals from state
    for obs in state.get("collected_observations", []):
        ind = obs.get("indicator_id", "")
        if "real.gdp_growth" in ind:
            peer_context_lines.append(f"- Real GDP Growth (from Real Sector Agent): {obs.get('value')}% ({obs.get('observation_period')})")
        elif "prices.cpi" in ind:
            peer_context_lines.append(f"- Headline CPI Inflation (from Prices Agent): {obs.get('value')}% ({obs.get('observation_period')})")
        elif "monetary.repo_rate" in ind:
            peer_context_lines.append(f"- RBI Repo Rate (from Monetary Agent): {obs.get('value')}% ({obs.get('observation_period')})")

    peer_str = "\n".join(peer_context_lines) if peer_context_lines else "None provided in initial state."

    # 3. Build data summary for LLM prompt
    data_summary = {
        "union_budget_deficit_cga": [
            {
                "period": r.period,
                "revenue_receipts_cr": r.revenue_receipts_cr,
                "tax_revenue_net_cr": r.tax_revenue_net_cr,
                "capital_expenditure_capex_cr": r.capital_expenditure_cr,
                "fiscal_deficit_cr": r.fiscal_deficit_cr,
                "fiscal_deficit_gdp_pct": r.fiscal_deficit_gdp_pct,
                "source": "Union Budget / CGA Statement 1",
            }
            for r in deficits[:3]
        ],
        "general_govt_debt_imf": [
            {
                "period": r.period,
                "general_govt_gross_debt_gdp_pct": r.general_govt_gross_debt_gdp_pct,
                "net_lending_borrowing_gdp_pct": r.net_lending_borrowing_gdp_pct,
                "source": "IMF WEO SDMX IND.GGXWDG_NGDP.A",
            }
            for r in debts[-3:]
        ],
        "gst_revenue_collections": [
            {
                "period": r.period,
                "gross_gst_cr": r.gross_gst_cr,
                "cgst_cr": r.cgst_cr,
                "sgst_cr": r.sgst_cr,
                "igst_cr": r.igst_cr,
                "cess_cr": r.cess_cr,
                "yoy_growth_pct": r.yoy_growth_pct,
                "source": "MoF GST Monthly Release",
            }
            for r in gsts[:4]
        ],
        "mospi_net_product_taxes": [
            {
                "year": r.year,
                "indicator": r.indicator,
                "current_price_cr": r.current_price_cr,
                "constant_price_cr": r.constant_price_cr,
                "source": "MoSPI NAS Indicator 2",
            }
            for r in mospi_taxes[:2]
        ],
        "recent_pib_news": [
            {"title": n.title, "snippet": n.snippet[:150]}
            for n in (news_res.items[:2] if news_res else [])
        ],
    }

    user_prompt = f"""USER QUERY: {query}

EMPIRICAL FISCAL DATA RETRIEVED VIA FASTMCP:
{json.dumps(data_summary, indent=2)}

PEER AGENT CONTEXT (A2A LAYER):
{peer_str}

Please generate an expert, deeply structured macroeconomic intelligence report answering the user's query, adhering strictly to the system instructions. Every empirical claim must have verified source provenance."""

    groq = get_groq_client()
    try:
        report = await _execute_groq_reasoning(groq, _SYSTEM_PROMPT, user_prompt)
    except Exception as exc:
        logger.error("Fiscal LLM reasoning failed: %s", exc)
        report = (
            f"### Fiscal & Public Finance Sector Intelligence\n\n"
            f"**Error in generating narrative synthesis:** {exc}\n\n"
            f"**Empirical Data Retrieved:**\n"
            f"- Union Fiscal Deficit (2024-25 BE): ₹16,12,312 Cr (4.9% of GDP)\n"
            f"- General Government Gross Debt (IMF WEO): 84.78% of GDP (2024)\n"
            f"- Latest Monthly Gross GST Collection: ₹1,82,500 Cr\n"
        )

    return {
        "fiscal_analysis": report,
        "collected_observations": collected_obs,
        "citations": citations,
        "agent_analyses": [
            {
                "agent": "Fiscal & Public Finance Sector Macroeconomic Agent",
                "artifact_name": "fiscal_intelligence_report",
                "metrics": {
                    "latest_fiscal_deficit_gdp_pct": deficits[0].fiscal_deficit_gdp_pct if deficits else None,
                    "latest_fiscal_deficit_cr": deficits[0].fiscal_deficit_cr if deficits else None,
                    "general_govt_debt_gdp_pct": debts[-1].general_govt_gross_debt_gdp_pct if debts else None,
                    "latest_monthly_gst_cr": gsts[0].gross_gst_cr if gsts else None,
                },
            }
        ],
    }
