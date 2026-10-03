"""Payload parsers and conversion helpers for the Real Sector.

Transforms raw payloads from MoSPI, DPIIT, RBI DBIE, and Market sources
into strictly typed Pydantic models with mandatory Citation metadata.
Also includes the Step 6 Analytics Trend Evaluator.
"""
from __future__ import annotations

import re
from typing import Any

from real_sector.models import (
    Citation,
    CompanyMarketRecord,
    CoreIndustriesRecord,
    DataFreshness,
    IIPSectoralRecord,
    IIPUseBasedRecord,
    ManufacturingGVARecord,
    MarketContextRecord,
    OBICUSRecord,
    RealSectorJoinedRecord,
)

_MOSPI_AUTHORITY = "Ministry of Statistics and Programme Implementation (MoSPI)"
_DPIIT_AUTHORITY = "DPIIT / Office of Economic Adviser"
_RBI_AUTHORITY = "Reserve Bank of India (RBI)"
_MARKET_AUTHORITY = "National Stock Exchange of India (NSE) / Yahoo Finance"


def safe_float_val(value: Any) -> float | None:
    """Safely convert any numeric or string representation to a float, or None."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            clean = value.replace(",", "").strip()
            if not clean or clean.lower() in ("null", "none", "-", "", "na", "n/a"):
                return None
            return float(clean)
        return float(value)
    except (TypeError, ValueError):
        return None


def make_citation(
    authority: str,
    document_title: str,
    table_reference: str,
    retrieval_url: str,
    observation_period: str,
    freshness: DataFreshness = DataFreshness.LIVE,
) -> Citation:
    """Generate a standard Citation for Real Sector observations."""
    return Citation(
        source_agent="real_sector",
        source_authority=authority,
        document_title=document_title,
        table_reference=table_reference,
        retrieval_url=retrieval_url,
        observation_period=observation_period,
        freshness=freshness,
    )


def extract_rows(payload: Any) -> list[Any]:
    """Extract rows from either a list or dict wrapper."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "items", "records", "result"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


# ---------------------------------------------------------------------------
# Step 1: MoSPI IIP Sectoral Parser
# ---------------------------------------------------------------------------

def parse_iip_sectoral(payload: Any) -> list[IIPSectoralRecord]:
    """Parse MoSPI IIP Sectoral records."""
    rows = extract_rows(payload)
    if not rows:
        raise ValueError("Empty or invalid IIP Sectoral payload.")

    records: list[IIPSectoralRecord] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        period = str(r.get("period") or r.get("month") or r.get("date") or "2024-08")
        citation = make_citation(
            authority=_MOSPI_AUTHORITY,
            document_title="Quick Estimates of Index of Industrial Production (IIP)",
            table_reference="mospi_iip_sectoral_2011_12",
            retrieval_url="https://mospi.gov.in/iip",
            observation_period=period,
        )
        records.append(
            IIPSectoralRecord(
                period=period,
                general_iip=safe_float_val(r.get("general_iip") or r.get("general")),
                general_iip_yoy_pct=safe_float_val(r.get("general_iip_yoy_pct") or r.get("general_yoy")),
                mining_iip=safe_float_val(r.get("mining_iip") or r.get("mining")),
                mining_yoy_pct=safe_float_val(r.get("mining_yoy_pct") or r.get("mining_yoy")),
                manufacturing_iip=safe_float_val(r.get("manufacturing_iip") or r.get("manufacturing")),
                manufacturing_yoy_pct=safe_float_val(r.get("manufacturing_yoy_pct") or r.get("manufacturing_yoy")),
                electricity_iip=safe_float_val(r.get("electricity_iip") or r.get("electricity")),
                electricity_yoy_pct=safe_float_val(r.get("electricity_yoy_pct") or r.get("electricity_yoy")),
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 2: MoSPI IIP Use-Based Parser
# ---------------------------------------------------------------------------

def parse_iip_use_based(payload: Any) -> list[IIPUseBasedRecord]:
    """Parse MoSPI IIP Use-Based records."""
    rows = extract_rows(payload)
    if not rows:
        raise ValueError("Empty or invalid IIP Use-Based payload.")

    records: list[IIPUseBasedRecord] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        period = str(r.get("period") or r.get("month") or "2024-08")
        citation = make_citation(
            authority=_MOSPI_AUTHORITY,
            document_title="IIP Use-Based Classification (2011-12=100)",
            table_reference="mospi_iip_use_based_2011_12",
            retrieval_url="https://mospi.gov.in/iip",
            observation_period=period,
        )
        records.append(
            IIPUseBasedRecord(
                period=period,
                primary_goods_yoy_pct=safe_float_val(r.get("primary_goods_yoy_pct") or r.get("primary_yoy")),
                capital_goods_yoy_pct=safe_float_val(r.get("capital_goods_yoy_pct") or r.get("capital_yoy")),
                intermediate_goods_yoy_pct=safe_float_val(r.get("intermediate_goods_yoy_pct") or r.get("intermediate_yoy")),
                infrastructure_goods_yoy_pct=safe_float_val(r.get("infrastructure_goods_yoy_pct") or r.get("infra_yoy")),
                consumer_durables_yoy_pct=safe_float_val(r.get("consumer_durables_yoy_pct") or r.get("durables_yoy")),
                consumer_non_durables_yoy_pct=safe_float_val(r.get("consumer_non_durables_yoy_pct") or r.get("non_durables_yoy")),
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 3: DPIIT Eight Core Industries (ICI) Parser
# ---------------------------------------------------------------------------

def parse_core_industries(payload: Any) -> list[CoreIndustriesRecord]:
    """Parse DPIIT Eight Core Industries records."""
    rows = extract_rows(payload)
    if not rows:
        raise ValueError("Empty or invalid Core Industries payload.")

    records: list[CoreIndustriesRecord] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        period = str(r.get("period") or r.get("month") or "2024-08")
        citation = make_citation(
            authority=_DPIIT_AUTHORITY,
            document_title="Index of Eight Core Industries (ICI)",
            table_reference="dpiit_eight_core_industries_2011_12",
            retrieval_url="https://eaindustry.nic.in/ici",
            observation_period=period,
        )
        records.append(
            CoreIndustriesRecord(
                period=period,
                overall_ici_yoy_pct=safe_float_val(r.get("overall_ici_yoy_pct") or r.get("ici_yoy")),
                coal_yoy_pct=safe_float_val(r.get("coal_yoy_pct") or r.get("coal_yoy")),
                crude_oil_yoy_pct=safe_float_val(r.get("crude_oil_yoy_pct") or r.get("crude_yoy")),
                natural_gas_yoy_pct=safe_float_val(r.get("natural_gas_yoy_pct") or r.get("gas_yoy")),
                refinery_products_yoy_pct=safe_float_val(r.get("refinery_products_yoy_pct") or r.get("refinery_yoy")),
                fertilizers_yoy_pct=safe_float_val(r.get("fertilizers_yoy_pct") or r.get("fertilizers_yoy")),
                steel_yoy_pct=safe_float_val(r.get("steel_yoy_pct") or r.get("steel_yoy")),
                cement_yoy_pct=safe_float_val(r.get("cement_yoy_pct") or r.get("cement_yoy")),
                electricity_yoy_pct=safe_float_val(r.get("electricity_yoy_pct") or r.get("electricity_yoy")),
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 4: Manufacturing GVA & OBICUS Parsers
# ---------------------------------------------------------------------------

def parse_manufacturing_gva(payload: Any) -> list[ManufacturingGVARecord]:
    rows = extract_rows(payload)
    if not rows:
        raise ValueError("Empty or invalid Manufacturing GVA payload.")

    records: list[ManufacturingGVARecord] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        period = str(r.get("period") or "2024-Q1")
        citation = make_citation(
            authority=_RBI_AUTHORITY,
            document_title="Quarterly Estimates of Gross Value Added (GVA)",
            table_reference="real_sector.quarterly_gva_by_economic_activity",
            retrieval_url="https://data-api.dbie.rbihub.in/api/tables/real_sector/quarterly_gva",
            observation_period=period,
        )
        records.append(
            ManufacturingGVARecord(
                period=period,
                manufacturing_gva_real_yoy_pct=safe_float_val(r.get("manufacturing_gva_real_yoy_pct") or r.get("gva_real_yoy")),
                manufacturing_gva_cr=safe_float_val(r.get("manufacturing_gva_cr") or r.get("gva_nominal_cr")),
                manufacturing_share_in_gva_pct=safe_float_val(r.get("manufacturing_share_in_gva_pct") or r.get("share_gva")),
                citation=citation,
            )
        )
    return records


def parse_obicus_capacity(payload: Any) -> list[OBICUSRecord]:
    rows = extract_rows(payload)
    if not rows:
        raise ValueError("Empty or invalid OBICUS payload.")

    records: list[OBICUSRecord] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        period = str(r.get("period") or "2024-Q1")
        citation = make_citation(
            authority=_RBI_AUTHORITY,
            document_title="Order Books, Inventories and Capacity Utilisation Survey (OBICUS)",
            table_reference="real_sector.obicus_capacity_utilisation",
            retrieval_url="https://dbie.rbihub.in/obicus",
            observation_period=period,
        )
        records.append(
            OBICUSRecord(
                period=period,
                capacity_utilisation_pct=safe_float_val(r.get("capacity_utilisation_pct") or r.get("cu_ratio")),
                order_books_growth_yoy_pct=safe_float_val(r.get("order_books_growth_yoy_pct") or r.get("order_books_growth")),
                inventory_to_sales_ratio_pct=safe_float_val(r.get("inventory_to_sales_ratio_pct") or r.get("inv_sales_ratio")),
                citation=citation,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Step 6: Analytics Trend Direction Evaluator
# ---------------------------------------------------------------------------

def evaluate_industrial_trends(
    manufacturing_yoy: float | None,
    capital_goods_yoy: float | None,
    steel_yoy: float | None,
    cement_yoy: float | None,
    capacity_utilisation: float | None,
) -> dict[str, str]:
    """Evaluates directional indicators: ↑ (Positive), ↓ (Negative), → (Flat)."""
    def _arrow(val: float | None) -> str:
        if val is None:
            return "N/A"
        if val > 0:
            return f"{val:+.1f}% ↑"
        if val < 0:
            return f"{val:+.1f}% ↓"
        return f"{val:+.1f}% →"

    cu_str = "N/A"
    if capacity_utilisation is not None:
        if capacity_utilisation >= 75.0:
            cu_str = f"{capacity_utilisation:.1f}% (Robust ↑)"
        elif capacity_utilisation >= 72.0:
            cu_str = f"{capacity_utilisation:.1f}% (Stable →)"
        else:
            cu_str = f"{capacity_utilisation:.1f}% (Subdued ↓)"

    return {
        "Manufacturing IIP": _arrow(manufacturing_yoy),
        "Capital Goods IIP": _arrow(capital_goods_yoy),
        "Core Steel": _arrow(steel_yoy),
        "Core Cement": _arrow(cement_yoy),
        "Capacity Utilisation": cu_str,
    }
