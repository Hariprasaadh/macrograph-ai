"""Cache loading fallback helpers for External Sector."""
from __future__ import annotations

import json
import logging
from typing import Any

from external_sector import database as db
from external_sector.models import (
    BoPRecord,
    Citation,
    DataFreshness,
    ExchangeRateRecord,
    ExternalDebtRecord,
    ForexReservesRecord,
    RemittancesRecord,
    TradeBalanceRecord,
)
from external_sector.parsers import parse_period_sort_key


class ExternalDataUnavailableError(Exception):
    """Raised when both live fetch and cache fallback fail."""
    pass


logger = logging.getLogger(__name__)

def prepare_cached_citation(citation_raw: Any, default_tool: str = "database_cache") -> Citation:
    """Normalize raw citation object/string from DuckDB."""
    if isinstance(citation_raw, dict):
        return Citation(
            source_agent="external_sector",
            source_authority=citation_raw.get("source_authority", "Reserve Bank of India (RBI)"),
            document_title=citation_raw.get("document_title", "Historical External Record"),
            table_reference=citation_raw.get("table_reference", default_tool),
            retrieval_url=citation_raw.get("retrieval_url", "https://dbie.rbihub.in"),
            observation_period=str(citation_raw.get("observation_period", "historical")),
            freshness=DataFreshness.CACHED,
        )
    if isinstance(citation_raw, str):
        try:
            parsed = json.loads(citation_raw)
            return prepare_cached_citation(parsed, default_tool=default_tool)
        except (ValueError, TypeError) as exc:
            logger.warning("Unparseable cached external citation; using default: %s", exc)
    return Citation(
        source_agent="external_sector",
        source_authority="Reserve Bank of India (RBI)",
        document_title="Historical External Record",
        table_reference=default_tool,
        retrieval_url="https://dbie.rbihub.in",
        observation_period="historical",
        freshness=DataFreshness.CACHED,
    )


def load_forex_from_cache(limit: int) -> list[ForexReservesRecord]:
    rows = db.query_latest_rows("forex_reserves", limit)
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_forex")
        records.append(
            ForexReservesRecord(
                period=row["period"],
                total_reserves_usd_mn=row["total_reserves_usd_mn"],
                foreign_currency_assets_usd_mn=row.get("foreign_currency_assets_usd_mn"),
                gold_reserves_usd_mn=row.get("gold_reserves_usd_mn"),
                sdrs_usd_mn=row.get("sdrs_usd_mn"),
                reserve_tranche_position_usd_mn=row.get("reserve_tranche_position_usd_mn"),
                import_cover_months=row.get("import_cover_months"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    if not records:
        raise ExternalDataUnavailableError("Forex reserves data unavailable: live fetch failed and cache is empty.")
    return records


def load_trade_from_cache(limit: int) -> list[TradeBalanceRecord]:
    rows = db.query_latest_rows("trade_balance", limit)
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_trade")
        exports_usd_bn = row.get("exports_usd_bn")
        if exports_usd_bn is None and row.get("merchandise_exports_usd_mn") is not None:
            exports_usd_bn = row["merchandise_exports_usd_mn"] / 1000.0

        imports_usd_bn = row.get("imports_usd_bn")
        if imports_usd_bn is None and row.get("merchandise_imports_usd_mn") is not None:
            imports_usd_bn = row["merchandise_imports_usd_mn"] / 1000.0

        trade_balance_usd_bn = row.get("trade_balance_usd_bn")
        if trade_balance_usd_bn is None and row.get("merchandise_trade_balance_usd_mn") is not None:
            trade_balance_usd_bn = row["merchandise_trade_balance_usd_mn"] / 1000.0

        oil_imports_usd_bn = row.get("oil_imports_usd_bn")
        if oil_imports_usd_bn is None and row.get("oil_imports_usd_mn") is not None:
            oil_imports_usd_bn = row["oil_imports_usd_mn"] / 1000.0

        non_oil_imports_usd_bn = row.get("non_oil_imports_usd_bn")
        if non_oil_imports_usd_bn is None and row.get("non_oil_imports_usd_mn") is not None:
            non_oil_imports_usd_bn = row["non_oil_imports_usd_mn"] / 1000.0

        services_surplus_usd_bn = row.get("services_surplus_usd_bn")
        if services_surplus_usd_bn is None and row.get("services_trade_balance_usd_mn") is not None:
            services_surplus_usd_bn = row["services_trade_balance_usd_mn"] / 1000.0

        records.append(
            TradeBalanceRecord(
                period=row["period"],
                exports_usd_bn=exports_usd_bn,
                imports_usd_bn=imports_usd_bn,
                trade_balance_usd_bn=trade_balance_usd_bn,
                oil_imports_usd_bn=oil_imports_usd_bn,
                non_oil_imports_usd_bn=non_oil_imports_usd_bn,
                oil_exports_usd_bn=row.get("oil_exports_usd_bn"),
                non_oil_exports_usd_bn=row.get("non_oil_exports_usd_bn"),
                services_surplus_usd_bn=services_surplus_usd_bn,
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    if not records:
        raise ExternalDataUnavailableError("Trade data unavailable: live fetch failed and cache is empty.")
    return records


def load_bop_from_cache(limit: int) -> list[BoPRecord]:
    rows = db.query_latest_rows("bop", limit)
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_bop")
        records.append(
            BoPRecord(
                period=row["period"],
                current_account_balance_usd_bn=row.get("current_account_balance_usd_bn"),
                current_account_to_gdp_pct=row.get("current_account_to_gdp_pct"),
                capital_account_balance_usd_bn=row.get("capital_account_balance_usd_bn"),
                net_bop_usd_bn=row.get("net_bop_usd_bn"),
                services_balance_usd_bn=row.get("services_balance_usd_bn"),
                remittances_usd_bn=row.get("remittances_usd_bn"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    if not records:
        raise ExternalDataUnavailableError("BoP data unavailable: cache is empty.")
    return records


def load_exchange_rates_from_cache(limit: int) -> list[ExchangeRateRecord]:
    rows = db.query_latest_rows("exchange_rates", limit)
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_fx")
        records.append(
            ExchangeRateRecord(
                period=row["period"],
                usd_inr_rate=row.get("usd_inr_rate"),
                reer_40_basket=row.get("reer_40_basket"),
                neer_40_basket=row.get("neer_40_basket"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    if not records:
        raise ExternalDataUnavailableError("Exchange-rate data unavailable: live fetch failed and cache is empty.")
    return records


def load_remittances_from_cache(limit: int) -> list[RemittancesRecord]:
    rows = db.query_latest_rows("remittances_invisibles", limit)
    if not rows:
        raise ExternalDataUnavailableError("Remittances data unavailable: live fetch failed and cache is empty.")
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_remittances")
        records.append(
            RemittancesRecord(
                period=row["period"],
                private_transfers_net_usd_mn=row.get("private_transfers_net_usd_mn"),
                receipts_usd_mn=row.get("receipts_usd_mn"),
                payments_usd_mn=row.get("payments_usd_mn"),
                services_receipts_usd_mn=row.get("services_receipts_usd_mn"),
                services_net_usd_mn=row.get("services_net_usd_mn"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    return records


def load_external_debt_from_cache(limit: int) -> list[ExternalDebtRecord]:
    rows = db.query_latest_rows("external_debt", limit)
    if not rows:
        raise ExternalDataUnavailableError("External debt data unavailable: live fetch failed and cache is empty.")
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_debt")
        records.append(
            ExternalDebtRecord(
                period=row["period"],
                total_debt_usd_bn=row.get("total_debt_usd_bn"),
                total_debt_inr_cr=row.get("total_debt_inr_cr"),
                general_government_usd_bn=row.get("general_government_usd_bn"),
                short_term_debt_usd_bn=row.get("short_term_debt_usd_bn"),
                short_term_to_reserves_pct=row.get("short_term_to_reserves_pct"),
                debt_to_gdp_pct=row.get("debt_to_gdp_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    return records
