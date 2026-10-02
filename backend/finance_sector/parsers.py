"""Payload parsers and conversion helpers for the Finance Sector.

Transforms raw JSON payloads from RBI DBIE CDN and Postgres REST APIs
into strictly typed Pydantic models with mandatory Citation metadata.
"""
from __future__ import annotations

import re
from typing import Any

from finance_sector.config import finance_settings
from finance_sector.models import (
    BankCreditGrowthRecord,
    BankGroup,
    Citation,
    DataFreshness,
    DepositRecord,
    LendingRateRecord,
    NPARecord,
    SectoralCreditBreakdown,
)

_DBIE_AUTHORITY = "Reserve Bank of India (RBI)"
_DBIE_BASE_URL = "https://dev.dbie.rbihub.in"


def safe_float_val(value: Any) -> float | None:
    """Safely convert any numeric or string representation to a float, or None."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            clean = value.replace(",", "").strip()
            if not clean or clean.lower() in ("null", "none", "-", ""):
                return None
            return float(clean)
        return float(value)
    except (TypeError, ValueError):
        return None


def map_bank_group(raw: str) -> BankGroup:
    """Map DBIE group string to BankGroup enum."""
    mapping = {
        "ALL": BankGroup.ALL_SCB,
        "PUBLIC": BankGroup.PUBLIC_SECTOR,
        "PRIVATE": BankGroup.PRIVATE_SECTOR,
        "FOREIGN": BankGroup.FOREIGN_BANKS,
        "SFB": BankGroup.SMALL_FINANCE,
        "SMALL FINANCE": BankGroup.SMALL_FINANCE,
        "PSB": BankGroup.PUBLIC_SECTOR,
    }
    for key, value in mapping.items():
        if key in raw.upper():
            return value
    return BankGroup.ALL_SCB


def make_citation(
    document_title: str,
    table_reference: str,
    observation_period: str,
    freshness: DataFreshness = DataFreshness.LIVE,
) -> Citation:
    """Generate a standard Citation for RBI DBIE observations."""
    return Citation(
        source_authority=_DBIE_AUTHORITY,
        document_title=document_title,
        table_reference=table_reference,
        retrieval_url=f"{_DBIE_BASE_URL}/statistics?table={table_reference}",
        observation_period=observation_period,
        freshness=freshness,
    )


def extract_rows(payload: Any) -> list[Any]:
    """Universally extracts rows whether the payload is a List or a Dict with 'rows', 'data', 'items'."""
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


# ── Pillar 1: Bank Credit Growth Parser ───────────────────────────────────

def parse_credit_records(payload: Any) -> list[BankCreditGrowthRecord]:
    """Parse CDN JSON into typed BankCreditGrowthRecord list.
    
    Supports both RBI CDN structure (periods + items) and row-based structures.
    """
    if not isinstance(payload, dict):
        raise ValueError("Unexpected credit payload type.")

    # 1. CDN Structure with 'periods' and 'items'
    if "periods" in payload and "items" in payload:
        periods: list[str] = payload.get("periods", [])
        raw_items: list[dict] = payload.get("items", [])
        if not periods or not raw_items:
            raise ValueError("Empty periods or items in credit payload.")

        items: dict[str, list[Any]] = {
            it.get("label", "").strip(): it.get("values", []) for it in raw_items
        }

        def find_item_values(*patterns: str) -> list[Any]:
            for pat in patterns:
                for k, vals in items.items():
                    if pat.lower() in k.lower():
                        return vals
            return []

        gross_vals = find_item_values("Gross Bank Credit (II+III)", "Gross Bank Credit", "Gross Credit")
        non_food_vals = find_item_values("Non-food Credit", "Non-Food")
        agri_vals = find_item_values("Agriculture & Allied", "Agriculture")
        ind_vals = find_item_values("Industry(Micro and Small", "Industry")
        msme_vals = find_item_values("Micro and Small", "MSME")
        large_vals = find_item_values("Large")
        services_vals = find_item_values("Services")
        personal_vals = find_item_values("Personal Loans")
        housing_vals = find_item_values("Housing")
        vehicle_vals = find_item_values("Vehicle Loans")

        records: list[BankCreditGrowthRecord] = []
        for idx, period in enumerate(periods):
            # Allow live observation periods up to 2026 (exclude 2027+)
            if any(str(yr) in period for yr in (2027, 2028, 2029)):
                continue

            gross = safe_float_val(gross_vals[idx]) if idx < len(gross_vals) else 0.0
            non_food = safe_float_val(non_food_vals[idx]) if idx < len(non_food_vals) else 0.0

            # Calculate 1-year YoY growth (12 monthly periods per year)
            yoy: float | None = None
            if idx >= 12 and idx < len(non_food_vals):
                prior_val = safe_float_val(non_food_vals[idx - 12])
                if prior_val and prior_val > 0 and non_food:
                    yoy = round(((non_food - prior_val) / prior_val) * 100, 2)

            records.append(
                BankCreditGrowthRecord(
                    period=str(period),
                    gross_credit_cr=gross or 0.0,
                    non_food_credit_cr=non_food or 0.0,
                    non_food_credit_yoy_pct=yoy,
                    sectoral=SectoralCreditBreakdown(
                        agriculture_cr=safe_float_val(agri_vals[idx]) if idx < len(agri_vals) else None,
                        industry_cr=safe_float_val(ind_vals[idx]) if idx < len(ind_vals) else None,
                        industry_msme_cr=safe_float_val(msme_vals[idx]) if idx < len(msme_vals) else None,
                        industry_large_cr=safe_float_val(large_vals[idx]) if idx < len(large_vals) else None,
                        services_cr=safe_float_val(services_vals[idx]) if idx < len(services_vals) else None,
                        personal_loans_cr=safe_float_val(personal_vals[idx]) if idx < len(personal_vals) else None,
                        personal_housing_cr=safe_float_val(housing_vals[idx]) if idx < len(housing_vals) else None,
                        personal_vehicle_cr=safe_float_val(vehicle_vals[idx]) if idx < len(vehicle_vals) else None,
                    ),
                    citation=make_citation(
                        document_title="RBI DBIE — Sectoral Deployment of Non-Food Gross Bank Credit",
                        table_reference="financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                        observation_period=str(period),
                        freshness=DataFreshness.LIVE,
                    ),
                )
            )
        return records

    # 2. Row/dict fallback structure
    rows: list[Any] = extract_rows(payload)
    if not rows:
        raise ValueError("No rows in credit payload.")

    records = []
    for row in rows:
        if isinstance(row, dict):
            period = row.get("period") or row.get("date") or "unknown"
            records.append(
                BankCreditGrowthRecord(
                    period=str(period),
                    gross_credit_cr=safe_float_val(row.get("total_gross_credit")) or 0.0,
                    non_food_credit_cr=safe_float_val(row.get("non_food_credit")) or 0.0,
                    non_food_credit_yoy_pct=safe_float_val(row.get("non_food_credit_yoy")),
                    sectoral=SectoralCreditBreakdown(
                        agriculture_cr=safe_float_val(row.get("agriculture")),
                        industry_cr=safe_float_val(row.get("industry")),
                        industry_msme_cr=safe_float_val(row.get("micro_small_medium")),
                        industry_large_cr=safe_float_val(row.get("large_industry")),
                        services_cr=safe_float_val(row.get("services")),
                        personal_loans_cr=safe_float_val(row.get("personal_loans")),
                        personal_housing_cr=safe_float_val(row.get("housing")),
                        personal_vehicle_cr=safe_float_val(row.get("vehicle_loans")),
                    ),
                    citation=make_citation(
                        document_title="RBI DBIE — Sectoral Deployment of Non-Food Gross Bank Credit",
                        table_reference="financial_sector.r539_deployment_of_bank_credit_by_major_sectors",
                        observation_period=str(period),
                    ),
                )
            )
    return records


# ── Pillar 2: Asset Quality & Capital Adequacy Parser ─────────────────────

def parse_asset_quality(
    npa_payload: Any,
    crar_payload: Any,
    bank_group: BankGroup,
    lookback_quarters: int,
) -> list[NPARecord]:
    """Parse NPA and CRAR API payloads into typed NPARecord list.
    
    Handles both list-of-lists rows from the Postgres REST API and list-of-dicts.
    """
    raw_npa_rows: list[Any] = extract_rows(npa_payload)

    records: list[NPARecord] = []

    # Handle list-of-lists format from r330 table
    for row in raw_npa_rows:
        if isinstance(row, list) and len(row) > 10:
            if bank_group != BankGroup.ALL_SCB:
                continue
            row_no = safe_float_val(row[3])
            # Rows 12-22 represent aggregate All Scheduled Commercial Banks
            if row_no and row_no > 25:
                continue

            period_str = str(row[4] or "").strip()
            if "-" in period_str and period_str[:4].isdigit():
                gross_adv = safe_float_val(row[5])
                net_adv = safe_float_val(row[6])
                gnpa = safe_float_val(row[7])
                gnpa_pct = round((gnpa / gross_adv * 100), 2) if gross_adv and gnpa else safe_float_val(row[8])
                nnpa = safe_float_val(row[10])
                nnpa_pct = round((nnpa / net_adv * 100), 2) if net_adv and nnpa else (safe_float_val(row[11]) if len(row) > 11 else None)
                pcr = round(((gnpa - nnpa) / gnpa * 100), 2) if gnpa and nnpa else None

                records.append(
                    NPARecord(
                        period=period_str,
                        bank_group=BankGroup.ALL_SCB,
                        gross_npa_pct=gnpa_pct,
                        net_npa_pct=nnpa_pct,
                        gross_npa_cr=gnpa,
                        net_npa_cr=nnpa,
                        provision_coverage_ratio_pct=pcr,
                        crar_pct=None,
                        cet1_pct=None,
                        citation=make_citation(
                            document_title="RBI DBIE — Gross and Net NPAs of Scheduled Commercial Banks",
                            table_reference="financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou",
                            observation_period=period_str,
                            freshness=DataFreshness.LIVE,
                        ),
                    )
                )
        elif isinstance(row, dict):
            row_group = str(row.get("bank_group") or "ALL")
            if bank_group != BankGroup.ALL_SCB and row_group.upper() not in bank_group.value:
                continue
            period = str(row.get("period") or row.get("year") or "unknown")
            records.append(
                NPARecord(
                    period=period,
                    bank_group=map_bank_group(row_group),
                    gross_npa_pct=safe_float_val(row.get("gross_npa_pct") or row.get("gnpa_pct")),
                    net_npa_pct=safe_float_val(row.get("net_npa_pct") or row.get("nnpa_pct")),
                    gross_npa_cr=safe_float_val(row.get("gross_npa") or row.get("gnpa_cr")),
                    net_npa_cr=safe_float_val(row.get("net_npa") or row.get("nnpa_cr")),
                    provision_coverage_ratio_pct=safe_float_val(row.get("pcr") or row.get("provision_coverage_ratio")),
                    crar_pct=safe_float_val(row.get("crar")),
                    cet1_pct=safe_float_val(row.get("cet1")),
                    citation=make_citation(
                        document_title="RBI DBIE — Gross and Net NPAs of Scheduled Commercial Banks",
                        table_reference="financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks_bank_grou",
                        observation_period=period,
                        freshness=DataFreshness.LIVE,
                    ),
                )
            )

    if not records:
        raise ValueError("Could not extract NPA records from payload.")

    records.sort(key=lambda r: r.period)
    return records[-lookback_quarters:]


# ── Pillar 3: Lending Rates Parser ────────────────────────────────────────

def parse_lending_rates(payload: Any, lookback_months: int) -> list[LendingRateRecord]:
    """Parse key rates API payload into typed LendingRateRecord list.
    
    Safely inspects both dictionary and list-of-lists rows.
    """
    raw_rows: list[Any] = extract_rows(payload)
    if not raw_rows:
        raise ValueError("No rows in lending rates payload.")

    records: list[LendingRateRecord] = []
    for row in raw_rows:
        if isinstance(row, dict):
            period = str(row.get("period") or row.get("month") or row.get("date") or "unknown")
            records.append(
                LendingRateRecord(
                    period=period,
                    walr_fresh_pct=safe_float_val(row.get("walr_fresh") or row.get("walr_new_loans")),
                    walr_outstanding_pct=safe_float_val(row.get("walr_outstanding") or row.get("walr_old_loans")),
                    mclr_1yr_median_pct=safe_float_val(row.get("mclr_1yr") or row.get("mclr_median_1yr")),
                    wadtdr_fresh_pct=safe_float_val(row.get("wadtdr_fresh") or row.get("term_deposit_rate_fresh")),
                    wadtdr_outstanding_pct=safe_float_val(row.get("wadtdr_outstanding") or row.get("term_deposit_rate_outstanding")),
                    repo_rate_pct=safe_float_val(row.get("repo_rate")),
                    citation=make_citation(
                        document_title="RBI DBIE — Key Rates (WALR, MCLR, WADTDR)",
                        table_reference="financial_sector.r531_key_rates",
                        observation_period=period,
                        freshness=DataFreshness.LIVE,
                    ),
                )
            )
        elif isinstance(row, list) and len(row) > 6:
            period_str = str(row[4] or "").strip()
            # If row has a date and numeric rate data
            if any(re.match(r"\d{2}-\d{2}-\d{4}", period_str) or re.match(r"\d{4}", period_str) for _ in [1]):
                bank_rate = safe_float_val(row[5])
                repo_rate = safe_float_val(row[6])
                records.append(
                    LendingRateRecord(
                        period=period_str,
                        walr_fresh_pct=None,
                        walr_outstanding_pct=None,
                        mclr_1yr_median_pct=None,
                        wadtdr_fresh_pct=None,
                        wadtdr_outstanding_pct=None,
                        repo_rate_pct=repo_rate,
                        citation=make_citation(
                            document_title="RBI DBIE — Key Rates (WALR, MCLR, WADTDR)",
                            table_reference="financial_sector.r531_key_rates",
                            observation_period=period_str,
                            freshness=DataFreshness.LIVE,
                        ),
                    )
                )

    if not records:
        raise ValueError("No parseable rate rows found in payload.")

    records.sort(key=lambda r: r.period)
    return records[-lookback_months:]


# ── Pillar 4: Deposits & CD Ratio Parser ──────────────────────────────────

def parse_deposits(survey: Any, business: Any, lookback_months: int) -> list[DepositRecord]:
    """Parse Commercial Bank Survey and Business of SCBs payloads."""
    survey_data: list[Any] = extract_rows(survey)
    if not survey_data:
        raise ValueError("No data in commercial bank survey.")

    records: list[DepositRecord] = []
    # Sort fortnights ascending
    sorted_survey = sorted(survey_data, key=lambda x: str(x.get("fortnight") or x.get("period") or ""))

    for idx, row in enumerate(sorted_survey):
        if isinstance(row, dict):
            period = str(row.get("fortnight") or row.get("period") or "unknown")
            # Allow live observation periods up to 2026 (exclude 2027+)
            if any(str(yr) in period for yr in (2027, 2028, 2029)):
                continue

            # Support both coded keys (ci, ci1, ci2, si) and named keys
            dep_val = safe_float_val(row.get("ci") or row.get("aggregate_deposits") or row.get("deposits"))
            demand_val = safe_float_val(row.get("ci1") or row.get("demand_deposits"))
            time_val = safe_float_val(row.get("ci2") or row.get("time_deposits"))
            credit_val = safe_float_val(row.get("si") or row.get("bank_credit") or row.get("credit"))

            # Calculate YoY % if prior year fortnight exists (approx 26 fortnights)
            yoy: float | None = None
            if idx >= 26 and dep_val:
                prior_row = sorted_survey[idx - 26]
                prior_dep = safe_float_val(prior_row.get("ci") or prior_row.get("aggregate_deposits"))
                if prior_dep and prior_dep > 0:
                    yoy = round(((dep_val - prior_dep) / prior_dep) * 100, 2)

            casa: float | None = None
            if demand_val is not None and dep_val and dep_val > 0:
                casa = round((demand_val / dep_val) * 100, 2)

            cd_ratio: float | None = None
            if credit_val and dep_val and dep_val > 0:
                cd_ratio = round((credit_val / dep_val) * 100, 2)

            records.append(
                DepositRecord(
                    period=period,
                    aggregate_deposits_cr=dep_val,
                    deposits_yoy_pct=yoy or safe_float_val(row.get("deposits_yoy")),
                    demand_deposits_cr=demand_val,
                    time_deposits_cr=time_val,
                    casa_ratio_pct=casa,
                    bank_credit_cr=credit_val,
                    cd_ratio_pct=cd_ratio,
                    citation=make_citation(
                        document_title="RBI DBIE — Commercial Bank Survey (Fortnightly Form A)",
                        table_reference="financial_sector.r689_business_of_scheduled_banks",
                        observation_period=period,
                        freshness=DataFreshness.LIVE,
                    ),
                )
            )

    records.sort(key=lambda r: r.period)
    return records[-lookback_months:]
