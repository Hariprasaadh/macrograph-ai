"""Pydantic v2 data models for the Services Sector.

Every model that carries a macroeconomic observation MUST include a Citation
object. No numeric value is permitted without provenance.

Rules enforced here:
- No default values for citation fields — they must always be supplied.
- ISP index values are unit-free index numbers (Base 2024-25 = 100).
- All percentage values are plain floats (e.g. 6.8 means 6.8 %).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ServiceSubSector(str, Enum):
    GENERAL = "GENERAL"
    WHOLESALE_TRADE = "WHOLESALE_TRADE"
    RETAIL_TRADE = "RETAIL_TRADE"
    REPAIR_SERVICES = "REPAIR_SERVICES"
    ACCOMMODATION_FOOD = "ACCOMMODATION_FOOD"
    RAILWAY_TRANSPORT = "RAILWAY_TRANSPORT"
    ROAD_TRANSPORT = "ROAD_TRANSPORT"
    WATER_TRANSPORT = "WATER_TRANSPORT"
    AIR_TRANSPORT = "AIR_TRANSPORT"
    WAREHOUSING_SUPPORT = "WAREHOUSING_SUPPORT"
    POSTAL_COURIER = "POSTAL_COURIER"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"
    INFORMATION_BROADCASTING = "INFORMATION_BROADCASTING"
    BANKING = "BANKING"
    INSURANCE = "INSURANCE"
    REAL_ESTATE = "REAL_ESTATE"
    IT_COMPUTER = "IT_COMPUTER"
    PROFESSIONAL_TECHNICAL = "PROFESSIONAL_TECHNICAL"
    ADMIN_SUPPORT = "ADMIN_SUPPORT"
    ARTS_ENTERTAINMENT = "ARTS_ENTERTAINMENT"


class DataFreshness(str, Enum):
    LIVE = "live"       # fetched from MoSPI MCP in this request
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
        default="services_sector",
        description="The sector agent that owns and produced this observation.",
    )
    source_authority: str = Field(
        ...,
        description="Official publisher of the underlying data (e.g. 'National Statistical Office (NSO), MoSPI').",
    )
    document_title: str = Field(
        ...,
        description="Full title of the official publication or release.",
    )
    table_reference: str = Field(
        ...,
        description="Exact dataset/table identifier (e.g. 'mospi.isp_monthly' or 'mospi.nas_statement_8_12').",
    )
    retrieval_url: str = Field(
        ...,
        description="Canonical URL where the data point can be verified.",
    )
    observation_period: str = Field(
        ...,
        description="Period to which the observation applies (YYYY-MM or YYYY-YY).",
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
# Pillar 1 — Index of Service Production (ISP, MoSPI)
# ---------------------------------------------------------------------------

class ISPRecord(BaseModel):
    """One monthly observation of the Index of Service Production."""

    period: str = Field(..., description="Month label (YYYY-MM).")
    sub_sector: ServiceSubSector = Field(..., description="Service sub-sector (GENERAL = all-services index).")
    isp_index: float | None = Field(None, description="ISP index level (Base 2024-25 = 100).")
    isp_yoy_pct: float | None = Field(None, description="Year-on-year ISP growth (%).")
    isp_mom_pct: float | None = Field(None, description="Month-on-month ISP growth (%).")
    citation: Citation


class ISPGrowthResponse(BaseModel):
    """MCP tool response — get_isp_growth."""

    status: DataFreshness
    records: list[ISPRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None

    @model_validator(mode="after")
    def check_unavailable_has_no_records(self) -> "ISPGrowthResponse":
        if self.status == DataFreshness.UNAVAILABLE and self.records:
            raise ValueError("UNAVAILABLE response must not carry data records.")
        return self


# ---------------------------------------------------------------------------
# Pillar 2 — Services GVA (NAS Statements 8.9–8.14, MoSPI)
# ---------------------------------------------------------------------------

class ServicesGVARecord(BaseModel):
    """Services GVA / Output for one NAS statement in a reporting year."""

    period: str = Field(..., description="Fiscal year label (e.g. '2024-25').")
    nas_statement: str = Field(..., description="NAS statement code (e.g. '8.12' for financial services).")
    segment: str = Field(..., description="Services segment name (e.g. 'Financial services').")
    gva_current_cr: float | None = Field(None, description="GVA at current prices (Rs Crore).")
    gva_constant_cr: float | None = Field(None, description="GVA at constant prices (Rs Crore).")
    gva_yoy_pct: float | None = Field(None, description="Year-on-year real GVA growth (%).")
    citation: Citation


class ServicesGVAResponse(BaseModel):
    """MCP tool response — get_services_gva."""

    status: DataFreshness
    records: list[ServicesGVARecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 3 — Services PMI Sentiment (S&P Global / HSBC)
# ---------------------------------------------------------------------------

class ServicesPMIRecord(BaseModel):
    """Monthly Services PMI business-activity snapshot."""

    period: str = Field(..., description="Month label (YYYY-MM).")
    headline_pmi: float | None = Field(None, description="Headline Services PMI (50 = no change).")
    new_orders_idx: float | None = Field(None, description="New business / orders sub-index.")
    input_costs_idx: float | None = Field(None, description="Input cost pressure sub-index.")
    employment_idx: float | None = Field(None, description="Employment sub-index.")
    citation: Citation


class ServicesPMIResponse(BaseModel):
    """MCP tool response — get_services_pmi."""

    status: DataFreshness
    records: list[ServicesPMIRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 4 — Transport, Freight & Telecom Volumes
# ---------------------------------------------------------------------------

class TransportFreightRecord(BaseModel):
    """High-frequency services volume observation."""

    period: str = Field(..., description="Month label (YYYY-MM).")
    indicator: str = Field(..., description="Volume indicator key (e.g. 'railway_freight_mt').")
    value: float | None = Field(None, description="Observed volume in indicator-native units.")
    unit: str = Field(..., description="Native unit (e.g. 'Million Tonnes', 'Million subscribers').")
    yoy_pct: float | None = Field(None, description="Year-on-year change (%).")
    citation: Citation


class TransportFreightResponse(BaseModel):
    """MCP tool response — get_transport_and_freight_indicators."""

    status: DataFreshness
    records: list[TransportFreightRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Unavailable response — sentinel for "No Source, No Answer"
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    """Returned when neither live MoSPI MCP nor local DuckDB can supply data.

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


# ---------------------------------------------------------------------------
# Pillar 5 — Services Market Context (yfinance: NIFTY IT / services stocks)
# ---------------------------------------------------------------------------

class ServicesEquityMetric(BaseModel):
    """Live/recent equity quote for a services-linked stock or index."""

    symbol: str = Field(..., description="Ticker symbol (e.g. ^CNXIT, TCS.NS, INFY.NS).")
    name: str = Field(..., description="Entity name.")
    current_price: float | None = Field(None, description="Last traded / current price in INR.")
    change_pct: float | None = Field(None, description="Day price change percentage (%).")
    pe_ratio: float | None = Field(None, description="Trailing Price-to-Earnings ratio.")
    pb_ratio: float | None = Field(None, description="Price-to-Book ratio.")
    market_cap_cr: float | None = Field(None, description="Market Capitalization in Rs Crore.")
    high_52w: float | None = Field(None, description="52-week high in INR.")
    low_52w: float | None = Field(None, description="52-week low in INR.")
    citation: Citation


class ServicesMarketResponse(BaseModel):
    """MCP tool response — get_services_market_indicators."""

    status: DataFreshness
    benchmark_index: ServicesEquityMetric | None = None
    top_stocks: list[ServicesEquityMetric] = Field(default_factory=list)
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 6 — Real-Time Services News & Intelligence (Tavily)
# ---------------------------------------------------------------------------

class TavilyNewsItem(BaseModel):
    """Real-time services news article or policy announcement."""

    title: str = Field(..., description="Headline of the article or notification.")
    url: str = Field(..., description="Canonical source URL.")
    content: str = Field(..., description="Extracted content snippet or summary.")
    published_date: str | None = Field(None, description="Published date if available.")
    source: str = Field(default="Tavily AI Search", description="Information broker.")


class ServicesNewsResponse(BaseModel):
    """MCP tool response — get_realtime_services_news."""

    status: DataFreshness
    query: str = Field(..., description="Search query executed.")
    news_items: list[TavilyNewsItem] = Field(default_factory=list)
    total_results: int = Field(default=0)
    error_message: str | None = None
