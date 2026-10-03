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
# Pillar 1 — Forex Reserves & Liquidity
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
    import_cover_months: float | None = Field(None, description="Estimated months of merchandise & services imports covered.")
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
# Pillar 2 — Trade Balance & Composition
# ---------------------------------------------------------------------------

class TradeBalanceRecord(BaseModel):
    """Monthly merchandise trade exports, imports, and trade balance."""

    period: str = Field(...)
    exports_usd_bn: float | None = Field(None, description="Merchandise Exports (USD Billion).")
    imports_usd_bn: float | None = Field(None, description="Merchandise Imports (USD Billion).")
    trade_balance_usd_bn: float | None = Field(None, description="Trade Deficit (-) / Surplus (+) (USD Billion).")
    oil_imports_usd_bn: float | None = Field(None, description="Oil imports in USD Billion.")
    non_oil_imports_usd_bn: float | None = Field(None, description="Non-oil imports in USD Billion.")
    oil_exports_usd_bn: float | None = Field(None, description="Oil exports in USD Billion.")
    non_oil_exports_usd_bn: float | None = Field(None, description="Non-oil exports in USD Billion.")
    services_surplus_usd_bn: float | None = Field(None, description="Net services trade surplus (USD Billion).")
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
    services_balance_usd_bn: float | None = Field(None, description="Net invisibles / services balance (USD Billion).")
    remittances_usd_bn: float | None = Field(None, description="Private transfers / remittances (USD Billion).")
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


class LiveMarketRatesRecord(BaseModel):
    """Real-time spot FX rates and Brent crude oil benchmark."""

    timestamp: str = Field(..., description="Timestamp of live market snapshot.")
    usd_inr: float | None = Field(None, description="Spot USD/INR rate.")
    eur_inr: float | None = Field(None, description="Spot EUR/INR rate.")
    gbp_inr: float | None = Field(None, description="Spot GBP/INR rate.")
    jpy_inr: float | None = Field(None, description="Spot JPY/INR rate.")
    brent_crude_usd: float | None = Field(None, description="Brent crude price (USD/barrel).")
    citation: Citation


class LiveMarketRatesResponse(BaseModel):
    status: DataFreshness
    record: LiveMarketRatesRecord | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 5 — Remittances and Cross-Border Income Flows
# ---------------------------------------------------------------------------

class RemittancesRecord(BaseModel):
    """Cross-border remittances, secondary income, and services invisibles."""

    period: str = Field(..., description="Reporting fiscal year or quarter.")
    private_transfers_net_usd_mn: float | None = Field(None, description="Net private transfers (USD Million).")
    receipts_usd_mn: float | None = Field(None, description="Gross inward remittances receipts (USD Million).")
    payments_usd_mn: float | None = Field(None, description="Outward remittances payments (USD Million).")
    services_receipts_usd_mn: float | None = Field(None, description="Non-factor services receipts (USD Million).")
    services_net_usd_mn: float | None = Field(None, description="Net non-factor services surplus (USD Million).")
    citation: Citation


class RemittancesResponse(BaseModel):
    status: DataFreshness
    records: list[RemittancesRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Pillar 6 — External Capital Flows & External Debt
# ---------------------------------------------------------------------------

class ExternalFlowsRecord(BaseModel):
    """FDI and FPI net investment flows."""

    period: str = Field(...)
    net_fdi_usd_mn: float | None = Field(None, description="Net Foreign Direct Investment (USD Million).")
    net_fpi_usd_mn: float | None = Field(None, description="Net Foreign Portfolio Investment (USD Million).")
    ecb_usd_mn: float | None = Field(None, description="External Commercial Borrowings net inflow (USD Million).")
    nri_deposits_usd_mn: float | None = Field(None, description="NRI deposits net flow (USD Million).")
    citation: Citation


class ExternalFlowsResponse(BaseModel):
    status: DataFreshness
    records: list[ExternalFlowsRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


class ExternalDebtRecord(BaseModel):
    """Sovereign and non-sovereign external debt stock and vulnerability."""

    period: str = Field(..., description="Quarter ended or financial year end date.")
    total_debt_usd_bn: float | None = Field(None, description="Total External Debt (USD Billion).")
    total_debt_inr_cr: float | None = Field(None, description="Total External Debt (₹ Crore).")
    general_government_usd_bn: float | None = Field(None, description="General Government external debt (USD Billion).")
    short_term_debt_usd_bn: float | None = Field(None, description="Short-term external debt (USD Billion).")
    short_term_to_reserves_pct: float | None = Field(None, description="Short-term debt to forex reserves ratio (%).")
    debt_to_gdp_pct: float | None = Field(None, description="External debt as percentage of GDP.")
    citation: Citation


class ExternalDebtResponse(BaseModel):
    status: DataFreshness
    records: list[ExternalDebtRecord]
    total_records: int = Field(default=0)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Real-time Web Intelligence (Tavily)
# ---------------------------------------------------------------------------

class RealtimeIntelligenceRecord(BaseModel):
    """Live macroeconomic web intelligence retrieved via Tavily."""

    query: str = Field(...)
    summary: str = Field(..., description="Synthesized real-time context.")
    news_items: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    fetched_at: str = Field(...)
    citation: Citation | None = Field(None, description="Attribution metadata for Tavily search intelligence.")


class RealtimeIntelligenceResponse(BaseModel):
    status: DataFreshness
    record: RealtimeIntelligenceRecord | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Multilateral Intelligence (IMF SDMX 3.0 WEO Projections)
# ---------------------------------------------------------------------------

class IMFExternalOutlookRecord(BaseModel):
    """Multilateral WEO medium-term projections and comparative benchmarks."""

    period: str = Field(..., description="Calendar or fiscal year.")
    current_account_to_gdp_pct: float | None = Field(None, description="IMF WEO CAD as % of GDP.")
    current_account_balance_usd_bn: float | None = Field(None, description="IMF WEO Current Account Balance (USD Bn).")
    export_volume_growth_pct: float | None = Field(None, description="Export volume growth (% YoY).")
    citation: Citation


class IMFExternalOutlookResponse(BaseModel):
    status: DataFreshness
    records: list[IMFExternalOutlookRecord]
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
