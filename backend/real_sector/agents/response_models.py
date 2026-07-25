from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SectorResponse(BaseModel):
    agent: str
    assessment: str
    indicators: dict[str, dict[str, Any]] = Field(default_factory=dict)
    alerts: list[str] = Field(default_factory=list)
    source_metadata: list[dict[str, Any]] = Field(default_factory=list)
