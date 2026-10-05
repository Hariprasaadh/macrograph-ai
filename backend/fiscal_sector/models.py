"""Pydantic v2 domain models for the Fiscal & Public Finance Sector.

Rules:
  - Strict type annotations on every field.
  - Mandatory Citation object attached to every empirical record.
  - Zero hardcoded numbers in default fields.
  - Use model_validate() and model_dump().
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataFreshness(str, Enum):
    """Provenance indicator showing data pipeline freshness."""
    LIVE = "live"
    CACHED = "cached"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class Citation(BaseModel):
    """Mandatory citation metadata satisfying the No Source, No Answer policy."""
    source_agent: str = Field(default="fiscal_sector", description="Agent that owns this data")
    source_authority: str = Field(..., description="Official government or international authority (CGA, MoSPI, IMF, CBIC)")
    document_title: str = Field(..., description="Official report, bulletin, or dataset name")
    table_reference: str = Field(..., description="Exact table, series key, or API endpoint identifier")
    indicator_id: str = Field(..., description="Canonical macro indicator ID (e.g. in.macro.fiscal.fiscal_deficit)")
    observation_period: str = Field(..., description="Period of observation (e.g., '2024-25', '2024-11')")
    value: Optional[float | str] = Field(default=None, description="The specific empirical value cited")
    unit: str = Field(..., description="Measurement unit (e.g., '₹ Crore', '% of GDP', '% YoY')")
    url: str = Field(..., description="Direct link or official portal reference")
    freshness: DataFreshness = Field(default=DataFreshness.LIVE, description="Freshness status of the cited observation")
    retrieved_at: str = Field(..., description="ISO 8601 timestamp of data ingestion")


# ── Pillar 1: Union Accounts & Fiscal Deficit (CGA & Union Budget) ───────────

class FiscalDeficitRecord(BaseModel):
    """Union Government accounts at a glance from Controller General of Accounts (CGA)."""
    period: str = Field(..., description="Fiscal year or monthly reporting period, e.g. '2024-25 (BE)' or '2024-11'")
    revenue_receipts_cr: float = Field(..., description="Revenue Receipts (₹ Crore)")
    tax_revenue_net_cr: float = Field(..., description="Tax Revenue (Net to Centre) (₹ Crore)")
    non_tax_revenue_cr: float = Field(..., description="Non-Tax Revenue (₹ Crore)")
    non_debt_capital_receipts_cr: float = Field(default=0.0, description="Non-Debt Capital Receipts (₹ Crore)")
    total_receipts_cr: float = Field(..., description="Total Non-Debt Receipts (₹ Crore)")
    total_expenditure_cr: float = Field(..., description="Total Expenditure (₹ Crore)")
    revenue_expenditure_cr: float = Field(..., description="Revenue Expenditure (₹ Crore)")
    capital_expenditure_cr: float = Field(..., description="Capital Expenditure (Capex) (₹ Crore)")
    fiscal_deficit_cr: float = Field(..., description="Fiscal Deficit (₹ Crore)")
    fiscal_deficit_gdp_pct: Optional[float] = Field(default=None, description="Fiscal Deficit as % of GDP")
    revenue_deficit_cr: Optional[float] = Field(default=None, description="Revenue Deficit (₹ Crore)")
    primary_deficit_cr: Optional[float] = Field(default=None, description="Primary Deficit (₹ Crore)")
    citation: Citation


class FiscalDeficitResponse(BaseModel):
    """Response payload for Union fiscal deficit and budgetary accounts."""
    status: DataFreshness
    records: List[FiscalDeficitRecord]
    total_records: int


# ── Pillar 2: Sovereign Debt & International Balance (IMF WEO) ─────────────

class SovereignDebtRecord(BaseModel):
    """General Government Debt & Net Lending/Borrowing from IMF WEO SDMX / MCP."""
    period: str = Field(..., description="Calendar/Fiscal year (e.g. '2024')")
    general_govt_gross_debt_gdp_pct: float = Field(..., description="General Government Gross Debt as % of GDP (IMF WEO IND.GGXWDG_NGDP.A)")
    net_lending_borrowing_gdp_pct: float = Field(..., description="General Government Net Lending/Borrowing as % of GDP (IMF WEO IND.GGXCNL_NGDP.A)")
    revenue_gdp_pct: Optional[float] = Field(default=None, description="General Government Revenue as % of GDP (IND.GGR_NGDP.A)")
    expenditure_gdp_pct: Optional[float] = Field(default=None, description="General Government Total Expenditure as % of GDP (IND.GGX_NGDP.A)")
    citation: Citation


class SovereignDebtResponse(BaseModel):
    """Response payload for General Government Debt & Fiscal Balance."""
    status: DataFreshness
    records: List[SovereignDebtRecord]
    total_records: int


# ── Pillar 3: Goods & Services Tax (GST Collections) ─────────────────────────

class GSTCollectionRecord(BaseModel):
    """Monthly Gross GST Revenue Collection."""
    period: str = Field(..., description="Monthly observation period (YYYY-MM)")
    gross_gst_cr: float = Field(..., description="Total Gross GST Collection (₹ Crore)")
    cgst_cr: Optional[float] = Field(default=None, description="Central GST (₹ Crore)")
    sgst_cr: Optional[float] = Field(default=None, description="State GST (₹ Crore)")
    igst_cr: Optional[float] = Field(default=None, description="Integrated GST (₹ Crore)")
    cess_cr: Optional[float] = Field(default=None, description="Compensation Cess (₹ Crore)")
    yoy_growth_pct: Optional[float] = Field(default=None, description="Year-on-Year Growth (%)")
    citation: Citation


class GSTCollectionResponse(BaseModel):
    """Response payload for GST collections."""
    status: DataFreshness
    records: List[GSTCollectionRecord]
    total_records: int


# ── Pillar 4: MoSPI Product Taxes & Government Consumption (NAS) ─────────────

class MoSPITaxAggregateRecord(BaseModel):
    """National Accounts product taxes, subsidies, and GFCE from MoSPI eSankhyiki."""
    year: str = Field(..., description="Financial year, e.g. '2024-25'")
    indicator: str = Field(..., description="Official indicator name (Net Taxes on Products, GFCE, etc.)")
    current_price_cr: float = Field(..., description="Value at Current Prices (₹ Crore)")
    constant_price_cr: Optional[float] = Field(default=None, description="Value at Constant (2011-12) Prices (₹ Crore)")
    frequency: str = Field(default="Annual", description="Frequency of observation")
    revision: Optional[str] = Field(default=None, description="Revision stage (First Advance Estimates, etc.)")
    citation: Citation


class MoSPITaxAggregateResponse(BaseModel):
    """Response payload for MoSPI National Accounts fiscal aggregates."""
    status: DataFreshness
    records: List[MoSPITaxAggregateRecord]
    total_records: int


# ── Pillar 5: Tax Policy & Calculators (eco-policy-mcp integration) ─────────

class GSTSplitBreakdown(BaseModel):
    """GST calculation split details."""
    tax_type: str = Field(..., description="'CGST+SGST' for intra-state or 'IGST' for inter-state")
    base_amount: float = Field(..., description="Base invoice amount before tax")
    rate_percent: float = Field(..., description="Applicable GST slab rate (%)")
    cgst: float = Field(default=0.0, description="Central GST component")
    sgst: float = Field(default=0.0, description="State GST component")
    igst: float = Field(default=0.0, description="Integrated GST component")
    total_tax: float = Field(..., description="Total GST amount")
    total_invoice_value: float = Field(..., description="Base amount + Total tax")


class TaxProvenance(BaseModel):
    """Provenance block for calculations and validation."""
    source: str
    as_of: str
    reference: str
    note: Optional[str] = None


class GSTSplitResponse(BaseModel):
    """GST Split tool response."""
    data: GSTSplitBreakdown
    provenance: TaxProvenance


class GSTINValidationResponse(BaseModel):
    """GSTIN validation and state code decode."""
    gstin: str
    is_valid: bool
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    provenance: TaxProvenance


class TaxRegimeComparison(BaseModel):
    """Income Tax regime comparison between New and Old regimes."""
    gross_salary: Optional[float] = Field(default=None, description="Gross taxable salary input")
    new_regime: Dict[str, Any]
    old_regime: Dict[str, Any]
    recommended_regime: str
    savings_if_switched: float
    note: Optional[str] = None


class IncomeTaxComparisonResponse(BaseModel):
    """Income Tax comparison response."""
    data: TaxRegimeComparison
    provenance: TaxProvenance


# ── Pillar 6: Real-time News & Notifications (Tavily AI) ────────────────────

class FiscalNewsItem(BaseModel):
    """Item for fiscal, budget, and tax news releases."""
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    source: str


class FiscalNewsResponse(BaseModel):
    """Response containing recent fiscal developments and PIB releases."""
    query: str
    total_results: int
    items: List[FiscalNewsItem]
    fetched_at: str


# ── Structured Fallback / Error Response ────────────────────────────────────

class UnavailableResponse(BaseModel):
    """Explicit structured unavailable response avoiding hallucination."""
    status: DataFreshness = DataFreshness.UNAVAILABLE
    tool: str
    reason: str
    error_detail: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
