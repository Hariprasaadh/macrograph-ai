"""Pydantic v2 data models for the Monetary Sector.

Every model carrying a macroeconomic observation MUST include a Citation object.
No numeric value is permitted without provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DataFreshness(str, Enum):
    LIVE = "live"       # live upstream source explicitly reports real-time data
    UPSTREAM_SNAPSHOT = "upstream_snapshot"  # fetched from an upstream deployment snapshot
    CACHED = "cached"   # returned from local DuckDB
    UNAVAILABLE = "unavailable"  # neither source returned data


class Citation(BaseModel):
    """Mandatory provenance chain for every monetary data point."""

    source_agent: str = Field(
        default="monetary_sector",
        description="The sector agent that owns and produced this observation.",
    )
    source_authority: str = Field(
        default="Reserve Bank of India (RBI)",
        description="Official publisher of the underlying data.",
    )
    document_title: str = Field(
        ...,
        description="Full title of the RBI publication or table.",
    )
    table_reference: str = Field(
        ...,
        description="Exact DBIE table or document identifier.",
    )
    retrieval_url: str = Field(
        ...,
        description="Canonical URL where the data point can be verified.",
    )
    observation_period: str = Field(
        ...,
        description="Period to which the observation applies (YYYY-MM or YYYY-MM-DD).",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this record was retrieved from its source.",
    )
    freshness: DataFreshness = Field(
        default=DataFreshness.UPSTREAM_SNAPSHOT,
        description="Whether data is an upstream snapshot, explicitly live, or locally cached.",
    )
    source_base_url: str | None = None
    source_note: str | None = None
    as_of: str | None = None
    frequency: str | None = None
    unit: str | None = None
    source_values: dict[str, Any] = Field(default_factory=dict)


class TavilyNewsItem(BaseModel):
    """Real-time monetary policy news and research snippet from Tavily AI."""
    title: str = Field(..., description="Headline of the article or publication.")
    url: str = Field(..., description="Canonical URL of the source.")
    content: str = Field(..., description="Relevant text excerpt or summary.")
    published_date: str | None = Field(None, description="Publication timestamp or date string.")
    source: str = Field(default="Tavily AI Search", description="Data source identifier.")
    score: float | None = Field(None, description="Relevance score from search engine.")


class MonetaryNewsResponse(BaseModel):
    """Response container for real-time monetary search intelligence."""
    status: DataFreshness
    query: str
    news_items: list[TavilyNewsItem]
    total_results: int = 0
    error_message: str | None = None


class MonetaryMarketMetric(BaseModel):
    """Bond yield, money-market rate, or policy transmission indicator."""
    symbol: str = Field(..., description="Market symbol or instrument name.")
    name: str = Field(..., description="Descriptive name (e.g. 10Y Indian Benchmark G-Sec).")
    current_yield_pct: float | None = Field(None, description="Current yield or rate (%).")
    change_bps: float | None = Field(None, description="Day-over-day change in basis points.")
    spread_over_repo_bps: float | None = Field(None, description="Spread over RBI Policy Repo rate (bps).")
    observation_date: str | None = Field(None, description="Observation date (YYYY-MM-DD).")
    citation: Citation


class MonetaryMarketResponse(BaseModel):
    """Snapshot of sovereign bond yields, interbank liquidity, and transmission spreads."""
    status: DataFreshness
    gsec_10y_yield_pct: float | None = None
    overnight_wacr_pct: float | None = None
    policy_spread_bps: float | None = None
    metrics: list[MonetaryMarketMetric] = Field(default_factory=list)
    total_records: int = 0


# ---------------------------------------------------------------------------
# Pillar 1 — Policy Rates
# ---------------------------------------------------------------------------

class PolicyRatesRecord(BaseModel):
    """Snapshot of RBI Policy Rates and Reserve Requirements."""

    period: str = Field(..., description="Effective date or period label (YYYY-MM-DD or YYYY-MM).")
    repo_rate_pct: float | None = Field(None, description="Policy Repo Rate (%).")
    reverse_repo_rate_pct: float | None = Field(None, description="Reverse Repo Rate (%).")
    sdf_rate_pct: float | None = Field(None, description="Standing Deposit Facility Rate (%).")
    msf_rate_pct: float | None = Field(None, description="Marginal Standing Facility Rate (%).")
    bank_rate_pct: float | None = Field(None, description="Bank Rate (%).")
    crr_pct: float | None = Field(None, description="Cash Reserve Ratio (%).")
    slr_pct: float | None = Field(None, description="Statutory Liquidity Ratio (%).")
    corridor_width_bps: float | None = Field(None, description="Width of LAF corridor (MSF minus SDF in bps).")
    stance: str | None = Field(None, description="Monetary Policy Committee stance label.")
    rates_effective_from: str | None = Field(None, description="Date from which these rates became effective.")
    citation: Citation


class PolicyRatesResponse(BaseModel):
    """MCP tool response — get_policy_rates."""

    status: DataFreshness
    records: list[PolicyRatesRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable(self) -> "PolicyRatesResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Pillar 2 — Money Supply
# ---------------------------------------------------------------------------

class MoneySupplyRecord(BaseModel):
    """Snapshot of Indian Money Supply aggregates (M1, M2, M3)."""

    period: str = Field(..., description="Reporting period (YYYY-MM or YYYY-MM-DD).")
    currency_with_public_cr: float | None = Field(None, description="Currency with the public (₹ Crore).")
    demand_deposits_cr: float | None = Field(None, description="Demand deposits with banks (₹ Crore).")
    other_deposits_rbi_cr: float | None = Field(None, description="Other deposits with RBI (₹ Crore).")
    m1_cr: float | None = Field(None, description="Narrow Money M1 (₹ Crore).")
    post_office_savings_cr: float | None = Field(None, description="Post office savings bank deposits (₹ Crore).")
    m2_cr: float | None = Field(None, description="Money supply M2 (₹ Crore).")
    time_deposits_cr: float | None = Field(None, description="Time deposits with banks (₹ Crore).")
    m3_cr: float | None = Field(None, description="Broad Money M3 (₹ Crore).")
    m3_yoy_pct: float | None = Field(None, description="Broad Money M3 YoY growth (%).")
    citation: Citation


class MoneySupplyResponse(BaseModel):
    """MCP tool response — get_money_supply."""

    status: DataFreshness
    records: list[MoneySupplyRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 3 — System Liquidity
# ---------------------------------------------------------------------------

class SystemLiquidityRecord(BaseModel):
    """RBI Net Liquidity Absorption / Injection indicator."""

    period: str = Field(..., description="Reporting period.")
    net_laf_absorption_cr: float | None = Field(None, description="Net LAF Absorption (+) / Injection (-) (₹ Crore).")
    laf_repo_cr: float | None = Field(None, description="Repo operations amount (₹ Crore).")
    laf_reverse_repo_cr: float | None = Field(None, description="Reverse Repo / SDF operations amount (₹ Crore).")
    msf_operations_cr: float | None = Field(None, description="MSF operations amount (₹ Crore).")
    liquidity_condition: str | None = Field(None, description="Condition label ('Surplus', 'Deficit', or 'Neutral').")
    citation: Citation


class SystemLiquidityResponse(BaseModel):
    """MCP tool response — get_system_liquidity."""

    status: DataFreshness
    records: list[SystemLiquidityRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 4 — Monetary Stance Snapshot
# ---------------------------------------------------------------------------

class MonetaryStanceRecord(BaseModel):
    """Comprehensive snapshot of Monetary Policy Stance."""

    period: str = Field(..., description="Policy stance period.")
    repo_rate_pct: float | None = Field(None, description="Current Repo Rate (%).")
    stance_label: str | None = Field(
        default=None,
        description="Only populated when an official source provides the stance label.",
    )
    real_policy_rate_pct: float | None = Field(None, description="Real policy rate (Repo minus Headline CPI % via A2A).")
    m3_growth_pct: float | None = Field(None, description="M3 YoY growth rate (%).")
    system_liquidity_status: str | None = Field(None, description="System liquidity status (Surplus / Deficit).")
    citation: Citation


class MonetaryStanceResponse(BaseModel):
    """MCP tool response — get_monetary_stance_snapshot."""

    status: DataFreshness
    records: list[MonetaryStanceRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Unavailable Response
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    """Sentinel for unavailable data."""

    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str = Field(..., description="Name of the MCP tool that could not fetch data.")
    reason: str = Field(..., description="Human-readable explanation of why data is unavailable.")
    last_successful_fetch: datetime | None = Field(None)
    error_detail: str | None = None


# ---------------------------------------------------------------------------
# Cache Maintenance
# ---------------------------------------------------------------------------

class CacheClearResponse(BaseModel):
    """Result of clearing the sector DuckDB cache tables."""

    status: str = Field(default="cache_cleared", description="Cache-clear outcome.")
    cleared_tables: dict[str, int] = Field(
        default_factory=dict, description="Deleted row count per data table."
    )
    total_rows_deleted: int = Field(default=0, description="Total cached rows deleted.")
    message: str = Field(
        default="",
        description="Human-readable note on what happens on subsequent queries.",
    )
