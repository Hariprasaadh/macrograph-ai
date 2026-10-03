"""Pydantic v2 data models for the Capital Markets Sector."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DataFreshness(str, Enum):
    LIVE = "live"
    UPSTREAM_SNAPSHOT = "upstream_snapshot"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class Citation(BaseModel):
    """Mandatory provenance chain for every capital market observation."""

    source_agent: str = Field(default="capital_market_sector")
    source_authority: str = Field(default="National Stock Exchange of India (NSE) / RBI")
    document_title: str = Field(...)
    table_reference: str = Field(...)
    retrieval_url: str = Field(...)
    observation_period: str = Field(...)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: DataFreshness = Field(default=DataFreshness.LIVE)


# ---------------------------------------------------------------------------
# Tool 1 — Nifty Snapshot
# ---------------------------------------------------------------------------

class NiftySnapshotRecord(BaseModel):
    """Snapshot of NIFTY 50 and key equity indices."""

    period: str = Field(..., description="Trade date or period label (YYYY-MM-DD).")
    index_name: str = Field(default="NIFTY 50")
    open_price: float | None = Field(None)
    high_price: float | None = Field(None)
    low_price: float | None = Field(None)
    close_price: float | None = Field(None)
    change_points: float | None = Field(None)
    change_pct: float | None = Field(None)
    volume_shares: float | None = Field(None)
    turnover_cr: float | None = Field(None)
    citation: Citation


class NiftySnapshotResponse(BaseModel):
    status: DataFreshness
    records: list[NiftySnapshotRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable(self) -> "NiftySnapshotResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Tool 2 — Market History
# ---------------------------------------------------------------------------

class MarketHistoryRecord(BaseModel):
    """Historical daily/weekly equity index performance record."""

    period: str = Field(...)
    index_name: str = Field(default="NIFTY 50")
    close_price: float | None = Field(None)
    yoy_return_pct: float | None = Field(None)
    pe_ratio: float | None = Field(None)
    pb_ratio: float | None = Field(None)
    dividend_yield_pct: float | None = Field(None)
    citation: Citation


class MarketHistoryResponse(BaseModel):
    status: DataFreshness
    records: list[MarketHistoryRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tool 3 — India VIX
# ---------------------------------------------------------------------------

class IndiaVixRecord(BaseModel):
    """India Volatility Index (India VIX) observation."""

    period: str = Field(...)
    vix_close: float | None = Field(None, description="India VIX index value.")
    vix_change_pct: float | None = Field(None, description="Daily % change in India VIX.")
    volatility_regime: str | None = Field(None, description="'Low', 'Normal', or 'High' volatility.")
    citation: Citation


class IndiaVixResponse(BaseModel):
    status: DataFreshness
    records: list[IndiaVixRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tool 4 — Market Breadth
# ---------------------------------------------------------------------------

class MarketBreadthRecord(BaseModel):
    """NSE equity market breadth metrics."""

    period: str = Field(...)
    total_stocks: int | None = Field(None, description="Total stocks included in the NSE breadth snapshot.")
    advances_count: int | None = Field(None, description="Number of advancing stocks.")
    declines_count: int | None = Field(None, description="Number of declining stocks.")
    unchanged_count: int | None = Field(None, description="Number of unchanged stocks.")
    advance_decline_ratio: float | None = Field(None, description="Ratio of advances to declines.")
    total_volume: int | None = Field(None, description="Total traded volume in the breadth snapshot.")
    citation: Citation


class MarketBreadthResponse(BaseModel):
    status: DataFreshness
    records: list[MarketBreadthRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tool 5 — G-Sec Yield Snapshot
# ---------------------------------------------------------------------------

class GSecYieldRecord(BaseModel):
    """Monthly RBI SGL transaction yields at labeled G-Sec maturities."""

    period: str = Field(...)
    ten_year_gsec_yield_pct: float | None = Field(None, description="RBI month-end SGL transaction yield at 10-year term to maturity (% p.a.).")
    five_year_gsec_yield_pct: float | None = Field(None, description="RBI month-end SGL transaction yield at 5-year term to maturity (% p.a.).")
    two_year_gsec_yield_pct: float | None = Field(None, description="RBI month-end SGL transaction yield at 2-year term to maturity (% p.a.).")
    yield_curve_spread_2s10s_bps: float | None = Field(None, description="10-year minus 2-year monthly SGL yield, in basis points.")
    citation: Citation


class GSecYieldResponse(BaseModel):
    status: DataFreshness
    records: list[GSecYieldRecord]
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
