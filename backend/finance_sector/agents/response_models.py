from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class FinanceSectorResponse(BaseModel):
    """Standardized response contract for Finance Sector tools."""
    agent: str = Field(default="finance")
    assessment: str = Field(..., description="Explainable macroeconomic assessment string")
    indicators: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Structured indicator dictionary")
    alerts: List[str] = Field(default_factory=list, description="Risk alerts and anomaly warnings")
    source_metadata: List[Dict[str, Any]] = Field(default_factory=list, description="Data provenance & freshness dates")
