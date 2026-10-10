"""Typed contracts shared by all Prices entry points."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field


def observation_identity(record: dict[str, Any]) -> str:
    """Content-addressed observation ID local to the prices sector.

    Revisions and scope changes alter the ID; retrieval timestamps and
    volatile freshness metadata do not.
    """
    payload = {k: v for k, v in record.items() if k not in ('observation_id', 'retrieved_at', 'request_id')}
    payload['metadata'] = {k: v for k, v in payload.get('metadata', {}).items()
                           if k not in ('freshness', 'coverage_complete', 'latest_available_period',
                                        'comparison_period', 'country', 'geography', 'sector')}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str, allow_nan=False)
    return 'obs_' + hashlib.sha256(encoded.encode()).hexdigest()


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
    geography: str = 'India'
    sector: str = 'combined'
    base_year: str | None = None
    value: float = Field(allow_inf_nan=False)
    unit: str
    url: str
    mcp_server: str
    mcp_tool: str
    retrieval_status: Literal['live'] = 'live'
    retrieved_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('value', mode='before')
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError('Boolean is not an observation value')
        return value

    @model_validator(mode='before')
    @classmethod
    def preserve_scope(cls, values):
        if isinstance(values, dict):
            values = dict(values)
            metadata = values.get('metadata') or {}
            values.setdefault('geography', metadata.get('geography', values.get('country', 'India')))
            values.setdefault('sector', metadata.get('sector', 'combined'))
        return values

    @computed_field
    @property
    def observation_id(self) -> str:
        return observation_identity(self.model_dump(mode='json', exclude={'observation_id'}))


class PricesResult(BaseModel):
    status: Literal['available', 'partial', 'unavailable', 'error']
    source: str | None = None
    observations: list[PriceObservation] = Field(default_factory=list)
    error: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    web_research: dict[str, Any] = Field(default_factory=dict)


class PriceRequest(BaseModel):
    indicator: Literal['cpi', 'wpi'] = 'cpi'
    category: str = 'headline'
    sector: Literal['combined', 'rural', 'urban'] = 'combined'
    measure: Literal['yoy', 'mom', 'index'] = 'yoy'

    @property
    def key(self) -> str:
        key = f'{self.indicator}:{self.category}:{self.sector}'
        return key if self.measure == 'yoy' else f'{key}:{self.measure}'


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
