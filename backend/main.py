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

# Sector FastMCP servers
from real_sector.mcp_server import mcp_server as real_mcp
from finance_sector.mcp_server import mcp_server as finance_mcp
from capital_market_sector.mcp_server import mcp_server as capital_mcp
from prices_sector.mcp_server import mcp_server as prices_mcp
from monetary_sector.mcp_server import mcp_server as monetary_mcp
from labour_sector.mcp_server import mcp_server as labour_mcp

# Sub-apps
from real_sector.api.app import app as real_app
from finance_sector.api.app import app as finance_app
from capital_market_sector.api.app import app as capital_app

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

# Mount sector sub-applications
app.mount("/real-sector", real_app)
app.mount("/finance-sector", finance_app)
app.mount("/capital-markets", capital_app)


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
