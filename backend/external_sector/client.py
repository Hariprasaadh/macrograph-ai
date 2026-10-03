"""Unified client for India's External Sector.

Integrates authoritative data from:
1. RBI DBIE Live APIs (Forex reserves, daily exchange rates, merchandise trade)
2. MoSPI eSankhyiki MCP (Quarterly invisibles/remittances, external debt structure)
3. IMF SDMX 3.0 MCP Server (WEO medium-term CAD/GDP projections and trade benchmarks)
4. Yahoo Finance Market Client (Intraday spot FX & Brent crude benchmark)
5. Tavily AI Search (Breaking real-time macroeconomic news & external shocks)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from external_sector.cache_loaders import (
    ExternalDataUnavailableError,
    load_bop_from_cache,
    load_exchange_rates_from_cache,
    load_external_debt_from_cache,
    load_forex_from_cache,
    load_remittances_from_cache,
    load_trade_from_cache,
    prepare_cached_citation,
)
from external_sector import database as db
from external_sector.dbie_client import (
    fetch_raw_exchange_rates,
    fetch_raw_forex,
    fetch_raw_trade,
)
from external_sector.imf_client import fetch_imf_external_outlook, imf_client
from external_sector.market_client import fetch_live_market_rates as get_live_rates
from external_sector.models import (
    BoPRecord,
    Citation,
    DataFreshness,
    ExchangeRateRecord,
    ExternalDebtRecord,
    ExternalFlowsRecord,
    ForexReservesRecord,
    IMFExternalOutlookRecord,
    LiveMarketRatesRecord,
    RealtimeIntelligenceRecord,
    RemittancesRecord,
    TradeBalanceRecord,
)
from external_sector.mospi_client import fetch_mospi_rbi_dataset
from external_sector.parsers import (
    parse_exchange_rates,
    parse_forex_reserves,
    parse_mospi_external_debt,
    parse_mospi_invisibles,
    parse_period_sort_key,
    parse_trade_balance,
    safe_float_val,
)
from external_sector.tavily_client import fetch_realtime_intelligence as get_realtime_news

logger = logging.getLogger(__name__)


# ── Pillar 1: Trade Balance & Critical Dependency ─────────────────────────

async def fetch_trade_balance(lookback_months: int = 24) -> list[TradeBalanceRecord]:
    """Fetch merchandise & services trade data, prioritizing live RBI DBIE with MoSPI composition."""
    db.initialise_schema()
    try:
        raw_items = await fetch_raw_trade(limit=lookback_months * 4)
        records = parse_trade_balance(raw_items, lookback_months)
        if not records:
            raise ValueError("Parsed trade balance returned 0 records.")

        now = datetime.now(timezone.utc).isoformat()
        db_rows = [
            {
                "period": r.period,
                "exports_usd_bn": r.exports_usd_bn,
                "imports_usd_bn": r.imports_usd_bn,
                "trade_balance_usd_bn": r.trade_balance_usd_bn,
                "oil_imports_usd_bn": r.oil_imports_usd_bn,
                "non_oil_imports_usd_bn": r.non_oil_imports_usd_bn,
                "oil_exports_usd_bn": r.oil_exports_usd_bn,
                "non_oil_exports_usd_bn": r.non_oil_exports_usd_bn,
                "services_surplus_usd_bn": r.services_surplus_usd_bn,
                "citation": r.citation.model_dump_json(),
                "fetched_at": now,
            }
            for r in records
        ]
        written = db.upsert_rows("trade_balance", db_rows)
        db.log_fetch("get_trade_balance", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live trade fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_trade_balance", "cache_fallback", error_msg=str(exc))
        return load_trade_from_cache(lookback_months)


# ── Pillar 2: Balance of Payments (BoP) ───────────────────────────────────

async def fetch_balance_of_payments(lookback_quarters: int = 8) -> list[BoPRecord]:
    """Fetch quarterly BoP snapshots (CAD, Capital Account, Services surplus)."""
    db.initialise_schema()
    return load_bop_from_cache(lookback_quarters)


async def fetch_imf_bop(lookback_quarters: int = 8) -> list[BoPRecord]:
    """Fetch live quarterly BoP from IMF SDMX MCP server, falling back to cache."""
    db.initialise_schema()
    try:
        live_records = await imf_client.get_india_bop_quarterly(lookback_quarters)
        if live_records:
            return live_records
    except Exception as exc:
        logger.warning("Live IMF BoP fetch failed: %s. Falling back to cache.", exc)
    return load_bop_from_cache(lookback_quarters)




# ── Pillar 3: Forex Reserves & External Liquidity ─────────────────────────

async def fetch_forex_reserves(lookback_weeks: int = 52) -> list[ForexReservesRecord]:
    """Fetch weekly foreign exchange reserves from RBI DBIE."""
    db.initialise_schema()
    try:
        raw_items = await fetch_raw_forex()
        records = parse_forex_reserves(raw_items, lookback_weeks)
        if not records:
            raise ValueError("Parsed forex reserves returned 0 records.")

        now = datetime.now(timezone.utc).isoformat()
        db_rows = [
            {
                "period": r.period,
                "total_reserves_usd_mn": r.total_reserves_usd_mn,
                "foreign_currency_assets_usd_mn": r.foreign_currency_assets_usd_mn,
                "gold_reserves_usd_mn": r.gold_reserves_usd_mn,
                "sdrs_usd_mn": r.sdrs_usd_mn,
                "reserve_tranche_position_usd_mn": r.reserve_tranche_position_usd_mn,
                "import_cover_months": r.import_cover_months,
                "citation": r.citation.model_dump_json(),
                "fetched_at": now,
            }
            for r in records
        ]
        written = db.upsert_rows("forex_reserves", db_rows)
        db.log_fetch("get_forex_reserves", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live forex fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_forex_reserves", "cache_fallback", error_msg=str(exc))
        return load_forex_from_cache(lookback_weeks)


# ── Pillar 4: Exchange Rates & External Competitiveness ───────────────────

async def fetch_exchange_rates(lookback_days: int = 90) -> list[ExchangeRateRecord]:
    """Fetch USD/INR and reference rates from RBI DBIE."""
    db.initialise_schema()
    try:
        raw_items = await fetch_raw_exchange_rates(limit=lookback_days)
        records = parse_exchange_rates(raw_items, lookback_days)
        if not records:
            raise ValueError("Parsed exchange rates returned 0 records.")

        now = datetime.now(timezone.utc).isoformat()
        rows_to_write = [
            {
                "period": record.period,
                "usd_inr_rate": record.usd_inr_rate,
                "reer_40_basket": record.reer_40_basket,
                "neer_40_basket": record.neer_40_basket,
                "citation": record.citation.model_dump_json(),
                "fetched_at": now,
            }
            for record in records
        ]
        written = db.upsert_rows("exchange_rates", rows_to_write)
        db.log_fetch("get_exchange_rate_snapshot", "live", rows_written=written)
        return records
    except Exception as exc:
        logger.warning("Live exchange-rate fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_exchange_rate_snapshot", "cache_fallback", error_msg=str(exc))
        return load_exchange_rates_from_cache(lookback_days)


fetch_exchange_rate_snapshot = fetch_exchange_rates


# ── Pillar 5: Remittances & Cross-Border Invisibles ───────────────────────

async def fetch_remittances_and_invisibles(lookback_years: int = 5) -> list[RemittancesRecord]:
    """Fetch private remittances and services invisibles from MoSPI eSankhyiki / RBI."""
    db.initialise_schema()
    try:
        raw_items = await fetch_mospi_rbi_dataset(
            indicator_code=9,
            filters={"year": "2024-25", "limit": "50"},
        )
        records = parse_mospi_invisibles(raw_items)
        if not records:
            raise ValueError("MoSPI returned empty invisibles data.")

        now_iso = datetime.now(timezone.utc).isoformat()
        db_rows = [
            {
                "period": r.period,
                "private_transfers_net_usd_mn": r.private_transfers_net_usd_mn,
                "receipts_usd_mn": r.receipts_usd_mn,
                "payments_usd_mn": r.payments_usd_mn,
                "services_receipts_usd_mn": r.services_receipts_usd_mn,
                "services_net_usd_mn": r.services_net_usd_mn,
                "citation": r.citation.model_dump_json(),
                "fetched_at": now_iso,
            }
            for r in records
        ]
        written = db.upsert_rows("remittances_invisibles", db_rows)
        db.log_fetch("get_remittances_and_invisibles", "live", rows_written=written)
        return records[:lookback_years]
    except Exception as exc:
        logger.warning("Live remittances fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_remittances_and_invisibles", "cache_fallback", error_msg=str(exc))
        return load_remittances_from_cache(lookback_years)


# ── Pillar 6: External Flows & External Debt ──────────────────────────────

async def fetch_external_flows(lookback_months: int = 12) -> list[ExternalFlowsRecord]:
    """Fetch foreign direct & portfolio investment flows from database."""
    db.initialise_schema()
    rows = db.query_latest_rows("external_flows", lookback_months)
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}), "duckdb_cache_flows")
        records.append(
            ExternalFlowsRecord(
                period=row["period"],
                net_fdi_usd_mn=row.get("net_fdi_usd_mn"),
                net_fpi_usd_mn=row.get("net_fpi_usd_mn"),
                ecb_usd_mn=row.get("ecb_usd_mn"),
                nri_deposits_usd_mn=row.get("nri_deposits_usd_mn"),
                citation=citation,
            )
        )
    return records


async def fetch_external_debt(lookback_quarters: int = 8) -> list[ExternalDebtRecord]:
    """Fetch external debt stock and vulnerability metrics from MoSPI eSankhyiki."""
    db.initialise_schema()
    try:
        raw_items = await fetch_mospi_rbi_dataset(
            indicator_code=27,
            filters={"limit": "40"},
        )
        records = parse_mospi_external_debt(raw_items, lookback_quarters)
        if not records:
            raise ValueError("MoSPI returned empty external debt data.")

        now_iso = datetime.now(timezone.utc).isoformat()
        db_rows = [
            {
                "period": r.period,
                "total_debt_usd_bn": r.total_debt_usd_bn,
                "total_debt_inr_cr": r.total_debt_inr_cr,
                "general_government_usd_bn": r.general_government_usd_bn,
                "short_term_debt_usd_bn": r.short_term_debt_usd_bn,
                "short_term_to_reserves_pct": r.short_term_to_reserves_pct,
                "debt_to_gdp_pct": r.debt_to_gdp_pct,
                "citation": r.citation.model_dump_json(),
                "fetched_at": now_iso,
            }
            for r in records
        ]
        written = db.upsert_rows("external_debt", db_rows)
        db.log_fetch("get_external_debt", "live", rows_written=written)
        return records[:lookback_quarters]
    except Exception as exc:
        logger.warning("Live external debt fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_external_debt", "cache_fallback", error_msg=str(exc))
        return load_external_debt_from_cache(lookback_quarters)


# ── Live Spot FX & Real-time Web Intelligence ─────────────────────────────

async def fetch_live_market_rates() -> LiveMarketRatesRecord:
    """Fetch live spot FX rates and Brent crude oil benchmark."""
    return await get_live_rates()


async def fetch_realtime_intelligence(
    query: str = "India foreign exchange reserves, trade deficit and rupee latest",
    max_results: int = 4,
) -> RealtimeIntelligenceRecord:
    """Fetch live macroeconomic web intelligence via Tavily search."""
    return await get_realtime_news(query=query, max_results=max_results)


# ── Unified Facade Class ──────────────────────────────────────────────────

class ExternalSectorClient:
    """Consolidated facade client for external sector operations."""

    def __init__(self, database: Any = None) -> None:
        self.db = database or db

    async def get_trade_balance(self, lookback_months: int = 24) -> list[TradeBalanceRecord]:
        return await fetch_trade_balance(lookback_months)

    async def get_balance_of_payments(self, lookback_quarters: int = 8) -> list[BoPRecord]:
        return await fetch_balance_of_payments(lookback_quarters)

    async def get_forex_reserves(self, lookback_weeks: int = 52) -> list[ForexReservesRecord]:
        return await fetch_forex_reserves(lookback_weeks)

    async def get_exchange_rates(self, lookback_days: int = 90) -> list[ExchangeRateRecord]:
        return await fetch_exchange_rates(lookback_days)

    async def get_exchange_rate_snapshot(self, lookback_months: int = 12) -> list[ExchangeRateRecord]:
        return await fetch_exchange_rates(lookback_days=lookback_months * 30)

    async def get_remittances_and_invisibles(self, lookback_years: int = 5) -> list[RemittancesRecord]:
        return await fetch_remittances_and_invisibles(lookback_years)

    async def get_external_flows(self, lookback_months: int = 12) -> list[ExternalFlowsRecord]:
        return await fetch_external_flows(lookback_months)

    async def get_external_debt(self, lookback_quarters: int = 8) -> list[ExternalDebtRecord]:
        return await fetch_external_debt(lookback_quarters)

    async def get_live_market_rates(self) -> LiveMarketRatesRecord:
        return await fetch_live_market_rates()

    async def get_realtime_intelligence(self, query: str = "India foreign exchange reserves, trade deficit and rupee latest", max_results: int = 4) -> RealtimeIntelligenceRecord:
        return await fetch_realtime_intelligence(query=query, max_results=max_results)

    async def get_imf_external_outlook(self, start_year: str = "2022", end_year: str = "2027") -> list[IMFExternalOutlookRecord]:
        return await fetch_imf_external_outlook(start_year, end_year)

    async def get_imf_bop(self, lookback_quarters: int = 8) -> list[BoPRecord]:
        return await fetch_imf_bop(lookback_quarters)



external_client = ExternalSectorClient()
