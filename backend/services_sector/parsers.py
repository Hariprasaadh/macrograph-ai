"""Payload parsers and conversion helpers for the Services Sector."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from services_sector.models import (
    Citation,
    DataFreshness,
    ISPRecord,
    ServicesGVARecord,
    ServicesPMIRecord,
    ServiceSubSector,
    TransportFreightRecord,
)

_MOSPI_AUTHORITY = "National Statistical Office (NSO), MoSPI"
_MOSPI_MCP_URL = "https://mcp.mospi.gov.in"

# NAS industry name → conceptual NAS statement label (Statements 8.9–8.14).
# The MCP exposes NAS GVA by industry_code; these labels preserve the
# statement taxonomy used across the sector's docs and API.
_NAS_STATEMENT_LABELS: dict[str, str] = {
    "Trade, Hotels, Transport, Communication & Services Related to Broadcasting": "8.9–8.11",
    "Trade, Repair, Hotels and Restaurants": "8.9",
    "Transport, Storage, Communication & Services Related to Broadcasting": "8.10–8.11",
    "Financial, Real Estate & Professional Services": "8.12–8.13",
    "Financial Services": "8.12",
    "Real Estate, Ownership of Dwelling & Professional Services": "8.13",
    "Public Administration, Defence & Other Services": "8.14",
    "Other Services": "8.14",
}

# NAS estimate-revision priority: prefer finalised estimates per year.
_REVISION_PRIORITY: dict[str, int] = {
    "Final Estimates": 5,
    "Second Revised Estimates": 4,
    "First Revised Estimates": 3,
    "Revised Estimates": 3,
    "Provisional Estimates": 2,
    "Advance Estimates": 1,
}

# MoSPI ISP sub-sector label → enum mapping
_SUB_SECTOR_KEYWORDS: dict[str, ServiceSubSector] = {
    "wholesale": ServiceSubSector.WHOLESALE_TRADE,
    "retail": ServiceSubSector.RETAIL_TRADE,
    "repair": ServiceSubSector.REPAIR_SERVICES,
    "accommodation": ServiceSubSector.ACCOMMODATION_FOOD,
    "hotel": ServiceSubSector.ACCOMMODATION_FOOD,
    "food": ServiceSubSector.ACCOMMODATION_FOOD,
    "railway": ServiceSubSector.RAILWAY_TRANSPORT,
    "rail": ServiceSubSector.RAILWAY_TRANSPORT,
    "road": ServiceSubSector.ROAD_TRANSPORT,
    "water": ServiceSubSector.WATER_TRANSPORT,
    "air": ServiceSubSector.AIR_TRANSPORT,
    "aviation": ServiceSubSector.AIR_TRANSPORT,
    "warehous": ServiceSubSector.WAREHOUSING_SUPPORT,
    "support activities for transportation": ServiceSubSector.WAREHOUSING_SUPPORT,
    "postal": ServiceSubSector.POSTAL_COURIER,
    "courier": ServiceSubSector.POSTAL_COURIER,
    "telecom": ServiceSubSector.TELECOMMUNICATIONS,
    "broadcast": ServiceSubSector.INFORMATION_BROADCASTING,
    "information": ServiceSubSector.INFORMATION_BROADCASTING,
    "banking": ServiceSubSector.BANKING,
    "insurance": ServiceSubSector.INSURANCE,
    "real estate": ServiceSubSector.REAL_ESTATE,
    "it & computer": ServiceSubSector.IT_COMPUTER,
    "it and computer": ServiceSubSector.IT_COMPUTER,
    "computer related": ServiceSubSector.IT_COMPUTER,
    "professional": ServiceSubSector.PROFESSIONAL_TECHNICAL,
    "scientific": ServiceSubSector.PROFESSIONAL_TECHNICAL,
    "technical": ServiceSubSector.PROFESSIONAL_TECHNICAL,
    "administrative": ServiceSubSector.ADMIN_SUPPORT,
    "arts": ServiceSubSector.ARTS_ENTERTAINMENT,
    "entertainment": ServiceSubSector.ARTS_ENTERTAINMENT,
    "recreation": ServiceSubSector.ARTS_ENTERTAINMENT,
    "general": ServiceSubSector.GENERAL,
}


def safe_float_val(value: Any) -> float | None:
    """Safely convert any numeric or string representation to a float, or None."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            clean = value.replace(",", "").strip()
            if not clean or clean.lower() in ("null", "none", "-", "", "p"):
                return None
            return float(clean)
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_period_sort_key(period_str: str) -> tuple[int, int, int, str]:
    """Parse any period string into a chronological sort key tuple (year, month, day, text)."""
    s = str(period_str).strip()
    m1 = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m1:
        return (int(m1.group(1)), int(m1.group(2)), int(m1.group(3)), s)
    m2 = re.match(r"^(\d{4})-(\d{2})$", s)
    if m2:
        return (int(m2.group(1)), int(m2.group(2)), 1, s)
    m3 = re.match(r"^(\d{4})-(\d{2,4})$", s)
    if m3:
        return (int(m3.group(1)), 3, 31, s)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d-%b-%Y", "%d-%b-%y", "%b - %Y", "%d-%m-%Y"):
        try:
            cleaned = " ".join(s.split())
            dt = datetime.strptime(cleaned, fmt)
            return (dt.year, dt.month, dt.day, s)
        except ValueError:
            pass
    return (0, 0, 0, s)


def map_sub_sector(raw: str) -> ServiceSubSector:
    """Map a MoSPI ISP sub-sector label to the ServiceSubSector enum."""
    lowered = str(raw).strip().lower()
    for keyword, sector in _SUB_SECTOR_KEYWORDS.items():
        if keyword in lowered:
            return sector
    return ServiceSubSector.GENERAL


def make_citation(
    document_title: str,
    table_reference: str,
    observation_period: str,
    source_authority: str = _MOSPI_AUTHORITY,
    freshness: DataFreshness = DataFreshness.LIVE,
) -> Citation:
    """Generate a standard Citation for MoSPI observations."""
    return Citation(
        source_authority=source_authority,
        document_title=document_title,
        table_reference=table_reference,
        retrieval_url=_MOSPI_MCP_URL,
        observation_period=observation_period,
        freshness=freshness,
    )


def extract_rows(payload: Any) -> list[Any]:
    """Universally extracts rows whether the payload is a List or a Dict."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "items", "records", "result", "sheets"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


# ── Pillar 1: ISP Parser ────────────────────────────────────────────────────
# Live MCP row format (verified): {"base_year": "2024-25", "year": "2025-26",
#   "frequency": "Monthly", "month": "July",
#   "broad_sub_sector": "IT & computer related services",
#   "index": "146.5", "growth_rate": null}.
# NOTE: the MCP view publishes the 19 sub-sectors only — no separate General
# index row. GENERAL records are therefore emitted only if ever returned.

def parse_isp_records(payload: Any, lookback_months: int) -> list[ISPRecord]:
    """Parse MoSPI ISP get_data payload into typed ISPRecord list."""
    from services_sector.mospi_client import isp_month_to_period

    rows: list[Any] = extract_rows(payload)
    if not rows:
        raise ValueError("No rows in ISP payload.")

    records: list[ISPRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fy_year = str(row.get("year") or "").strip()
        month_name = str(row.get("month") or "").strip()
        if not fy_year or not month_name:
            continue
        period = isp_month_to_period(fy_year, month_name)
        if any(str(yr) in period for yr in (2027, 2028, 2029)):
            continue
        sub_label = str(row.get("broad_sub_sector") or "General")
        records.append(
            ISPRecord(
                period=period,
                sub_sector=map_sub_sector(sub_label),
                isp_index=safe_float_val(row.get("index")),
                isp_yoy_pct=safe_float_val(row.get("growth_rate")),
                isp_mom_pct=None,
                citation=make_citation(
                    "Index of Service Production (ISP) Monthly Release",
                    "mospi.isp_monthly",
                    period,
                ),
            )
        )

    if not records:
        raise ValueError("No parseable ISP rows in payload.")

    # The MCP growth_rate is null in practice — derive YoY/MoM from levels.
    records.sort(key=lambda r: (r.sub_sector.value, parse_period_sort_key(r.period)))
    by_sector: dict[str, list[ISPRecord]] = {}
    for r in records:
        by_sector.setdefault(r.sub_sector.value, []).append(r)
    for series in by_sector.values():
        for idx, rec in enumerate(series):
            if rec.isp_yoy_pct is None and idx >= 12:
                prior = series[idx - 12].isp_index
                if prior and prior > 0 and rec.isp_index:
                    rec.isp_yoy_pct = round(((rec.isp_index - prior) / prior) * 100, 2)
            if rec.isp_mom_pct is None and idx >= 1:
                prior = series[idx - 1].isp_index
                if prior and prior > 0 and rec.isp_index:
                    rec.isp_mom_pct = round(((rec.isp_index - prior) / prior) * 100, 2)

    records.sort(key=lambda r: parse_period_sort_key(r.period))
    general = [r for r in records if r.sub_sector == ServiceSubSector.GENERAL]
    others = [r for r in records if r.sub_sector != ServiceSubSector.GENERAL]
    tail_general = general[-lookback_months:] if len(general) > lookback_months else general
    tail_others = others[-(lookback_months * 4):] if len(others) > lookback_months * 4 else others
    return sorted(tail_general + tail_others, key=lambda r: parse_period_sort_key(r.period))


# ── Pillar 2: Services GVA (NAS) Parser ─────────────────────────────────────
# Live MCP row format (verified): {"base_year": "2011-12", "series": "Current",
#   "year": "2023-24", "indicator": "Gross Value Added", "frequency": "Annual",
#   "revision": "First Revised Estimates", "industry": "Financial Services",
#   "subindustry": null, "current_price": "1598185", "constant_price": "972874",
#   "unit": "₹ Crore"}.

def parse_services_gva(payload: Any) -> list[ServicesGVARecord]:
    """Parse MoSPI NAS get_data payload into typed ServicesGVARecord list."""
    rows: list[Any] = extract_rows(payload)
    if not rows:
        raise ValueError("No rows in NAS services GVA payload.")

    # Keep the best (most finalised) revision per (industry, year).
    best: dict[tuple[str, str], dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        industry = str(row.get("industry") or "").strip()
        year = str(row.get("year") or "").strip()
        if not industry or not year:
            continue
        revision = str(row.get("revision") or "")
        key = (industry, year)
        current = best.get(key)
        if current is None or _REVISION_PRIORITY.get(revision, 0) >= _REVISION_PRIORITY.get(
            str(current.get("revision") or ""), 0
        ):
            best[key] = row

    by_industry: dict[str, list[tuple[str, dict]]] = {}
    for (industry, year), row in best.items():
        by_industry.setdefault(industry, []).append((year, row))

    records: list[ServicesGVARecord] = []
    for industry, series in by_industry.items():
        series.sort(key=lambda item: parse_period_sort_key(item[0]))
        for idx, (year, row) in enumerate(series):
            current_price = safe_float_val(row.get("current_price"))
            constant_price = safe_float_val(row.get("constant_price"))
            yoy: float | None = None
            if idx >= 1:
                prior = safe_float_val(series[idx - 1][1].get("constant_price"))
                if prior and prior > 0 and constant_price:
                    yoy = round(((constant_price - prior) / prior) * 100, 2)
            statement = _NAS_STATEMENT_LABELS.get(industry, "8.x")
            records.append(
                ServicesGVARecord(
                    period=year,
                    nas_statement=statement,
                    segment=industry,
                    gva_current_cr=current_price,
                    gva_constant_cr=constant_price,
                    gva_yoy_pct=yoy,
                    citation=make_citation(
                        f"National Accounts Statistics — {industry} (GVA)",
                        "mospi.nas_gva_annual",
                        year,
                    ),
                )
            )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records


# ── Pillar 3: Services PMI Parser ───────────────────────────────────────────

def parse_services_pmi(payload: Any, lookback_months: int) -> list[ServicesPMIRecord]:
    """Parse PMI payload (press-release mirror) into typed ServicesPMIRecord list."""
    rows: list[Any] = extract_rows(payload)
    if not rows:
        raise ValueError("No rows in services PMI payload.")

    records: list[ServicesPMIRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        period = str(row.get("period") or row.get("month") or row.get("date") or "unknown")
        records.append(
            ServicesPMIRecord(
                period=period,
                headline_pmi=safe_float_val(row.get("headline_pmi") or row.get("pmi")),
                new_orders_idx=safe_float_val(row.get("new_orders") or row.get("new_orders_idx")),
                input_costs_idx=safe_float_val(row.get("input_costs") or row.get("input_costs_idx")),
                employment_idx=safe_float_val(row.get("employment") or row.get("employment_idx")),
                citation=Citation(
                    source_authority="S&P Global / HSBC",
                    document_title="HSBC India Services PMI Press Release",
                    table_reference="sp_global.services_pmi_india",
                    retrieval_url="https://www.pmi.spglobal.com",
                    observation_period=period,
                    freshness=DataFreshness.LIVE,
                ),
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records[-lookback_months:] if len(records) > lookback_months else records


# ── Pillar 4: Telecom Penetration (NSS80 CMST) Parser ────────────────────────
# Live MCP row format (verified): {"indicator": "Percentage of households
#   possessing landline, mobile phone and optical fiber connectivity",
#   "state": "All-India", "mobile_household_assets": "Smartphone only",
#   "sector": "Rural", "value": "53"}. Values are % of households — a
# point-in-time survey wave, so yoy is always None and period is the survey
# round label.

def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).strip().lower())
    return slug.strip("_")[:60] or "unknown"


def parse_transport_freight(payload: Any, lookback_months: int) -> list[TransportFreightRecord]:
    """Parse NSS80 CMST telecom-penetration payload into typed records."""
    rows: list[Any] = extract_rows(payload)
    if not rows:
        raise ValueError("No rows in NSS80 telecom payload.")

    records: list[TransportFreightRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = safe_float_val(row.get("value"))
        if value is None:
            continue
        asset = str(
            row.get("mobile_household_assets")
            or row.get("internet_asset")
            or row.get("category")
            or "overall"
        )
        sector = str(row.get("sector") or "All").strip().lower()
        indicator = f"telecom_{_slug(asset)}_{sector}"
        records.append(
            TransportFreightRecord(
                period="NSS80",
                indicator=indicator,
                value=value,
                unit="% of households",
                yoy_pct=None,
                citation=make_citation(
                    str(row.get("indicator") or "NSS 80th Round — Comprehensive Modular Survey: Telecom"),
                    "mospi.nss80_cmst",
                    "NSS80",
                ),
            )
        )
    records.sort(key=lambda r: (r.indicator, parse_period_sort_key(r.period)))
    return records[-lookback_months:] if len(records) > lookback_months else records
