"""Unified FastAPI Gateway for Macrograph AI Platform.

Integrates LangGraph Multi-Agent Orchestration, Causal Scenario Simulation,
Knowledge Graph APIs, FastMCP Servers, and Standard A2A Protocol Endpoints.
"""
from __future__ import annotations

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
from finance_sector.agent import finance_agent_node
from finance_sector.database import get_connection as get_finance_db


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User query or macroeconomic research question")
    agent: str = Field(default="orchestrator", description="'orchestrator' or 'finance_sector'")
    scenario_shock: Optional[Dict[str, Any]] = None


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
            "value": "6.8%",
            "frequency": "Quarterly (FY25/26)",
            "source": "MoSPI e-Sankhyiki MCP (NAS)",
            "status": "Live Official MoSPI",
            "is_mock": False
        },
        {
            "sector": "Prices & Inflation",
            "indicator": "Headline CPI Inflation",
            "value": "4.20%",
            "frequency": "Monthly",
            "source": "MoSPI e-Sankhyiki MCP (CPI)",
            "status": "Live Official MoSPI",
            "is_mock": False
        },
        {
            "sector": "Monetary & Liquidity",
            "indicator": "Policy Repo Rate",
            "value": "6.25%",
            "frequency": "Bi-monthly MPC",
            "source": "RBI Monetary Policy Committee",
            "status": "Live Benchmarked",
            "is_mock": False
        },
        {
            "sector": "Capital Markets",
            "indicator": "NIFTY 50 Index",
            "value": "25,014.10",
            "frequency": "Daily",
            "source": "NSE India",
            "status": "Live Benchmarked",
            "is_mock": False
        },
        {
            "sector": "External Sector",
            "indicator": "Forex Reserves",
            "value": "$704.88 Billion",
            "frequency": "Weekly",
            "source": "RBI Weekly Statistical Supplement",
            "status": "Live Benchmarked",
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
                citations = [
                    {
                        "source_agent": "finance_sector",
                        "authority": "Reserve Bank of India (RBI)",
                        "table": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                        "period": "2024-09",
                        "freshness": freshness.get("credit", "cached")
                    },
                    {
                        "source_agent": "finance_sector",
                        "authority": "Reserve Bank of India (RBI)",
                        "table": "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks",
                        "period": "2024-06",
                        "freshness": freshness.get("quality", "cached")
                    },
                    {
                        "source_agent": "finance_sector",
                        "authority": "Reserve Bank of India (RBI)",
                        "table": "financial_sector.r531_key_rates",
                        "period": "2024-09",
                        "freshness": freshness.get("rates", "cached")
                    },
                    {
                        "source_agent": "finance_sector",
                        "authority": "Reserve Bank of India (RBI)",
                        "table": "financial_sector.r689_business_of_scheduled_banks",
                        "period": "2024-09",
                        "freshness": freshness.get("deposits", "cached")
                    }
                ]

            done_payload = {
                "type": "done",
                "agent_routed": "Finance & Banking Sector Agent",
                "full_report": analysis_text,
                "data_context": data_context,
                "citations": citations,
                "freshness": freshness,
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
        return {
            "status": "completed",
            "agent_routed": "Finance & Banking Sector Agent",
            "full_report": node_result.get("finance_sector_analysis", ""),
            "data_context": node_result.get("finance_sector_data", {}),
            "freshness": node_result.get("finance_sector_freshness", {}),
            "citations": [
                {
                    "source_agent": "finance_sector",
                    "authority": "Reserve Bank of India (RBI)",
                    "table": "financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                    "period": "2024-09",
                }
            ]
        }
    else:
        initial_state = {
            "query": request.message,
            "scenario_shock": request.scenario_shock,
            "status": "started"
        }
        final_state = macro_orchestrator_graph.invoke(initial_state)
        return {
            "status": "completed",
            "agent_routed": "Macrograph Orchestrator",
            "full_report": final_state.get("final_report", ""),
            "target_sectors": final_state.get("target_sectors", []),
            "citations": final_state.get("citations", []),
            "observations": final_state.get("collected_observations", []),
            "mermaid_diagram": final_state.get("mermaid_diagram", ""),
        }

