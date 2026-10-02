"""Pydantic v2 data models for the Finance & Banking Sector.

Every model that carries a macroeconomic observation MUST include a Citation
object.  No numeric value is permitted without provenance.

Rules enforced here:
- No default values for citation fields — they must always be supplied.
- All monetary values are in ₹ Crore unless the unit field says otherwise.
- All percentage values are plain floats (e.g. 4.5 means 4.5 %).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BankGroup(str, Enum):
    ALL_SCB = "ALL_SCB"
    PUBLIC_SECTOR = "PUBLIC_SECTOR"
    PRIVATE_SECTOR = "PRIVATE_SECTOR"
    FOREIGN_BANKS = "FOREIGN_BANKS"
    SMALL_FINANCE = "SMALL_FINANCE"


class DataFreshness(str, Enum):
    LIVE = "live"       # fetched from DBIE in this request
    CACHED = "cached"   # returned from local DuckDB
    UNAVAILABLE = "unavailable"  # neither source returned data


# ---------------------------------------------------------------------------
# Citation — mandatory on every observation
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    """Mandatory provenance chain for every macroeconomic data point.

    No Source, No Answer: a value without a Citation is a protocol violation.
    """

    source_agent: str = Field(
        default="finance_sector",
        description="The sector agent that owns and produced this observation.",
    )
    source_authority: str = Field(
        ...,
        description="Official publisher of the underlying data (e.g. 'Reserve Bank of India').",
    )
    document_title: str = Field(
        ...,
        description="Full title of the RBI publication or table.",
    )
    table_reference: str = Field(
        ...,
        description="Exact DBIE table identifier (e.g. financial_sector.r330_...).",
    )
    retrieval_url: str = Field(
        ...,
        description="Canonical URL where the data point can be verified.",
    )
    observation_period: str = Field(
        ...,
        description="Period to which the observation applies (YYYY-MM or YYYY-QN or YYYY-YY).",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this record was last fetched from the live source.",
    )
    freshness: DataFreshness = Field(
        default=DataFreshness.LIVE,
        description="Whether this value came from a live fetch or local cache.",
    )


# ---------------------------------------------------------------------------
# Pillar 1 — Bank Credit Growth & Sectoral Deployment
# ---------------------------------------------------------------------------

class SectoralCreditBreakdown(BaseModel):
    """Credit deployment split by major economic sector."""

    agriculture_cr: float | None = Field(None, description="Agriculture credit (₹ Crore)")
    industry_cr: float | None = Field(None, description="Total Industry credit (₹ Crore)")
    industry_msme_cr: float | None = Field(None, description="MSME credit (₹ Crore)")
    industry_large_cr: float | None = Field(None, description="Large enterprises credit (₹ Crore)")
    services_cr: float | None = Field(None, description="Services sector credit (₹ Crore)")
    personal_loans_cr: float | None = Field(None, description="Personal / Retail credit (₹ Crore)")
    personal_housing_cr: float | None = Field(None, description="Housing loans (₹ Crore)")
    personal_vehicle_cr: float | None = Field(None, description="Vehicle loans (₹ Crore)")


class BankCreditGrowthRecord(BaseModel):
    """One time-series observation of SCB non-food gross bank credit."""

    period: str = Field(..., description="Fortnightly / monthly period label.")
    gross_credit_cr: float = Field(..., description="Total gross credit outstanding (₹ Crore).")
    non_food_credit_cr: float = Field(..., description="Non-food credit outstanding (₹ Crore).")
    non_food_credit_yoy_pct: float | None = Field(
        None, description="Year-on-year growth of non-food credit (%)."
    )
    sectoral: SectoralCreditBreakdown = Field(
        default_factory=SectoralCreditBreakdown,
        description="Sectoral deployment breakdown.",
    )
    citation: Citation


class BankCreditGrowthResponse(BaseModel):
    """MCP tool response — get_bank_credit_growth."""

    status: DataFreshness
    records: list[BankCreditGrowthRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable_has_no_records(self) -> "BankCreditGrowthResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Pillar 2 — Asset Quality & Capital Adequacy
# ---------------------------------------------------------------------------

class NPARecord(BaseModel):
    """Gross & Net NPA for a single bank group in a reporting period."""

    period: str = Field(..., description="Reporting period (e.g. '2024-25' or 'H1-2025').")
    bank_group: BankGroup
    gross_npa_pct: float | None = Field(None, description="Gross NPA as % of gross advances.")
    net_npa_pct: float | None = Field(None, description="Net NPA as % of net advances.")
    gross_npa_cr: float | None = Field(None, description="Gross NPA amount (₹ Crore).")
    net_npa_cr: float | None = Field(None, description="Net NPA amount (₹ Crore).")
    provision_coverage_ratio_pct: float | None = Field(
        None, description="Provision Coverage Ratio (%)."
    )
    crar_pct: float | None = Field(None, description="Capital to Risk-Weighted Assets Ratio (%).")
    cet1_pct: float | None = Field(None, description="CET-1 capital ratio (%).")
    citation: Citation


class AssetQualityResponse(BaseModel):
    """MCP tool response — get_asset_quality."""

    status: DataFreshness
    records: list[NPARecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 3 — Lending Rates & Policy Transmission
# ---------------------------------------------------------------------------

class LendingRateRecord(BaseModel):
    """Monthly snapshot of commercial bank lending and deposit rates."""

    period: str = Field(..., description="Month/policy-cycle label (YYYY-MM).")
    walr_fresh_pct: float | None = Field(
        None, description="Weighted Average Lending Rate — fresh rupee loans (%)."
    )
    walr_outstanding_pct: float | None = Field(
        None, description="Weighted Average Lending Rate — outstanding rupee loans (%)."
    )
    mclr_1yr_median_pct: float | None = Field(
        None, description="1-Year Median Marginal Cost of Funds-based Lending Rate (%)."
    )
    wadtdr_fresh_pct: float | None = Field(
        None, description="Weighted Average Domestic Term Deposit Rate — fresh (%)."
    )
    wadtdr_outstanding_pct: float | None = Field(
        None, description="Weighted Average Domestic Term Deposit Rate — outstanding (%)."
    )
    repo_rate_pct: float | None = Field(
        None,
        description=(
            "Policy Repo Rate (%) — consumed from monetary_sector via A2A. "
            "NOT fetched independently by finance_sector."
        ),
    )
    lending_spread_over_repo_pct: float | None = Field(
        None,
        description="Computed spread: WALR (fresh) minus Policy Repo Rate (%).",
    )
    citation: Citation

    @model_validator(mode="after")
    def compute_spread(self) -> "LendingRateRecord":
        """Auto-compute lending spread if both components are available."""
        if (
            self.walr_fresh_pct is not None
            and self.repo_rate_pct is not None
            and self.lending_spread_over_repo_pct is None
        ):
            self.lending_spread_over_repo_pct = round(
                self.walr_fresh_pct - self.repo_rate_pct, 4
            )
        return self


class LendingRatesResponse(BaseModel):
    """MCP tool response — get_lending_and_deposit_rates."""

    status: DataFreshness
    records: list[LendingRateRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 4 — Deposit Mobilization & CD Ratio
# ---------------------------------------------------------------------------

class DepositRecord(BaseModel):
    """Fortnightly / monthly commercial bank deposit and CD ratio snapshot."""

    period: str = Field(..., description="Fortnightly / monthly period label.")
    aggregate_deposits_cr: float | None = Field(
        None, description="Total commercial bank aggregate deposits (₹ Crore)."
    )
    deposits_yoy_pct: float | None = Field(
        None, description="Year-on-year deposit growth (%)."
    )
    demand_deposits_cr: float | None = Field(None, description="Demand deposits (₹ Crore).")
    time_deposits_cr: float | None = Field(None, description="Time deposits (₹ Crore).")
    casa_ratio_pct: float | None = Field(
        None,
        description=(
            "CASA (Current + Savings Account) deposits as % of total deposits (%)."
        ),
    )
    bank_credit_cr: float | None = Field(
        None, description="Bank credit outstanding (₹ Crore), for CD ratio denominator."
    )
    cd_ratio_pct: float | None = Field(
        None, description="Credit-to-Deposit ratio (%)."
    )
    citation: Citation


class DepositsAndCDResponse(BaseModel):
    """MCP tool response — get_deposits_and_cd_ratio."""

    status: DataFreshness
    records: list[DepositRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Unavailable response — sentinel for "No Source, No Answer"
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    """Returned when neither live DBIE nor local DuckDB can supply data.

    The agent MUST return this instead of any hardcoded or estimated value.
    """

    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str = Field(..., description="Name of the MCP tool that could not fetch data.")
    reason: str = Field(..., description="Human-readable explanation of why data is unavailable.")
    last_successful_fetch: datetime | None = Field(
        None,
        description="UTC timestamp of the last successful data fetch, if any.",
    )
    error_detail: str | None = None
