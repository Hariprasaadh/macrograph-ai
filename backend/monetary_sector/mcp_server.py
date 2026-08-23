"""Monetary & Banking Sector FastMCP Tool Server."""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.database.macro_store import macro_store

mcp_server = FastMCP(
    "monetary_sector_mcp",
    instructions="FastMCP server providing RBI monetary policy and banking system metrics (Repo rate, Bank credit growth)."
)


class MonetaryQueryInput(BaseModel):
    indicator: Optional[str] = Field(default="repo_rate", description="Indicator key: repo_rate, bank_credit_growth")


@mcp_server.tool(name="get_repo_rate_snapshot", description="Fetches RBI Policy Repo Rate.")
def get_repo_rate_snapshot(params: MonetaryQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.monetary.repo_rate")
    if obs:
        return {"agent": "monetary_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "monetary_sector", "status": "error", "message": "Repo rate observation unavailable."}


@mcp_server.tool(name="get_credit_growth_snapshot", description="Fetches Scheduled Commercial Banks Credit Growth.")
def get_credit_growth_snapshot(params: MonetaryQueryInput) -> Dict[str, Any]:
    obs = macro_store.get_latest_canonical_observation("in.macro.monetary.bank_credit_growth")
    if obs:
        return {"agent": "monetary_sector", "status": "success", "observation": obs.model_dump()}
    return {"agent": "monetary_sector", "status": "error", "message": "Bank credit growth observation unavailable."}
