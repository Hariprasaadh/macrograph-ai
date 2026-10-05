"""Typed contracts shared by all Prices entry points."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class PriceObservation(BaseModel):
    source_agent: Literal['prices_sector'] = 'prices_sector'
    source_authority: str
    dataset_reference: str
    indicator_id: str
    indicator: str
    series_code: str
    request_id: str
    observation_period: str
    country: str = 'India'
    base_year: str | None = None
    value: float = Field(allow_inf_nan=False)
    unit: str
    url: str
    mcp_server: str
    mcp_tool: str
    retrieval_status: Literal['live'] = 'live'
    retrieved_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class PricesResult(BaseModel):
    status: Literal['available', 'partial', 'unavailable', 'error']
    source: str | None = None
    observations: list[PriceObservation] = Field(default_factory=list)
    error: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class PriceRequest(BaseModel):
    indicator: Literal['cpi', 'wpi'] = 'cpi'
    category: str = 'headline'
    sector: Literal['combined', 'rural', 'urban'] = 'combined'

    @property
    def key(self) -> str:
        return f'{self.indicator}:{self.category}:{self.sector}'


class PricesIntent(BaseModel):
    source: Literal['mospi', 'imf'] = 'mospi'
    operation: Literal['latest', 'trend', 'comparison'] = 'latest'
    countries: list[str] = Field(default_factory=list)
    lookback_months: int = Field(default=12, ge=1, le=120)
    requests: list[PriceRequest] = Field(default_factory=lambda: [PriceRequest()])
    geography: str = 'India'
    base_year: str | None = None
    start_period: str | None = None
    end_period: str | None = None
    errors: list[str] = Field(default_factory=list)
