"""Pydantic v2 data models for the Labour Sector."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DataFreshness(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class Citation(BaseModel):
    """Mandatory provenance chain for every labour market observation."""

    source_agent: str = Field(default="labour_sector")
    source_authority: str = Field(default="Ministry of Statistics and Programme Implementation (MoSPI) / NSO")
    document_title: str = Field(...)
    table_reference: str = Field(...)
    retrieval_url: str = Field(...)
    observation_period: str = Field(...)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: DataFreshness = Field(default=DataFreshness.LIVE)


# ---------------------------------------------------------------------------
# Tool 1 — Unemployment Snapshot
# ---------------------------------------------------------------------------

class UnemploymentRecord(BaseModel):
    """Periodic Labour Force Survey (PLFS) Unemployment Rate (UR %) observation."""

    period: str = Field(..., description="Reporting quarter or annual period (e.g. 'Q1-2024-25').")
    unemployment_rate_pct: float | None = Field(None, description="Unemployment Rate UR (%) for age 15+ in CWS/UPSS.")
    unemployment_rate_urban_pct: float | None = Field(None, description="Urban Unemployment Rate (%).")
    unemployment_rate_rural_pct: float | None = Field(None, description="Rural Unemployment Rate (%).")
    unemployment_rate_youth_pct: float | None = Field(None, description="Youth (15-29) Unemployment Rate (%).")
    citation: Citation


class UnemploymentResponse(BaseModel):
    status: DataFreshness
    records: list[UnemploymentRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable(self) -> "UnemploymentResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Tool 2 — Labour Force Participation Rate (LFPR)
# ---------------------------------------------------------------------------

class LabourForceParticipationRecord(BaseModel):
    """PLFS Labour Force Participation Rate (LFPR %) observation."""

    period: str = Field(...)
    lfpr_total_pct: float | None = Field(None, description="Overall Labour Force Participation Rate (%).")
    lfpr_male_pct: float | None = Field(None, description="Male LFPR (%).")
    lfpr_female_pct: float | None = Field(None, description="Female LFPR (%).")
    lfpr_urban_pct: float | None = Field(None, description="Urban LFPR (%).")
    lfpr_rural_pct: float | None = Field(None, description="Rural LFPR (%).")
    citation: Citation


class LabourForceParticipationResponse(BaseModel):
    status: DataFreshness
    records: list[LabourForceParticipationRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tool 3 — Worker Population Ratio (WPR)
# ---------------------------------------------------------------------------

class WorkerPopulationRatioRecord(BaseModel):
    """PLFS Worker Population Ratio (WPR %) observation."""

    period: str = Field(...)
    wpr_total_pct: float | None = Field(None, description="Overall Worker Population Ratio (%).")
    wpr_male_pct: float | None = Field(None, description="Male WPR (%).")
    wpr_female_pct: float | None = Field(None, description="Female WPR (%).")
    wpr_urban_pct: float | None = Field(None, description="Urban WPR (%).")
    wpr_rural_pct: float | None = Field(None, description="Rural WPR (%).")
    citation: Citation


class WorkerPopulationRatioResponse(BaseModel):
    status: DataFreshness
    records: list[WorkerPopulationRatioRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tool 4 — Labour Employment Conditions
# ---------------------------------------------------------------------------

class LabourConditionsRecord(BaseModel):
    """Summary of employment conditions, formal payrolls (EPFO), and wage growth."""

    period: str = Field(...)
    epfo_net_additions_thousands: float | None = Field(None, description="Net EPFO formal payroll additions (Thousands).")
    self_employed_share_pct: float | None = Field(None, description="Share of self-employed workers (%).")
    regular_wage_share_pct: float | None = Field(None, description="Share of regular wage/salaried workers (%).")
    casual_labour_share_pct: float | None = Field(None, description="Share of casual labour workers (%).")
    citation: Citation


class LabourConditionsResponse(BaseModel):
    status: DataFreshness
    records: list[LabourConditionsRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Unavailable Response
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str = Field(...)
    reason: str = Field(...)
    last_successful_fetch: datetime | None = Field(None)
    error_detail: str | None = None
