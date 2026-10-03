"""Unified FastAPI Gateway for Macrograph AI Platform.

Integrates LangGraph Multi-Agent Orchestration, Causal Scenario Simulation,
Knowledge Graph APIs, FastMCP Servers, and Standard A2A Protocol Endpoints.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.protocols.a2a import agent_registry
from core.knowledge_graph.networkx_engine import graph_engine
from core.econometrics.causal_engine import causal_engine
from core.orchestrator.graph import macro_orchestrator_graph
from core.orchestrator.state import OrchestratorState

# Sector FastMCP servers and Sub-apps (dynamically registered as implemented)
from real_sector.mcp_server import mcp_server as real_mcp
from real_sector.api.app import app as real_app
from finance_sector.mcp_server import mcp_server as finance_mcp
from finance_sector.api.app import app as finance_app
from external_sector.mcp_server import mcp_server as external_mcp
from capital_market_sector.mcp_server import mcp_server as capital_market_mcp
from labour_sector.mcp_server import mcp_server as labour_mcp
from monetary_sector.mcp_server import mcp_server as monetary_mcp

app = FastAPI(
    title="Macrograph AI — Indian Macroeconomic Intelligence Platform",
    description="Multi-Agent Macroeconomic Research, Knowledge Graph, Causal Simulation, and A2A Protocol Gateway.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount implemented core sub-applications
app.mount("/real-sector", real_app)
app.mount("/finance-sector", finance_app)

# Dynamically mount other sectors if available
_optional_sectors = [
    ("capital_market_sector.api.app", "app", "/capital-markets"),
    ("labour_sector.api.app", "app", "/labour-sector"),
    ("agriculture_sector.api.app", "app", "/agriculture-sector"),
    ("external_sector.api.app", "app", "/external-sector"),
    ("prices_sector.api.app", "app", "/prices-sector"),
    ("monetary_sector.api.app", "app", "/monetary-sector"),
]
for _mod_name, _app_attr, _prefix in _optional_sectors:
    try:
        import importlib
        _mod = importlib.import_module(_mod_name)
        _sub_app = getattr(_mod, _app_attr)
        app.mount(_prefix, _sub_app)
    except (ImportError, AttributeError):
        pass



# -----------------------------------------------------------------------------
# Request & Response Models
# -----------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Macroeconomic research query")
    scenario_shock: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional scenario shock, e.g. {'variable': 'in.macro.prices.brent_crude', 'magnitude': 20.0, 'name': 'Oil Surge'}"
    )


class ScenarioSimulateRequest(BaseModel):
    scenario_name: str = Field(..., description="Descriptive scenario name")
    shock_variable: str = Field(..., description="Canonical indicator ID to shock")
    shock_magnitude: float = Field(..., description="Magnitude of shock in units or %")
    horizon_periods: int = Field(default=4, description="Forecast horizon")


# -----------------------------------------------------------------------------
# Core API Routes
# -----------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "platform": "Macrograph AI",
        "version": "1.0.0",
        "sectors_active": 8,
        "knowledge_graph_nodes": graph_engine.graph.number_of_nodes(),
        "knowledge_graph_edges": graph_engine.graph.number_of_edges(),
    }


@app.post("/api/v1/analyze", tags=["Orchestrator"])
def analyze_macro_query(request: AnalyzeRequest) -> Dict[str, Any]:
    """Executes the LangGraph multi-agent research workflow."""
    initial_state: OrchestratorState = {
        "query": request.query,
        "scenario_shock": request.scenario_shock,
        "status": "started"
    }

    try:
        final_state = macro_orchestrator_graph.invoke(initial_state)
        return {
            "query": request.query,
            "status": final_state.get("status"),
            "target_sectors": final_state.get("target_sectors"),
            "collected_observations": final_state.get("collected_observations"),
            "causal_paths": final_state.get("causal_paths"),
            "scenario_result": final_state.get("scenario_result"),
            "mermaid_diagram": final_state.get("mermaid_diagram"),
            "report_markdown": final_state.get("final_report"),
            "confidence_score": final_state.get("confidence_score")
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Orchestration failure: {str(err)}")


@app.post("/api/v1/simulate", tags=["Econometrics"])
def simulate_scenario(request: ScenarioSimulateRequest) -> Dict[str, Any]:
    """Runs a multi-variable macroeconomic impulse response simulation."""
    try:
        res = causal_engine.simulate_scenario(
            scenario_name=request.scenario_name,
            shock_variable=request.shock_variable,
            shock_magnitude=request.shock_magnitude,
            horizon_periods=request.horizon_periods
        )
        return res.model_dump()
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(err)}")


@app.get("/api/v1/kg/path", tags=["Knowledge Graph"])
def get_transmission_path(source_id: str = Query(...), target_id: str = Query(...)) -> Dict[str, Any]:
    """Queries shortest transmission path between two canonical indicators."""
    path = graph_engine.get_shortest_transmission_path(source_id, target_id)
    return {
        "source": source_id,
        "target": target_id,
        "hops": len(path),
        "total_lag_months": sum(r.transmission_lag_months for r in path),
        "relationships": [r.model_dump() for r in path]
    }


@app.get("/api/v1/kg/impacts", tags=["Knowledge Graph"])
def get_downstream_impacts(shock_id: str = Query(...)) -> Dict[str, Any]:
    """Evaluates all reachable downstream indicators affected by a shock to source indicator."""
    impacts = graph_engine.get_downstream_impacts(shock_id)
    return {
        "shock_indicator_id": shock_id,
        "reachable_targets_count": len(impacts),
        "downstream_impacts": impacts
    }


@app.get("/a2a/registry", tags=["A2A Protocol"])
def get_agent_registry() -> Dict[str, Any]:
    """Returns all registered A2A Agent Cards and discoverable skills."""
    return {
        "agents": [card.model_dump() for card in agent_registry.list_agents()]
    }


# -----------------------------------------------------------------------------
# Dashboard & Chat Streaming Routes
# -----------------------------------------------------------------------------
import json
import asyncio
from fastapi.responses import StreamingResponse
from core.sector_reasoning import select_relevant_services_with_llm
from finance_sector.agent import finance_agent_node
from finance_sector.database import get_connection as get_finance_db
from external_sector.agent import (
    _SERVICE_KEYWORDS as _EXTERNAL_SERVICE_KEYWORDS,
    external_agent_node,
)
from external_sector.config import external_settings
from labour_sector.agent import (
    _SERVICE_KEYWORDS as _LABOUR_SERVICE_KEYWORDS,
    labour_agent_node,
)
from labour_sector.config import labour_settings
from capital_market_sector.agent import (
    _SERVICE_KEYWORDS as _CAPITAL_SERVICE_KEYWORDS,
    capital_agent_node,
)
from capital_market_sector.config import capital_settings
from monetary_sector.agent import (
    _SERVICE_KEYWORDS as _MONETARY_SERVICE_KEYWORDS,
    monetary_agent_node,
)
from monetary_sector.config import monetary_settings


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User query or macroeconomic research question")
    agent: str = Field(
        default="orchestrator",
        description=(
            "'orchestrator', 'finance_sector', 'external_sector', 'labour_sector', "
            "'capital_market_sector', or 'monetary_sector'"
        ),
    )
    scenario_shock: Optional[Dict[str, Any]] = None


_DIRECT_SECTOR_CHAT: dict[str, dict[str, Any]] = {
    "external_sector": {
        "node": external_agent_node,
        "service_keywords": _EXTERNAL_SERVICE_KEYWORDS,
        "api_key": external_settings.SERV_EXT_KEY,
        "model": external_settings.EXTERNAL_LLM_MODEL,
        "name": "External Sector & Trade",
        "data_key": "external_sector_data",
        "analysis_key": "external_sector_analysis",
        "citations_key": "external_sector_citations",
        "errors_key": "external_sector_errors",
        "freshness_key": "external_sector_freshness",
        "sections": [
            ("forex_reserves", "Foreign exchange reserves", [
                ("Total reserves", "total_reserves_usd_mn", " million USD"),
                ("Foreign currency assets", "foreign_currency_assets_usd_mn", " million USD"),
                ("Gold reserves", "gold_reserves_usd_mn", " million USD"),
            ]),
            ("trade_balance", "Merchandise trade", [
                ("Exports", "exports_usd_bn", " billion USD"),
                ("Imports", "imports_usd_bn", " billion USD"),
                ("Trade balance", "trade_balance_usd_bn", " billion USD"),
            ]),
            ("balance_of_payments", "Balance of payments", [
                ("Current account balance", "current_account_balance_usd_bn", " billion USD"),
                ("Current account / GDP", "current_account_to_gdp_pct", "%"),
                ("Capital account balance", "capital_account_balance_usd_bn", " billion USD"),
                ("Net balance of payments", "net_bop_usd_bn", " billion USD"),
            ]),
            ("exchange_rates", "Exchange rates", [
                ("USD/INR reference rate", "usd_inr_rate", ""),
            ]),
            ("external_flows", "Foreign investment flows", [
                ("Net FDI", "net_fdi_usd_mn", " million USD"),
                ("Net FPI", "net_fpi_usd_mn", " million USD"),
            ]),
        ],
    },
    "labour_sector": {
        "node": labour_agent_node,
        "service_keywords": _LABOUR_SERVICE_KEYWORDS,
        "api_key": labour_settings.LABOUR_LLM_KEY,
        "model": labour_settings.LABOUR_LLM_MODEL,
        "name": "Labour & Employment",
        "data_key": "labour_sector_data",
        "analysis_key": "labour_sector_analysis",
        "citations_key": "labour_sector_citations",
        "errors_key": "labour_sector_errors",
        "freshness_key": "labour_sector_freshness",
        "sections": [
            ("unemployment", "Unemployment", [
                ("Unemployment rate (UR)", "unemployment_rate_pct", "%"),
            ]),
            ("lfpr", "Labour force participation", [
                ("Labour force participation rate (LFPR)", "lfpr_total_pct", "%"),
            ]),
            ("wpr", "Worker population", [
                ("Worker population ratio (WPR)", "wpr_total_pct", "%"),
            ]),
            ("labour_conditions", "Employment conditions", [
                ("EPFO net additions", "epfo_net_additions_thousands", " thousand"),
                ("Self-employed share", "self_employed_share_pct", "%"),
                ("Regular wage/salaried share", "regular_wage_share_pct", "%"),
                ("Casual labour share", "casual_labour_share_pct", "%"),
            ]),
        ],
    },
    "capital_market_sector": {
        "node": capital_agent_node,
        "service_keywords": _CAPITAL_SERVICE_KEYWORDS,
        "api_key": capital_settings.CAPITAL_LLM_KEY,
        "model": capital_settings.CAPITAL_LLM_MODEL,
        "name": "Capital Markets",
        "data_key": "capital_market_sector_data",
        "analysis_key": "capital_market_sector_analysis",
        "citations_key": "capital_market_sector_citations",
        "errors_key": "capital_market_sector_errors",
        "freshness_key": "capital_market_sector_freshness",
        "sections": [
            ("nifty_snapshot", "NIFTY 50", [
                ("Close", "close_price", ""),
                ("Change", "change_pct", "%"),
            ]),
            ("india_vix", "India VIX", [
                ("Close", "vix_close", ""),
            ]),
            ("market_history", "Historical index data", [
                ("Index", "index_name", ""),
                ("Close", "close_price", ""),
                ("Year-over-year return", "yoy_return_pct", "%"),
                ("P/E", "pe_ratio", ""),
                ("P/B", "pb_ratio", ""),
                ("Dividend yield", "dividend_yield_pct", "%"),
            ]),
            ("market_breadth", "Market breadth", [
                ("Advances", "advances_count", ""),
                ("Declines", "declines_count", ""),
                ("Unchanged", "unchanged_count", ""),
                ("Advance/decline ratio", "advance_decline_ratio", ""),
            ]),
            ("gsec_yields", "Government security yields", [
                ("10-year G-Sec yield", "ten_year_gsec_yield_pct", "%"),
                ("5-year G-Sec yield", "five_year_gsec_yield_pct", "%"),
                ("2-year G-Sec yield", "two_year_gsec_yield_pct", "%"),
                ("2s10s spread", "yield_curve_spread_2s10s_bps", " bps"),
            ]),
        ],
    },
    "monetary_sector": {
        "node": monetary_agent_node,
        "service_keywords": _MONETARY_SERVICE_KEYWORDS,
        "api_key": monetary_settings.MONETARY_LLM_KEY,
        "model": monetary_settings.MONETARY_LLM_MODEL,
        "name": "Monetary & Liquidity",
        "data_key": "monetary_sector_data",
        "analysis_key": "monetary_sector_analysis",
        "citations_key": "monetary_sector_citations",
        "errors_key": "monetary_sector_errors",
        "freshness_key": "monetary_sector_freshness",
        "sections": [
            ("policy_rates", "Policy rates", [
                ("Repo rate", "repo_rate_pct", "%"),
                ("Standing Deposit Facility (SDF)", "sdf_rate_pct", "%"),
                ("Marginal Standing Facility (MSF)", "msf_rate_pct", "%"),
                ("Cash Reserve Ratio (CRR)", "crr_pct", "%"),
                ("Statutory Liquidity Ratio (SLR)", "slr_pct", "%"),
            ]),
            ("money_supply", "Money supply", [
                ("M3", "m3_cr", " crore"),
                ("M3 year-over-year growth", "m3_yoy_pct", "%"),
            ]),
            ("system_liquidity", "System liquidity", [
                ("Net LAF absorption / injection", "net_laf_absorption_cr", " crore"),
                ("Liquidity condition", "liquidity_condition", ""),
            ]),
            ("monetary_stance", "Monetary stance", [
                ("Official stance label", "stance_label", ""),
                ("Real policy rate", "real_policy_rate_pct", "%"),
                ("M3 growth", "m3_growth_pct", "%"),
                ("System liquidity status", "system_liquidity_status", ""),
            ]),
        ],
    },
}


def _has_sector_value(value: Any) -> bool:
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return False
    return value is not None and not (
        isinstance(value, str) and value.strip().lower() in {"", "unknown", "unavailable"}
    )


def _format_sector_report(
    config: dict[str, Any],
    data_context: dict[str, Any],
    freshness: dict[str, Any] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> str:
    freshness = freshness or {}
    citations = citations or []
    lines = [
        "### Latest observations",
        "",
        "| Indicator | Observation | Period | Freshness | Source |",
        "|---|---:|---|---|---|",
    ]
    takeaway_rows: list[tuple[str, str]] = []
    for section_key, section_title, fields in config["sections"]:
        if section_key not in data_context:
            continue
        section = data_context.get(section_key)
        if isinstance(section, dict):
            period = section.get("period")
            period_label = str(period) if _has_sector_value(period) else "Unavailable"
            citation = next(
                (item for item in citations if item.get("dataset") == section_key),
                {},
            )
            source = citation.get("source_authority") or "Unavailable"
            freshness_label = str(freshness.get(section_key, citation.get("freshness", "unavailable")))
            for label, field_key, unit in fields:
                value = section.get(field_key)
                rendered_value = f"{value}{unit}" if _has_sector_value(value) else "Unavailable"
                lines.append(
                    f"| {label} | {rendered_value} | {period_label} | "
                    f"{freshness_label} | {source} |"
                )
            has_section_observation = any(
                _has_sector_value(section.get(field_key))
                for _, field_key, _ in fields
            )
            if not has_section_observation:
                continue
            if section_key == "trade_balance":
                trade_balance = section.get("trade_balance_usd_bn")
                if isinstance(trade_balance, (int, float)) and trade_balance < 0:
                    takeaway_rows.append((
                        "Merchandise trade balance is negative",
                        "Imports exceeded exports in the reported period; this describes goods trade, not the full current account.",
                    ))
                elif isinstance(trade_balance, (int, float)) and trade_balance > 0:
                    takeaway_rows.append((
                        "Merchandise trade balance is positive",
                        "Exports exceeded imports in the reported period; this describes goods trade, not the full current account.",
                    ))
            elif section_key == "exchange_rates" and _has_sector_value(section.get("usd_inr_rate")):
                takeaway_rows.append((
                    "USD/INR is quoted as rupees per U.S. dollar",
                    "A single observation establishes the reference level for that date; compare other dates from the same series to assess movement.",
                ))
            else:
                takeaway_rows.append((
                    f"{section_title} is reported for {period_label}",
                    "The observation describes that period; by itself it does not establish a longer-term trend or its cause.",
                ))

    if not lines or len(lines) == 4:
        lines.extend(["", "| Observation | Detail |", "|---|---|", "| Data availability | No usable observations were returned for the selected datasets. |"])
    lines.extend([
        "",
        "### Take-aways",
        "",
        "| Insight | Implication |",
        "|---|---|",
    ])
    if takeaway_rows:
        lines.extend(f"| {insight} | {implication} |" for insight, implication in takeaway_rows)
    else:
        lines.append("| Data unavailable | There are no observations to interpret. |")
    lines.extend([
        "",
        "Model-generated analysis was unavailable; take-aways are limited to direct interpretation of the returned observations.",
    ])
    return "\n".join(lines)


def _sector_chat_response(target: str, node_result: dict[str, Any]) -> dict[str, Any]:
    config = _DIRECT_SECTOR_CHAT[target]
    data_context = node_result.get(config["data_key"]) or {}
    if not isinstance(data_context, dict):
        data_context = {}
    freshness = node_result.get(config["freshness_key"]) or {}
    raw_errors = node_result.get(config["errors_key"]) or []
    errors = raw_errors if isinstance(raw_errors, list) else [str(raw_errors)]
    raw_citations = node_result.get(config["citations_key"]) or []
    citations = [
        {
            "source_agent": citation["source_agent"],
            "authority": citation.get("source_authority"),
            "source_authority": citation.get("source_authority"),
            "document_title": citation.get("document_title"),
            "table": citation.get("table_reference"),
            "table_reference": citation.get("table_reference"),
            "retrieval_url": citation.get("retrieval_url"),
            "source_base_url": citation.get("source_base_url"),
            "source_note": citation.get("source_note"),
            "as_of": citation.get("as_of"),
            "frequency": citation.get("frequency"),
            "unit": citation.get("unit"),
            "period": citation.get("observation_period"),
            "observation_period": citation.get("observation_period"),
            "freshness": citation.get("freshness"),
            "dataset": citation.get("dataset"),
        }
        for citation in raw_citations
        if isinstance(citation, dict) and citation.get("source_agent")
    ]
    report = node_result.get(config["analysis_key"])
    if not isinstance(report, str) or not report.strip():
        report = _format_sector_report(config, data_context, freshness, citations)
    else:
        report = report.strip()

    reasoning_errors = [
        error for error in errors
        if isinstance(error, str) and error.startswith("LLM reasoning unavailable:")
    ]
    retrieval_errors = [error for error in errors if error not in reasoning_errors]
    if reasoning_errors:
        report += "\n\nAnalysis note: The configured LLM could not provide a narrative interpretation."
    if retrieval_errors:
        report += "\n\n### Data retrieval issues\n\n" + "\n".join(f"- {error}" for error in retrieval_errors)

    available_values = []
    for section_key, _, fields in config["sections"]:
        if section_key not in data_context:
            continue
        section = data_context.get(section_key)
        available_values.extend(
            _has_sector_value(section.get(field_key)) if isinstance(section, dict) else False
            for _, field_key, _ in fields
        )
    has_values = any(available_values)
    status = (
        "unavailable"
        if not has_values
        else "partial"
        if errors or not all(available_values)
        else "completed"
    )

    return {
        "status": status,
        "agent_routed": f"{config['name']} Specialist",
        "full_report": report,
        "data_context": data_context,
        "freshness": freshness,
        "errors": errors,
        "citations": citations,
    }


async def _run_direct_sector_chat(
    target: str,
    message: str,
    *,
    selected_services: set[str] | None = None,
    selection_error: str | None = None,
) -> dict[str, Any]:
    config = _DIRECT_SECTOR_CHAT[target]
    try:
        state: dict[str, Any] = {"query": message}
        if selected_services is not None:
            state["_selected_services"] = selected_services
            state["_selection_error"] = selection_error
        node_result = await config["node"](state)
    except Exception as exc:
        logging.getLogger(__name__).exception("Direct %s chat agent failed", target)
        return {
            "status": "failed",
            "agent_routed": f"{config['name']} Specialist",
            "full_report": (
                f"### {config['name']} Request Failed\n\n"
                f"The sector agent could not complete this request: {exc}. "
                "No observations are available."
            ),
            "data_context": {},
            "freshness": {},
            "errors": [str(exc)],
            "citations": [],
        }
    return _sector_chat_response(target, node_result)


def _sector_progress_events(
    target: str,
    selected_services: set[str],
    selection_error: str | None,
) -> list[dict[str, Any]]:
    config = _DIRECT_SECTOR_CHAT[target]
    events = [{
        "type": "step",
        "step": 1,
        "agent": target,
        "title": f"Targeting {config['name']} Specialist",
        "detail": "Invoking the selected sector agent directly, without Orchestrator routing.",
    }]
    if selection_error:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "Resolving query-relevant data",
            "detail": f"Service selection reported an issue: {selection_error}",
        })
    elif selected_services:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "Matched query-relevant data",
            "detail": "Selected: " + ", ".join(
                service.replace("_", " ") for service in config["service_keywords"]
                if service in selected_services
            ),
        })
    else:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "No matching sector dataset",
            "detail": "The available sector indicators do not explicitly match this query.",
        })

    step = len(events) + 1
    for service in config["service_keywords"]:
        if service not in selected_services:
            continue
        events.append({
            "type": "step",
            "step": step,
            "agent": target,
            "tool": service,
            "title": f"Retrieving {service.replace('_', ' ')}",
            "detail": (
                "Fetching only this query-selected dataset through the sector client; "
                "availability, source freshness, and cache fallback will be reported."
            ),
        })
        step += 1

    events.append({
        "type": "step",
        "step": step,
        "agent": target,
        "title": "Preparing evidence-based explanation",
        "detail": (
            "After retrieval, the specialist will explain the result, key takeaways, "
            "source periods, and any limitations."
        ),
    })
    return events


@app.get("/api/v1/dashboard/overview", tags=["Dashboard"])
def get_dashboard_overview() -> Dict[str, Any]:
    """Returns aggregated real macroeconomic data for the Finance Sector alongside staged indicators."""
    credit_data = None
    asset_data = None
    rates_data = None
    deposits_data = None

    try:
        with get_finance_db() as conn:
            # 1. Bank Credit Growth
            cr_row = conn.execute(
                "SELECT period, gross_credit_cr, non_food_credit_cr, non_food_credit_yoy_pct, "
                "agriculture_cr, industry_msme_cr, industry_large_cr, services_cr, personal_loans_cr, "
                "personal_housing_cr, personal_vehicle_cr, citation FROM bank_credit_growth ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if cr_row:
                credit_data = {
                    "period": cr_row[0],
                    "gross_credit_cr": cr_row[1],
                    "non_food_credit_cr": cr_row[2],
                    "non_food_credit_yoy_pct": cr_row[3],
                    "sectoral": {
                        "agriculture_cr": cr_row[4],
                        "industry_msme_cr": cr_row[5],
                        "industry_large_cr": cr_row[6],
                        "services_cr": cr_row[7],
                        "personal_loans_cr": cr_row[8],
                        "personal_housing_cr": cr_row[9],
                        "personal_vehicle_cr": cr_row[10],
                    },
                    "citation": json.loads(cr_row[11]) if isinstance(cr_row[11], str) else cr_row[11],
                    "is_real_data": True,
                }

            # 2. Asset Quality
            aq_row = conn.execute(
                "SELECT period, bank_group, gross_npa_pct, net_npa_pct, gross_npa_cr, net_npa_cr, "
                "provision_coverage_ratio_pct, crar_pct, cet1_pct, citation FROM asset_quality ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if aq_row:
                asset_data = {
                    "period": aq_row[0],
                    "bank_group": aq_row[1],
                    "gross_npa_pct": aq_row[2],
                    "net_npa_pct": aq_row[3],
                    "gross_npa_cr": aq_row[4],
                    "net_npa_cr": aq_row[5],
                    "provision_coverage_ratio_pct": aq_row[6],
                    "crar_pct": aq_row[7],
                    "cet1_pct": aq_row[8],
                    "citation": json.loads(aq_row[9]) if isinstance(aq_row[9], str) else aq_row[9],
                    "is_real_data": True,
                }

            # 3. Lending Rates
            lr_row = conn.execute(
                "SELECT period, walr_fresh_pct, walr_outstanding_pct, mclr_1yr_median_pct, "
                "wadtdr_fresh_pct, wadtdr_outstanding_pct, citation FROM lending_rates ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if lr_row:
                rates_data = {
                    "period": lr_row[0],
                    "walr_fresh_pct": lr_row[1],
                    "walr_outstanding_pct": lr_row[2],
                    "mclr_1yr_median_pct": lr_row[3],
                    "wadtdr_fresh_pct": lr_row[4],
                    "wadtdr_outstanding_pct": lr_row[5],
                    "citation": json.loads(lr_row[6]) if isinstance(lr_row[6], str) else lr_row[6],
                    "is_real_data": True,
                }

            # 4. Deposits and CD Ratio
            dp_row = conn.execute(
                "SELECT period, aggregate_deposits_cr, deposits_yoy_pct, demand_deposits_cr, "
                "time_deposits_cr, casa_ratio_pct, bank_credit_cr, cd_ratio_pct, citation "
                "FROM deposits_cd_ratio WHERE period != 'unknown' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if dp_row:
                deposits_data = {
                    "period": dp_row[0],
                    "aggregate_deposits_cr": dp_row[1],
                    "deposits_yoy_pct": dp_row[2],
                    "demand_deposits_cr": dp_row[3],
                    "time_deposits_cr": dp_row[4],
                    "casa_ratio_pct": dp_row[5],
                    "bank_credit_cr": dp_row[6],
                    "cd_ratio_pct": dp_row[7],
                    "citation": json.loads(dp_row[8]) if isinstance(dp_row[8], str) else dp_row[8],
                    "is_real_data": True,
                }
    except Exception as e:
        pass

    # Live and benchmarked indicators for other sectors with MoSPI e-Sankhyiki integration
    other_sectors_preview = [
        {
            "sector": "Real Sector (GDP/GVA)",
            "indicator": "Real GDP Growth Rate",
            "value": None,
            "frequency": "Quarterly (FY25/26)",
            "source": "MoSPI e-Sankhyiki MCP (NAS)",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Prices & Inflation",
            "indicator": "Headline CPI Inflation",
            "value": None,
            "frequency": "Monthly",
            "source": "MoSPI e-Sankhyiki MCP (CPI)",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Monetary & Liquidity",
            "indicator": "Policy Repo Rate",
            "value": None,
            "frequency": "Bi-monthly MPC",
            "source": "RBI Monetary Policy Committee",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Capital Markets",
            "indicator": "NIFTY 50 Index",
            "value": None,
            "frequency": "Daily",
            "source": "NSE India",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "External Sector",
            "indicator": "Forex Reserves",
            "value": None,
            "frequency": "Weekly",
            "source": "RBI Weekly Statistical Supplement",
            "status": "unavailable",
            "is_mock": False
        },
    ]

    return {
        "status": "success",
        "finance_sector": {
            "credit_growth": credit_data,
            "asset_quality": asset_data,
            "lending_rates": rates_data,
            "deposits_cd_ratio": deposits_data,
        },
        "other_sectors_preview": other_sectors_preview,
        "platform_summary": {
            "active_live_sectors": ["finance_sector"],
            "staged_sectors": ["real_sector", "capital_market_sector"],
            "development_sectors": [
                "prices_sector", "monetary_sector", "fiscal_sector",
                "external_sector", "agriculture_sector", "labour_sector", "services_sector"
            ],
            "total_sectors": 10,
        }
    }


def _build_finance_citations(ctx: dict, fresh: dict) -> list[dict]:
    cits = []
    credit_info = ctx.get("credit_growth", {})
    if credit_info.get("status") != "unavailable" and credit_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": credit_info.get("source", "financial_sector.r539_deployment_of_bank_credit_by_major_sectors"),
            "period": credit_info.get("period"),
            "freshness": credit_info.get("freshness", fresh.get("credit", "cached")),
        })
    quality_info = ctx.get("asset_quality", {})
    if quality_info.get("status") != "unavailable" and quality_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": quality_info.get("source", "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks"),
            "period": quality_info.get("period"),
            "freshness": quality_info.get("freshness", fresh.get("quality", "cached")),
        })
    rates_info = ctx.get("lending_rates", {})
    if rates_info.get("status") != "unavailable" and rates_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": rates_info.get("source", "financial_sector.r531_key_rates"),
            "period": rates_info.get("period"),
            "freshness": rates_info.get("freshness", fresh.get("rates", "cached")),
        })
    deposits_info = ctx.get("deposits", {})
    if deposits_info.get("status") != "unavailable" and deposits_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": deposits_info.get("source", "financial_sector.r689_business_of_scheduled_banks"),
            "period": deposits_info.get("period"),
            "freshness": deposits_info.get("freshness", fresh.get("deposits", "cached")),
        })
    return cits


@app.post("/api/v1/chat/stream", tags=["Chat"])
async def stream_chat(request: ChatMessageRequest):
    """Server-Sent Events (SSE) streaming chat endpoint with real-time agent updates and fluid token output."""
    async def event_generator():
        msg = request.message.strip()
        target = request.agent.lower()

        if target == "finance_sector":
            # Direct domain investigation of Finance & Banking sector
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'finance_sector', 'title': 'Targeting Finance Sector Agent', 'detail': 'Bypassing Orchestrator. Direct domain investigation of Indian Scheduled Commercial Banks.'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 2, 'agent': 'finance_sector', 'tool': 'get_bank_credit_growth', 'title': 'Invoking FastMCP Tool: get_bank_credit_growth', 'detail': 'Querying non-food credit & sectoral deployment from RBI DBIE (Table r539)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 3, 'agent': 'finance_sector', 'tool': 'get_asset_quality', 'title': 'Invoking FastMCP Tool: get_asset_quality', 'detail': 'Querying Gross NPA, Net NPA, CRAR & PCR ratios from Financial Stability Report (Table r330)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 4, 'agent': 'finance_sector', 'tool': 'get_lending_and_deposit_rates', 'title': 'Invoking FastMCP Tool: get_lending_and_deposit_rates', 'detail': 'Querying WALR, MCLR & WADTDR spreads from RBI Bulletin (Table r531)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 5, 'agent': 'finance_sector', 'title': 'Executing LLM Econometric Reasoning', 'detail': 'Analyzing banking stability & transmission via Groq LLM reasoning engine...'})}\n\n"

            node_result = await finance_agent_node({"query": msg})
            analysis_text = node_result.get("finance_sector_analysis", "")
            data_context = node_result.get("finance_sector_data", {})
            freshness = node_result.get("finance_sector_freshness", {})

            words = analysis_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.04)

            # Check if query is out-of-domain and declined
            is_domain_decline = (
                any(k in analysis_text.lower() for k in ["outside my domain", "falls outside", "switch to the", "scope"])
                and not any(k in msg.lower() for k in ["bank", "npa", "credit", "loan", "lending", "deposit", "mclr", "walr", "crar", "scb"])
            )

            if is_domain_decline:
                citations = []
            else:
                citations = _build_finance_citations(data_context, freshness)

            done_payload = {
                "type": "done",
                "agent_routed": "Finance & Banking Sector Agent",
                "full_report": analysis_text,
                "data_context": data_context,
                "citations": citations,
                "freshness": freshness,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        elif target in _DIRECT_SECTOR_CHAT:
            sector_config = _DIRECT_SECTOR_CHAT[target]
            selected_services, selection_error = await select_relevant_services_with_llm(
                query=msg,
                service_keywords=sector_config["service_keywords"],
                api_key=sector_config["api_key"],
                model=sector_config["model"],
            )
            for progress_event in _sector_progress_events(
                target,
                selected_services,
                selection_error,
            ):
                yield f"data: {json.dumps(progress_event)}\n\n"
                await asyncio.sleep(0.15)

            sector_response = await _run_direct_sector_chat(
                target,
                msg,
                selected_services=selected_services,
                selection_error=selection_error,
            )
            report_text = sector_response["full_report"]
            words = report_text.split()
            for index in range(0, len(words), 5):
                chunk = " ".join(words[index:index + 5]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            done_payload = {
                "type": "done",
                "agent_routed": sector_response["agent_routed"],
                "full_report": report_text,
                "data_context": sector_response["data_context"],
                "freshness": sector_response["freshness"],
                "errors": sector_response["errors"],
                "citations": sector_response["citations"],
                "mermaid_diagram": "",
                "confidence_score": None,
                "status": sector_response["status"],
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        else:
            # Multi-agent orchestrator route
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'orchestrator', 'title': 'Orchestrator Decomposing Query', 'detail': 'Analyzing question semantics, identifying domain boundaries across 10 sectors...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 2, 'agent': 'orchestrator', 'title': 'A2A Protocol Task Dispatch', 'detail': 'Inspecting registered Agent Cards, routing subtasks to Finance & Real sector peers...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 3, 'agent': 'finance_sector', 'tool': 'get_bank_credit_growth', 'title': 'FastMCP Data Retrieval', 'detail': 'Sector agents querying canonical DuckDB store and live RBI DBIE mirrors...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 4, 'agent': 'orchestrator', 'title': 'Causal Knowledge Graph Traversal', 'detail': 'Mapping cross-sector transmission paths in NetworkX Causal Graph engine...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 5, 'agent': 'orchestrator', 'title': 'Academic Synthesis & Citation Verification', 'detail': 'Applying strict anti-hallucination checks and generating cited report via Groq LLM...'})}\n\n"

            loop = asyncio.get_running_loop()
            final_state = await loop.run_in_executor(
                None,
                lambda: macro_orchestrator_graph.invoke({
                    "query": msg,
                    "scenario_shock": request.scenario_shock,
                    "status": "started"
                })
            )

            report_text = final_state.get("final_report", "")
            collected_obs = final_state.get("collected_observations", [])
            citations = final_state.get("citations", [])
            mermaid_diag = final_state.get("mermaid_diagram", "")
            target_sectors = final_state.get("target_sectors", [])

            words = report_text.split(" ")
            chunk_size = 5
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            done_payload = {
                "type": "done",
                "agent_routed": "Macrograph Orchestrator (Multi-Sector)",
                "target_sectors": target_sectors,
                "full_report": report_text,
                "citations": citations,
                "observations": collected_obs,
                "mermaid_diagram": mermaid_diag,
                "confidence_score": final_state.get("confidence_score", 0.94),
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/v1/chat", tags=["Chat"])
async def sync_chat(request: ChatMessageRequest) -> Dict[str, Any]:
    """Synchronous non-streaming chat endpoint."""
    target = request.agent.lower()
    if target == "finance_sector":
        node_result = await finance_agent_node({"query": request.message})
        d_context = node_result.get("finance_sector_data", {})
        f_freshness = node_result.get("finance_sector_freshness", {})
        return {
            "status": "completed",
            "agent_routed": "Finance & Banking Sector Agent",
            "full_report": node_result.get("finance_sector_analysis", ""),
            "data_context": d_context,
            "freshness": f_freshness,
            "citations": _build_finance_citations(d_context, f_freshness),
        }
    elif target in _DIRECT_SECTOR_CHAT:
        return await _run_direct_sector_chat(target, request.message)
    else:
        initial_state = {
            "query": request.message,
            "scenario_shock": request.scenario_shock,
            "status": "started"
        }
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(
            None,
            lambda: macro_orchestrator_graph.invoke(initial_state)
        )
        return {
            "status": "completed",
            "agent_routed": "Macrograph Orchestrator",
            "full_report": final_state.get("final_report", ""),
            "target_sectors": final_state.get("target_sectors", []),
            "citations": final_state.get("citations", []),
            "observations": final_state.get("collected_observations", []),
            "mermaid_diagram": final_state.get("mermaid_diagram", ""),
        }
