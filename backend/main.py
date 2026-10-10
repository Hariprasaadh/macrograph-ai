"""Unified FastAPI Gateway for Macrograph AI Platform.

Integrates LangGraph Multi-Agent Orchestration, Causal Scenario Simulation,
Knowledge Graph APIs, FastMCP Servers, and Standard A2A Protocol Endpoints.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import dataclasses

from core.config import settings
from core.protocols.a2a import agent_registry
from core.protocols.a2a.dependencies import CROSS_SECTOR_DEPENDENCIES
from core.protocols.a2a.api import router as a2a_api_router
from core.knowledge_graph.networkx_engine import graph_engine
from core.knowledge_graph.neo4j_store import neo4j_store
from core.econometrics.causal_engine import causal_engine
from core.orchestrator.graph import macro_orchestrator_graph
from core.orchestrator.state import OrchestratorState
from api.dashboard import router as dashboard_router
from api.chat import router as chat_router

# Sector FastMCP servers and Sub-apps (dynamically registered as implemented)
from real_sector.mcp_server import mcp_server as real_mcp
from real_sector.api.app import app as real_app
from finance_sector.mcp_server import mcp_server as finance_mcp
from finance_sector.api.app import app as finance_app
from fiscal_sector.mcp_server import mcp_server as fiscal_mcp
from fiscal_sector.api.app import app as fiscal_app
from fiscal_sector.agent import fiscal_agent_node, is_direct_fiscal_query
from external_sector.mcp_server import mcp_server as external_mcp
from capital_market_sector.mcp_server import mcp_server as capital_market_mcp
from labour_sector.mcp_server import mcp_server as labour_mcp
from monetary_sector.mcp_server import mcp_server as monetary_mcp
from agriculture_sector.api.app import mcp_http_app as agriculture_mcp_http
from agriculture_sector.agent import (
    agriculture_agent_node, select_agriculture_tools,
    _SERVICE_KEYWORDS as _AGRICULTURE_SERVICE_KEYWORDS,
)
from prices_sector.agent import prices_agent_node, is_direct_prices_query


@asynccontextmanager
async def gateway_lifespan(application: FastAPI):
    # Mounted sub-app lifespans are not run by FastAPI automatically.
    if neo4j_store.enabled:
        synced = await run_in_threadpool(neo4j_store.sync_ontology)
        logging.getLogger(__name__).info("Neo4j ontology mirror sync ok=%s", synced)
    # Optional 08:15 IST daily brief loop; off unless BRIEF_CRON_ENABLED=true so existing runs/tests are unaffected.
    brief_task = None
    if os.getenv("BRIEF_CRON_ENABLED", "false").lower() == "true":
        try:
            from core.briefing.job import brief_cron_loop
            brief_task = asyncio.create_task(brief_cron_loop())
        except Exception as exc:
            logging.getLogger(__name__).warning("Daily brief loop not started: %s", exc)
    async with agriculture_mcp_http.lifespan(agriculture_mcp_http):
        yield
    if brief_task is not None:
        brief_task.cancel()
    neo4j_store.close()

app = FastAPI(
    title="Macrograph AI — Indian Macroeconomic Intelligence Platform",
    description="Multi-Agent Macroeconomic Research, Knowledge Graph, Causal Simulation, and A2A Protocol Gateway.",
    version="1.0.0",
    lifespan=gateway_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount implemented core sub-applications
app.mount("/real-sector", real_app)
app.mount("/finance-sector", finance_app)
app.mount("/fiscal-sector", fiscal_app)

# Ensure Real Sector and Fiscal Sector DuckDB are initialised + seeded at import time
# (sub-app lifespans don't fire when mounted via app.mount)
try:
    from real_sector import database as _real_db
    _real_db.initialise_schema(seed_baseline=True)
    logging.getLogger(__name__).info("Real sector DuckDB initialised.")
except Exception as _e:
    logging.getLogger(__name__).warning("Real sector DB init skipped: %s", _e)

# Ensure Services Sector DuckDB is initialised + seeded at import time
try:
    from services_sector import database as _services_db
    _services_db.initialise_schema(seed_baseline=True)
    logging.getLogger(__name__).info("Services sector DuckDB initialised.")
except Exception as _e:
    logging.getLogger(__name__).warning("Services sector DB init skipped: %s", _e)

# Ensure Finance Sector DuckDB is initialised + seeded at import time
try:
    from finance_sector import database as _fin_db
    _fin_db.initialise_schema(seed_baseline=True)
    logging.getLogger(__name__).info("Finance sector DuckDB initialised.")
except Exception as _e:
    logging.getLogger(__name__).warning("Finance sector DB init skipped: %s", _e)

# Ensure Fiscal Sector DuckDB is initialised + seeded at import time
try:
    from fiscal_sector import database as _fiscal_db
    _fiscal_db.initialise_schema(seed_baseline=True)
    logging.getLogger(__name__).info("Fiscal sector DuckDB initialised.")
except Exception as _e:
    logging.getLogger(__name__).warning("Fiscal sector DB init skipped: %s", _e)

# Dynamically mount other sectors if available
_optional_sectors = [
    ("capital_market_sector.api.app", "app", "/capital-markets"),
    ("labour_sector.api.app", "app", "/labour-sector"),
    ("agriculture_sector.api.app", "app", "/agriculture-sector"),
    ("external_sector.api.app", "app", "/external-sector"),
    ("prices_sector.api.app", "app", "/prices-sector"),
    ("monetary_sector.api.app", "app", "/monetary-sector"),
    ("services_sector.api.app", "app", "/services-sector"),
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
class ScenarioShock(BaseModel):
    variable: str = Field(default="in.macro.prices.brent_crude", description="Canonical indicator ID to shock")
    magnitude: float = Field(default=20.0, description="Shock size in indicator units")
    name: str = Field(default="Simulated Macro Shock", description="Scenario label")


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Macroeconomic research query")
    scenario_shock: Optional[ScenarioShock] = Field(
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
@app.get("/", tags=["System"])
def root() -> Dict[str, Any]:
    return {
        "platform": "Macrograph AI — Indian Macroeconomic Intelligence Platform",
        "status": "online",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "sectors": {
            "real_sector": "/real-sector",
            "finance_sector": "/finance-sector",
            "services_sector": "/services-sector",
            "capital_markets": "/capital-markets",
            "labour_sector": "/labour-sector",
            "external_sector": "/external-sector",
            "monetary_sector": "/monetary-sector",
        },
        "chat_endpoint": "/api/v1/chat",
        "analyze_endpoint": "/api/v1/analyze",
    }


@app.get("/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    active_count = len(agent_registry.list_agents())
    return {
        "status": "healthy",
        "platform": "Macrograph AI",
        "version": "1.0.0",
        "sectors_active": active_count if active_count > 0 else 8,
        "knowledge_graph_nodes": graph_engine.graph.number_of_nodes(),
        "knowledge_graph_edges": graph_engine.graph.number_of_edges(),
        "neo4j_enabled": neo4j_store.enabled,
    }


@app.post("/api/v1/analyze", tags=["Orchestrator"])
async def analyze_macro_query(request: AnalyzeRequest) -> Dict[str, Any]:
    """Executes the LangGraph multi-agent research workflow asynchronously."""
    initial_state: OrchestratorState = {
        "query": request.query,
        "scenario_shock": request.scenario_shock.model_dump() if request.scenario_shock else None,
        "status": "started"
    }

    try:
        final_state = await run_in_threadpool(macro_orchestrator_graph.invoke, initial_state)
        return {
            "query": request.query,
            "status": final_state.get("status"),
            "target_sectors": final_state.get("target_sectors"),
            "collected_observations": final_state.get("collected_observations"),
            "causal_paths": final_state.get("causal_paths"),
            "scenario_result": final_state.get("scenario_result"),
            "mermaid_diagram": final_state.get("mermaid_diagram"),
            "report_markdown": final_state.get("final_report"),
            "final_report": final_state.get("final_report"),
            "confidence_score": final_state.get("confidence_score")
        }
    except Exception as err:
        logging.getLogger("macrograph.main").exception("Orchestration failure for query=%s", request.query)
        raise HTTPException(status_code=500, detail="An internal orchestration error occurred. Please try again.")


@app.post("/api/v1/simulate", tags=["Econometrics"])
async def simulate_scenario(request: ScenarioSimulateRequest) -> Dict[str, Any]:
    """Runs a multi-variable macroeconomic impulse response simulation asynchronously."""
    try:
        res = await run_in_threadpool(
            causal_engine.simulate_scenario,
            scenario_name=request.scenario_name,
            shock_variable=request.shock_variable,
            shock_magnitude=request.shock_magnitude,
            horizon_periods=request.horizon_periods,
        )
        return res.model_dump()
    except Exception as err:
        logging.getLogger("macrograph.main").exception("Simulation error for scenario=%s", request.scenario_name)
        raise HTTPException(status_code=500, detail="Simulation error: internal failure")


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
    """Returns all registered A2A Agent Cards, discoverable skills, and dependencies."""
    return {
        "agents": [card.model_dump() for card in agent_registry.list_agents()],
        "dependencies": [dataclasses.asdict(d) for d in CROSS_SECTOR_DEPENDENCIES],
    }


# Mount Modular Application Routers
app.include_router(a2a_api_router)
app.include_router(dashboard_router)
app.include_router(chat_router)

# Optional research routers: a failure here must never block gateway startup.
import importlib
for _router_mod in ("api.research", "api.brief"):
    try:
        app.include_router(importlib.import_module(_router_mod).router)
    except Exception as _exc:
        logging.getLogger(__name__).warning("Optional router %s skipped: %s", _router_mod, _exc)
