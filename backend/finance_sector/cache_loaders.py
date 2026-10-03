"""Cache loaders for Finance Sector DuckDB.

Retrieves persisted records from sector-isolated DuckDB and reconstructs
strictly typed Pydantic models with DataFreshness.CACHED provenance.
"""
from __future__ import annotations

import json
from typing import Any

from finance_sector import database as db
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
from finance_sector.parsers import parse_period_sort_key


class FinanceDataUnavailableError(Exception):
    """Raised when neither live fetch nor cache can supply data."""


def prepare_cached_citation(citation_data: Any) -> Citation:
    """Deserialise citation dictionary and mark freshness as CACHED."""
    if isinstance(citation_data, str):
        try:
            citation_data = json.loads(citation_data)
        except json.JSONDecodeError:
            citation_data = {}
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


def load_credit_from_cache(lookback_months: int) -> list[BankCreditGrowthRecord]:
    """Load bank credit growth records from DuckDB."""
    rows = db.query_latest_rows("bank_credit_growth", lookback_months)
    if not rows:
        raise FinanceDataUnavailableError(
            "Bank credit growth data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            BankCreditGrowthRecord(
                period=row["period"],
                gross_credit_cr=row.get("gross_credit_cr") or 0.0,
                non_food_credit_cr=row.get("non_food_credit_cr") or 0.0,
                non_food_credit_yoy_pct=row.get("non_food_credit_yoy_pct"),
                sectoral=SectoralCreditBreakdown(
                    agriculture_cr=row.get("agriculture_cr"),
                    industry_cr=row.get("industry_cr"),
                    industry_msme_cr=row.get("industry_msme_cr"),
                    industry_large_cr=row.get("industry_large_cr"),
                    services_cr=row.get("services_cr"),
                    personal_loans_cr=row.get("personal_loans_cr"),
                    personal_housing_cr=row.get("personal_housing_cr"),
                    personal_vehicle_cr=row.get("personal_vehicle_cr"),
                ),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records


def load_asset_quality_from_cache(bank_group: BankGroup, lookback_quarters: int) -> list[NPARecord]:
    """Load asset quality & CRAR records from DuckDB."""
    rows = db.query_latest_rows("asset_quality", lookback_quarters * 5)
    if not rows:
        raise FinanceDataUnavailableError(
            "Asset quality data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        if bank_group != BankGroup.ALL_SCB and row.get("bank_group") != bank_group.value:
            continue
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            NPARecord(
                period=row["period"],
                bank_group=BankGroup(row.get("bank_group", "ALL_SCB")),
                gross_npa_pct=row.get("gross_npa_pct"),
                net_npa_pct=row.get("net_npa_pct"),
                gross_npa_cr=row.get("gross_npa_cr"),
                net_npa_cr=row.get("net_npa_cr"),
                provision_coverage_ratio_pct=row.get("provision_coverage_ratio_pct"),
                crar_pct=row.get("crar_pct"),
                cet1_pct=row.get("cet1_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    retained = records[:lookback_quarters]
    retained.sort(key=lambda r: parse_period_sort_key(r.period))
    return retained


def load_lending_rates_from_cache(lookback_months: int) -> list[LendingRateRecord]:
    """Load lending and deposit rate records from DuckDB."""
    rows = db.query_latest_rows("lending_rates", lookback_months)
    if not rows:
        raise FinanceDataUnavailableError(
            "Lending rates data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            LendingRateRecord(
                period=row["period"],
                walr_fresh_pct=row.get("walr_fresh_pct"),
                walr_outstanding_pct=row.get("walr_outstanding_pct"),
                mclr_1yr_median_pct=row.get("mclr_1yr_median_pct"),
                wadtdr_fresh_pct=row.get("wadtdr_fresh_pct"),
                wadtdr_outstanding_pct=row.get("wadtdr_outstanding_pct"),
                repo_rate_pct=row.get("repo_rate_pct"),
                lending_spread_over_repo_pct=row.get("lending_spread_over_repo_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records


def load_deposits_from_cache(lookback_months: int) -> list[DepositRecord]:
    """Load deposit & CD ratio records from DuckDB."""
    rows = db.query_latest_rows("deposits_cd_ratio", lookback_months)
    if not rows:
        raise FinanceDataUnavailableError(
            "Deposits/CD ratio data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            DepositRecord(
                period=row["period"],
                aggregate_deposits_cr=row.get("aggregate_deposits_cr"),
                deposits_yoy_pct=row.get("deposits_yoy_pct"),
                demand_deposits_cr=row.get("demand_deposits_cr"),
                time_deposits_cr=row.get("time_deposits_cr"),
                casa_ratio_pct=row.get("casa_ratio_pct"),
                bank_credit_cr=row.get("bank_credit_cr"),
                cd_ratio_pct=row.get("cd_ratio_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records
