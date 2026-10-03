"""Pydantic v2 data models for the External Sector."""
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
    """Mandatory provenance chain for every external sector data point."""

    source_agent: str = Field(default="external_sector")
    source_authority: str = Field(default="Reserve Bank of India (RBI)")
    document_title: str = Field(...)
    table_reference: str = Field(...)
    retrieval_url: str = Field(...)
    observation_period: str = Field(...)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: DataFreshness = Field(default=DataFreshness.LIVE)


# ---------------------------------------------------------------------------
# Pillar 1 — Forex Reserves
# ---------------------------------------------------------------------------

class ForexReservesRecord(BaseModel):
    """Weekly snapshot of India's Foreign Exchange Reserves."""

    period: str = Field(..., description="Week ended date (e.g. '18-Sep-2026').")
    total_reserves_usd_mn: float | None = Field(None, description="Total Forex Reserves (USD Million).")
    total_reserves_inr_cr: float | None = Field(None, description="Total Forex Reserves (₹ Crore).")
    foreign_currency_assets_usd_mn: float | None = Field(None, description="Foreign Currency Assets (USD Million).")
    gold_reserves_usd_mn: float | None = Field(None, description="Gold Reserves (USD Million).")
    sdrs_usd_mn: float | None = Field(None, description="SDRs (USD Million).")
    reserve_tranche_position_usd_mn: float | None = Field(None, description="Reserve Tranche Position in IMF (USD Million).")
    citation: Citation


class ForexReservesResponse(BaseModel):
    status: DataFreshness
    records: list[ForexReservesRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable(self) -> "ForexReservesResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Pillar 2 — Trade Balance
# ---------------------------------------------------------------------------

class TradeBalanceRecord(BaseModel):
    """Monthly merchandise trade exports, imports, and trade balance."""

    period: str = Field(...)
    exports_usd_bn: float | None = Field(None, description="Merchandise Exports (USD Billion).")
    imports_usd_bn: float | None = Field(None, description="Merchandise Imports (USD Billion).")
    trade_balance_usd_bn: float | None = Field(None, description="Trade Deficit (-) / Surplus (+) (USD Billion).")
    citation: Citation


class TradeBalanceResponse(BaseModel):
    status: DataFreshness
    records: list[TradeBalanceRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 3 — Balance of Payments (BoP)
# ---------------------------------------------------------------------------

class BoPRecord(BaseModel):
    """Quarterly Balance of Payments snapshot."""

    period: str = Field(...)
    current_account_balance_usd_bn: float | None = Field(None, description="Current Account Balance (USD Billion).")
    current_account_to_gdp_pct: float | None = Field(None, description="Current Account Balance as % of GDP.")
    capital_account_balance_usd_bn: float | None = Field(None, description="Capital Account Balance (USD Billion).")
    net_bop_usd_bn: float | None = Field(None, description="Overall BoP Balance (USD Billion).")
    citation: Citation


class BoPResponse(BaseModel):
    status: DataFreshness
    records: list[BoPRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 4 — Exchange Rates (USD/INR, REER, NEER)
# ---------------------------------------------------------------------------

class ExchangeRateRecord(BaseModel):
    """Exchange Rate snapshot."""

    period: str = Field(...)
    usd_inr_rate: float | None = Field(None, description="USD/INR reference exchange rate.")
    reer_40_basket: float | None = Field(None, description="Real Effective Exchange Rate (40-currency basket).")
    neer_40_basket: float | None = Field(None, description="Nominal Effective Exchange Rate (40-currency basket).")
    citation: Citation


class ExchangeRatesResponse(BaseModel):
    status: DataFreshness
    records: list[ExchangeRateRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 5 — External Flows (FDI, FPI)
# ---------------------------------------------------------------------------

class ExternalFlowsRecord(BaseModel):
    """FDI and FPI net investment flows."""

    period: str = Field(...)
    net_fdi_usd_mn: float | None = Field(None, description="Net Foreign Direct Investment (USD Million).")
    net_fpi_usd_mn: float | None = Field(None, description="Net Foreign Portfolio Investment (USD Million).")
    citation: Citation


class ExternalFlowsResponse(BaseModel):
    status: DataFreshness
    records: list[ExternalFlowsRecord]
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
