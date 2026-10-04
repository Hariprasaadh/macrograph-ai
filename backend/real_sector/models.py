"""Pydantic v2 data models for the Real Sector & Industrial Output.

Every macroeconomic observation MUST include a Citation object.
Rules:
- No default values for citation fields.
- Percentages are plain floats (e.g. 4.5 means 4.5%).
- Monetary values are in â‚¹ Crore where applicable.
"""
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
    """Mandatory provenance chain for every macroeconomic data point."""

    source_agent: str = Field(
        default="real_sector",
        description="The sector agent that owns and produced this observation.",
    )
    source_authority: str = Field(
        ...,
        description="Official publisher (e.g. 'MoSPI', 'DPIIT / Office of Economic Adviser', 'RBI').",
    )
    document_title: str = Field(
        ...,
        description="Full title of the publication or press release.",
    )
    table_reference: str = Field(
        ...,
        description="Exact table identifier or series code.",
    )
    retrieval_url: str = Field(
        ...,
        description="Canonical URL where the data point can be verified.",
    )
    observation_period: str = Field(
        ...,
        description="Period to which the observation applies (YYYY-MM or YYYY-QN).",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this record was fetched.",
    )
    freshness: DataFreshness = Field(
        default=DataFreshness.LIVE,
        description="Data freshness status.",
    )
    dataset: str | None = Field(default=None, description="Dataset/section identifier.")
    authority: str | None = Field(default=None, description="Alias for source_authority.")
    frequency: str | None = Field(default=None, description="Observation frequency.")
    unit: str | None = Field(default=None, description="Unit of measurement.")
    source_note: str | None = Field(default=None, description="Additional context or notes.")
    as_of: str | None = Field(default=None, description="As of date.")


# ---------------------------------------------------------------------------
# Step 1 â€” MoSPI IIP Sectoral Breakdown
# ---------------------------------------------------------------------------

class IIPSectoralRecord(BaseModel):
    """Index of Industrial Production (IIP) by Sectoral Classification (2011-12=100)."""

    period: str = Field(..., description="Observation month (YYYY-MM).")
    general_iip: float | None = Field(None, description="General IIP index level.")
    general_iip_yoy_pct: float | None = Field(None, description="General IIP YoY growth (%).")
    mining_iip: float | None = Field(None, description="Mining sector IIP index level.")
    mining_yoy_pct: float | None = Field(None, description="Mining sector YoY growth (%).")
    manufacturing_iip: float | None = Field(None, description="Manufacturing sector IIP index level.")
    manufacturing_yoy_pct: float | None = Field(None, description="Manufacturing sector YoY growth (%).")
    electricity_iip: float | None = Field(None, description="Electricity sector IIP index level.")
    electricity_yoy_pct: float | None = Field(None, description="Electricity sector YoY growth (%).")
    citation: Citation


class IIPSectoralResponse(BaseModel):
    status: DataFreshness
    records: list[IIPSectoralRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable(self) -> "IIPSectoralResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Step 2 â€” MoSPI IIP Use-Based Classification
# ---------------------------------------------------------------------------

class IIPUseBasedRecord(BaseModel):
    """Index of Industrial Production by Use-Based Classification (2011-12=100)."""

    period: str = Field(..., description="Observation month (YYYY-MM).")
    primary_goods_yoy_pct: float | None = Field(None, description="Primary goods YoY growth (%).")
    capital_goods_yoy_pct: float | None = Field(None, description="Capital goods YoY growth (%).")
    intermediate_goods_yoy_pct: float | None = Field(None, description="Intermediate goods YoY growth (%).")
    infrastructure_goods_yoy_pct: float | None = Field(None, description="Infrastructure/Construction goods YoY growth (%).")
    consumer_durables_yoy_pct: float | None = Field(None, description="Consumer durables YoY growth (%).")
    consumer_non_durables_yoy_pct: float | None = Field(None, description="Consumer non-durables YoY growth (%).")
    citation: Citation


class IIPUseBasedResponse(BaseModel):
    status: DataFreshness
    records: list[IIPUseBasedRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Step 3 â€” DPIIT Index of Eight Core Industries (ICI)
# ---------------------------------------------------------------------------

class CoreIndustriesRecord(BaseModel):
    """DPIIT Index of Eight Core Industries (ICI) (2011-12=100)."""

    period: str = Field(..., description="Observation month (YYYY-MM).")
    overall_ici_yoy_pct: float | None = Field(None, description="Combined 8 Core Industries YoY growth (%).")
    coal_yoy_pct: float | None = Field(None, description="Coal production YoY growth (%).")
    crude_oil_yoy_pct: float | None = Field(None, description="Crude oil production YoY growth (%).")
    natural_gas_yoy_pct: float | None = Field(None, description="Natural gas production YoY growth (%).")
    refinery_products_yoy_pct: float | None = Field(None, description="Petroleum refinery products YoY growth (%).")
    fertilizers_yoy_pct: float | None = Field(None, description="Fertilizers production YoY growth (%).")
    steel_yoy_pct: float | None = Field(None, description="Steel production YoY growth (%).")
    cement_yoy_pct: float | None = Field(None, description="Cement production YoY growth (%).")
    electricity_yoy_pct: float | None = Field(None, description="Electricity generation YoY growth (%).")
    citation: Citation


class CoreIndustriesResponse(BaseModel):
    status: DataFreshness
    records: list[CoreIndustriesRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

class ManufacturingGVARecord(BaseModel):
    """Gross Value Added (GVA) for Manufacturing sector at constant and current prices."""

    period: str = Field(..., description="Quarterly / annual period label (e.g. '2024-Q1', '2024-Q2').")
    manufacturing_gva_real_yoy_pct: float | None = Field(None, description="Real Manufacturing GVA growth YoY (%).")
    manufacturing_gva_cr: float | None = Field(None, description="Nominal Manufacturing GVA (â‚¹ Crore).")
    manufacturing_share_in_gva_pct: float | None = Field(None, description="Manufacturing share in total GVA (%).")
    citation: Citation


class ManufacturingGVAResponse(BaseModel):
    status: DataFreshness
    records: list[ManufacturingGVARecord]
    total_records: int = Field(default=0)
    error_message: str | None = None




# ---------------------------------------------------------------------------
# Step 5 â€” Joined Real Sector Observation (DuckDB JOIN)
# ---------------------------------------------------------------------------

class RealSectorJoinedRecord(BaseModel):

    period: str = Field(..., description="Observation period (YYYY-MM or YYYY-QN).")
    manufacturing_iip_yoy_pct: float | None = None
    capital_goods_iip_yoy_pct: float | None = None
    intermediate_goods_yoy_pct: float | None = None
    consumer_durables_yoy_pct: float | None = None
    core_steel_yoy_pct: float | None = None
    core_cement_yoy_pct: float | None = None
    core_electricity_yoy_pct: float | None = None
    core_coal_yoy_pct: float | None = None
    overall_ici_yoy_pct: float | None = None
    manufacturing_gva_yoy_pct: float | None = None
    trend_summary: str | None = None
    citation: Citation


class RealSectorJoinedResponse(BaseModel):
    status: DataFreshness
    records: list[RealSectorJoinedRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Step 7 â€” Market Context: Infrastructure & Industrial Listed Companies
# ---------------------------------------------------------------------------

class CompanyMarketRecord(BaseModel):
    """Market performance snapshot for a key industrial/infra corporate bellwether."""

    symbol: str
    company_name: str
    sector_category: str  # Steel, Cement, Capital Goods, Infrastructure
    current_price: float | None = None
    change_pct_1m: float | None = None
    change_pct_1y: float | None = None
    pe_ratio: float | None = None


class MarketContextRecord(BaseModel):
    """Market context snapshot for industrial and infrastructure equity bellwethers."""

    period: str = Field(..., description="Market date (YYYY-MM-DD).")
    nifty_infra_change_pct: float | None = Field(None, description="NIFTY Infrastructure index change (%).")
    nifty_metal_change_pct: float | None = Field(None, description="NIFTY Metal index change (%).")
    bellwether_companies: list[CompanyMarketRecord] = Field(default_factory=list)
    citation: Citation


class MarketContextResponse(BaseModel):
    status: DataFreshness
    records: list[MarketContextRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Sentinel Unavailable Response
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    """Returned when neither live source nor local cache can supply data."""

    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str = Field(..., description="Name of the tool that could not fetch data.")
    reason: str = Field(..., description="Human-readable explanation of why data is unavailable.")
    last_successful_fetch: datetime | None = None
    error_detail: str | None = None
