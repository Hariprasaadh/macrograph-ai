"""Research-lab endpoints: shockwave, twin, anomaly radar, MPC, edge audit and the graph for the SVG."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.knowledge_graph.networkx_engine import graph_engine
from core.research.anomaly import scan
from core.research.attribution import compare
from core.research.edge_audit import audit_edges, edge_note
from core.research.mpc import simulate_mpc
from core.research.trajectory import build_trajectory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/research", tags=["Research"])


class TrajectoryRequest(BaseModel):
    shock_variable: str = "in.macro.prices.brent_crude"
    shock_magnitude: float = 20.0
    horizon_months: int = Field(default=12, ge=1, le=60)
    shape: str = "step"
    half_life_months: Optional[float] = None


class CompareRequest(BaseModel):
    shock_variable: str = "in.macro.prices.brent_crude"
    shock_magnitude: float = 20.0


class MpcRequest(BaseModel):
    use_llm: bool = True


@router.get("/kg/graph")
def kg_graph() -> Dict[str, Any]:
    nodes = [{"id": nid, "name": d.get("name", nid), "sector": d.get("sector", ""), "unit": d.get("unit", "")}
             for nid, d in graph_engine.graph.nodes(data=True)]
    edges = [{"relation_id": rel.relation_id, "from": rel.source_indicator_id, "to": rel.target_indicator_id,
              "lag_months": rel.transmission_lag_months, "confidence": rel.confidence_score,
              "sign": rel.elasticity_sign, "type": rel.relation_type.value, "mechanism": rel.mechanism_description,
              "seeded_p": rel.empirical_p_value, "note": edge_note(rel.source_indicator_id, rel.target_indicator_id)}
             for rel in graph_engine.ontology.relationships]
    return {"nodes": nodes, "edges": edges}


@router.get("/edges/audit")
async def edges_audit() -> Dict[str, Any]:
    rows = await run_in_threadpool(audit_edges)
    return {"rows": rows, "empirical": sum(1 for r in rows if r["evidence_class"] == "EMPIRICAL"), "total": len(rows)}


@router.post("/trajectory")
async def trajectory(req: TrajectoryRequest) -> Dict[str, Any]:
    try:
        return await run_in_threadpool(build_trajectory, req.shock_variable, req.shock_magnitude,
                                       req.horizon_months, req.shape, req.half_life_months)
    except Exception:  # noqa: BLE001
        logger.exception("trajectory failed")
        raise HTTPException(status_code=500, detail="Trajectory computation failed.")


@router.post("/compare")
async def compare_worlds(req: CompareRequest) -> Dict[str, Any]:
    try:
        return await run_in_threadpool(compare, req.shock_variable, req.shock_magnitude)
    except Exception:  # noqa: BLE001
        logger.exception("compare failed")
        raise HTTPException(status_code=500, detail="Comparison failed.")


@router.get("/anomalies")
async def anomalies(inject: Optional[str] = Query(default=None, description="SIM replay, e.g. in.macro.external.usd_inr:3.0")) -> Dict[str, Any]:
    try:
        return await run_in_threadpool(scan, inject)
    except Exception:  # noqa: BLE001
        logger.exception("anomaly scan failed")
        raise HTTPException(status_code=500, detail="Anomaly scan failed.")


@router.post("/mpc/simulate")
async def mpc_simulate(req: MpcRequest | None = None) -> Dict[str, Any]:
    try:
        return await simulate_mpc(use_llm=req.use_llm if req else True)
    except Exception:  # noqa: BLE001
        logger.exception("mpc simulation failed")
        raise HTTPException(status_code=500, detail="MPC simulation failed.")
