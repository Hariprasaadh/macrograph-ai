"""Pydantic v2 data models for the Capital Markets Sector.

Covers all 10 domain responsibilities:
1. Equity Market Performance
2. Market Volatility & Sentiment
3. Mutual Fund Flows
4. Foreign Portfolio Investment (FPI) in Equities
5. Corporate Earnings & Valuation
6. Market Liquidity & Breadth
7. Sectoral Market Performance
8. Primary Capital Markets (IPOs)
9. Market Structure & Investor Participation
10. Market-Economy Linkages
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
    """Mandatory provenance chain for every capital market observation."""

    source_agent: str = Field(default="capital_market_sector")
    source_authority: str = Field(default="National Stock Exchange of India (NSE) / RBI / SEBI / AMFI")
    document_title: str = Field(...)
    table_reference: str = Field(...)
    retrieval_url: str = Field(...)
    observation_period: str = Field(...)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: DataFreshness = Field(default=DataFreshness.LIVE)


# ---------------------------------------------------------------------------
# 1. Equity Market Performance (NIFTY Snapshot & History)
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


class MarketHistoryRecord(BaseModel):
    """Historical daily/weekly/monthly equity index performance record."""

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
# 2. Market Volatility & Sentiment (India VIX)
# ---------------------------------------------------------------------------

class IndiaVixRecord(BaseModel):
    """India Volatility Index (India VIX) observation and regime."""

    period: str = Field(...)
    vix_close: float | None = Field(None, description="India VIX index value.")
    vix_change_pct: float | None = Field(None, description="Daily % change in India VIX.")
    volatility_regime: str | None = Field(None, description="'Low' (<13), 'Normal' (13-18), 'Elevated' (18-24), 'High' (>24).")
    citation: Citation


class IndiaVixResponse(BaseModel):
    status: DataFreshness
    records: list[IndiaVixRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 3. Market Liquidity & Breadth
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
# 4. Government Securities (G-Sec) Yield Curve
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
# 5. Mutual Fund Flows (AMFI Data)
# ---------------------------------------------------------------------------

class MutualFundFlowsRecord(BaseModel):
    """Official AMFI mutual fund flows, SIP contributions, and AUM."""

    period: str = Field(..., description="Observation month (YYYY-MM).")
    equity_inflows_cr: float | None = Field(None, description="Net equity mutual fund inflows in ₹ Crore.")
    sip_inflow_cr: float | None = Field(None, description="Monthly SIP contribution total in ₹ Crore.")
    total_mf_aum_lakh_cr: float | None = Field(None, description="Mutual fund industry total AUM in ₹ Lakh Crore.")
    net_inflow_cr: float | None = Field(None, description="Total industry net inflow across categories in ₹ Crore.")
    citation: Citation


class MutualFundFlowsResponse(BaseModel):
    status: DataFreshness
    records: list[MutualFundFlowsRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 6. Foreign Portfolio Investment (FPI / FII) in Equities
# ---------------------------------------------------------------------------

class FpiFlowsRecord(BaseModel):
    """Official NSDL / SEBI FPI equity investment flows."""

    period: str = Field(..., description="Observation period (YYYY-MM or YYYY-MM-DD).")
    fpi_gross_purchases_cr: float | None = Field(None, description="Gross FPI equity purchases in ₹ Crore.")
    fpi_gross_sales_cr: float | None = Field(None, description="Gross FPI equity sales in ₹ Crore.")
    fpi_net_investment_cr: float | None = Field(None, description="Net FPI equity investment in ₹ Crore.")
    fpi_net_investment_usd_mn: float | None = Field(None, description="Net FPI equity investment in USD Million.")
    dii_net_investment_cr: float | None = Field(None, description="Net Domestic Institutional Investor (DII) investment in ₹ Crore.")
    citation: Citation


class FpiFlowsResponse(BaseModel):
    status: DataFreshness
    records: list[FpiFlowsRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 7. Corporate Earnings & Valuation
# ---------------------------------------------------------------------------

class CorporateEarningsRecord(BaseModel):
    """Corporate earnings growth, EPS, and valuation metrics."""

    period: str = Field(..., description="Reporting quarter or period (e.g., FY2024-Q2 or YYYY-MM).")
    index_name: str = Field(default="NIFTY 50")
    ttm_eps: float | None = Field(None, description="Trailing Twelve Months (TTM) EPS in ₹.")
    pe_ratio: float | None = Field(None, description="Price to Earnings ratio.")
    pb_ratio: float | None = Field(None, description="Price to Book ratio.")
    dividend_yield_pct: float | None = Field(None, description="Dividend Yield in %.")
    pat_growth_yoy_pct: float | None = Field(None, description="NIFTY 50 Aggregate PAT YoY growth %.")
    citation: Citation


class CorporateEarningsResponse(BaseModel):
    status: DataFreshness
    records: list[CorporateEarningsRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 8. Sectoral Market Performance
# ---------------------------------------------------------------------------

class SectoralPerformanceRecord(BaseModel):
    """Comparative returns across major NSE sectoral indices."""

    period: str = Field(..., description="Observation trade date (YYYY-MM-DD).")
    nifty_50_change_pct: float | None = Field(None, description="NIFTY 50 daily change %.")
    nifty_bank_change_pct: float | None = Field(None, description="NIFTY Bank daily change %.")
    nifty_it_change_pct: float | None = Field(None, description="NIFTY IT daily change %.")
    nifty_auto_change_pct: float | None = Field(None, description="NIFTY Auto daily change %.")
    nifty_pharma_change_pct: float | None = Field(None, description="NIFTY Pharma daily change %.")
    nifty_fmcg_change_pct: float | None = Field(None, description="NIFTY FMCG daily change %.")
    leading_sector: str | None = Field(None, description="Top performing sector in session.")
    lagging_sector: str | None = Field(None, description="Bottom performing sector in session.")
    citation: Citation


class SectoralPerformanceResponse(BaseModel):
    status: DataFreshness
    records: list[SectoralPerformanceRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 9. Primary Capital Markets (IPOs & Equity Issuance)
# ---------------------------------------------------------------------------

class PrimaryMarketRecord(BaseModel):
    """SEBI / NSE primary equity market mobilization via IPOs, QIPs, and rights."""

    period: str = Field(..., description="Observation period (YYYY-MM or quarter).")
    ipo_count: int | None = Field(None, description="Number of completed IPO issues.")
    ipo_proceeds_cr: float | None = Field(None, description="Total capital mobilized through IPOs in ₹ Crore.")
    qip_proceeds_cr: float | None = Field(None, description="Capital mobilized through QIPs in ₹ Crore.")
    rights_proceeds_cr: float | None = Field(None, description="Capital mobilized through Rights issues in ₹ Crore.")
    total_equity_raised_cr: float | None = Field(None, description="Total primary equity capital raised in ₹ Crore.")
    citation: Citation


class PrimaryMarketResponse(BaseModel):
    status: DataFreshness
    records: list[PrimaryMarketRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 10. Market Structure & Investor Participation
# ---------------------------------------------------------------------------

class InvestorParticipationRecord(BaseModel):
    """Demat account count, retail participation, and institutional ownership."""

    period: str = Field(..., description="Observation month (YYYY-MM).")
    total_demat_accounts_cr: float | None = Field(None, description="Total active Demat accounts in Crores (NSDL + CDSL).")
    monthly_demat_additions_lakh: float | None = Field(None, description="Net new Demat accounts added in the month (Lakhs).")
    retail_turnover_share_pct: float | None = Field(None, description="Retail share in equity cash market turnover (%).")
    institutional_holding_pct: float | None = Field(None, description="Combined institutional ownership (FPI + DII) in %.")
    citation: Citation


class InvestorParticipationResponse(BaseModel):
    status: DataFreshness
    records: list[InvestorParticipationRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 11. Market-Economy Linkages (respecting A2A boundaries)
# ---------------------------------------------------------------------------

class MarketEconomyLinkageRecord(BaseModel):
    """Linkage metrics between capital market valuations and macro aggregates."""

    period: str = Field(..., description="Observation period (YYYY-MM).")
    nifty_earnings_yield_pct: float | None = Field(None, description="NIFTY earnings yield (1 / PE * 100).")
    ten_year_gsec_yield_pct: float | None = Field(None, description="10-Year RBI SGL transaction yield (% p.a.).")
    equity_risk_premium_bps: float | None = Field(None, description="Equity Risk Premium: Earnings Yield minus 10Y G-Sec in basis points.")
    market_cap_to_gdp_pct: float | None = Field(None, description="Market Cap to GDP ratio (Buffett Indicator for India) in %.")
    linkage_regime: str | None = Field(None, description="Interpretation: 'Equity Yield Advantage', 'Fair Value', 'Bond Yield Advantage'.")
    citation: Citation


class MarketEconomyLinkageResponse(BaseModel):
    status: DataFreshness
    records: list[MarketEconomyLinkageRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Generic Unavailable Response
# ---------------------------------------------------------------------------

class UnavailableResponse(BaseModel):
    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str = Field(...)
    reason: str = Field(...)
    last_successful_fetch: datetime | None = Field(None)
    error_detail: str | None = None
