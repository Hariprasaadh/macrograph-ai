"""Labour & Employment Sector FastMCP Tool Server."""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.database.macro_store import macro_store

mcp_server = FastMCP(
    "labour_sector_mcp",
    instructions="FastMCP server providing Indian labour and employment metrics (EPFO formal payroll additions, PLFS unemployment)."
)


class LabourQueryInput(BaseModel):
    indicator: Optional[str] = Field(default="epfo_additions", description="Indicator key: epfo_additions, unemployment")


@mcp_server.tool(name="get_epfo_payroll_snapshot", description="Fetches monthly net EPFO payroll additions.")
def get_epfo_payroll_snapshot(params: LabourQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.labour.epfo_additions")
    if obs:
        return {"agent": "labour_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "labour_sector", "status": "error", "message": "EPFO observation unavailable."}
