"""Async HTTP client and data manager for Capital Markets Sector.

Covers all 10 core domain responsibilities:
1. Equity Market Performance (NIFTY Snapshot & History)
2. Market Volatility & Sentiment (India VIX)
3. Market Liquidity & Breadth (NSE Breadth)
4. G-Sec Yield Curve (RBI DBIE SGL yields)
5. Mutual Fund Flows (AMFI data)
6. Foreign Portfolio Investment (NSDL / SEBI FPI flows)
7. Corporate Earnings & Valuation (NSE P/E, EPS, PAT growth)
8. Sectoral Market Performance (NSE Sectoral Indices)
9. Primary Capital Markets (IPOs & Equity Issuances)
10. Market Structure & Investor Participation (Demat accounts & Retail share)
11. Market-Economy Linkages (Equity Risk Premium & Buffett Indicator)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from capital_market_sector import database as db
from capital_market_sector.config import capital_settings
from capital_market_sector.data_sources.amfi_data import get_latest_amfi_flows
from capital_market_sector.data_sources.institutional_data import (
    compute_market_economy_linkages,
    fetch_corporate_earnings_data,
    fetch_fpi_flows_data,
    fetch_investor_participation_data,
    fetch_primary_market_ipos_data,
)
from capital_market_sector.data_sources.yahoo_data import (
    fetch_sectoral_indices,
    parse_market_chart,
)
from capital_market_sector.mcp_client import call_nse_tool
from capital_market_sector.models import (
    Citation,
    CorporateEarningsRecord,
    DataFreshness,
    FpiFlowsRecord,
    GSecYieldRecord,
    IndiaVixRecord,
    InvestorParticipationRecord,
    MarketBreadthRecord,
    MarketEconomyLinkageRecord,
    MarketHistoryRecord,
    MutualFundFlowsRecord,
    NiftySnapshotRecord,
    PrimaryMarketRecord,
    SectoralPerformanceRecord,
)
from capital_market_sector.parsers import parse_gsec_yields, parse_market_breadth

logger = logging.getLogger(__name__)

_MARKET_CACHE_TTL_SECONDS = 300
_SLOW_MARKET_CACHE_TTL_SECONDS = 21_600
_GSEC_YIELD_TABLE = "financial_markets/r217_month_end_yield_of_sgl_transactions_in_government_dated_se"
_GSEC_YIELD_API_URL = f"{capital_settings.RBI_DBIE_API_BASE.rstrip('/')}/{_GSEC_YIELD_TABLE}/rows"

_parse_market_chart = parse_market_chart


class CapitalMarketDataUnavailableError(Exception):
    """Raised when neither live fetch nor cache can supply capital markets data."""


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=capital_settings.HTTP_CONNECT_TIMEOUT, read=capital_settings.HTTP_READ_TIMEOUT),
        headers={"User-Agent": "macrograph-ai/capital-market-sector"},
        follow_redirects=True,
    )


async def _fetch_json(http_client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    response = await http_client.get(url, params=params, timeout=10.0)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _prepare_cached_citation(citation_data: Any) -> Citation:
    if isinstance(citation_data, str):
        citation_data = json.loads(citation_data)
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


def _save_live_records(table: str, records: list[Any], tool_name: str) -> None:
    fetched_at = datetime.now(timezone.utc)
    rows = [
        {
            **record.model_dump(mode="json", exclude={"citation"}),
            "citation": record.citation.model_dump_json(),
            "fetched_at": (fetched_at - timedelta(milliseconds=index)).isoformat(),
        }
        for index, record in enumerate(records)
    ]
    written = db.upsert_rows(table, rows)
    db.log_fetch(tool_name, "upstream_snapshot", rows_written=written)


def _rows_are_recent(rows: list[dict[str, Any]], max_age_seconds: int) -> bool:
    if not rows:
        return False
    fetched_at = rows[0].get("fetched_at")
    if isinstance(fetched_at, str):
        try:
            fetched_at = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(fetched_at, datetime):
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched_at).total_seconds() <= max_age_seconds


def _is_seed_observation(row: dict[str, Any]) -> bool:
    cit = row.get("citation")
    if isinstance(cit, str):
        try:
            cit = json.loads(cit)
        except json.JSONDecodeError:
            return False
    return isinstance(cit, dict) and str(cit.get("freshness")) == "cached"


def _query_non_seed_rows(table: str, limit: int) -> list[dict[str, Any]]:
    return [r for r in db.query_latest_rows(table, limit=limit) if not _is_seed_observation(r)]


async def _fetch_yahoo_chart(
    *,
    symbol: str,
    range_value: str,
    document_title: str,
    table: str,
    tool_name: str,
    is_vix: bool,
) -> list[Any]:
    from capital_market_sector import client as self_mod

    encoded_symbol = quote(symbol, safe="")
    url = f"{capital_settings.YAHOO_FINANCE_CHART_URL.rstrip('/')}/{encoded_symbol}"
    params = {"range": range_value, "interval": "1d"}
    retrieval_url = str(httpx.URL(url, params=params))
    async with _build_client() as http_client:
        payload = await self_mod._fetch_json(http_client, url, params)
    records = self_mod._parse_market_chart(
        payload,
        symbol=symbol,
        document_title=document_title,
        retrieval_url=retrieval_url,
        is_vix=is_vix,
    )
    _save_live_records(table, records, tool_name)
    return records


# ── 1. NIFTY Snapshot ────────────────────────────────────────────────────────

async def fetch_nifty_snapshot() -> list[NiftySnapshotRecord]:
    from capital_market_sector import client as self_mod

    db.initialise_schema()
    recent = _query_non_seed_rows("nifty_snapshot", limit=5)
    if _rows_are_recent(recent, _MARKET_CACHE_TTL_SECONDS):
        return [NiftySnapshotRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        return await self_mod._fetch_yahoo_chart(
            symbol="^NSEI",
            range_value="5d",
            document_title="NIFTY 50 daily chart (Yahoo Finance provider snapshot)",
            table="nifty_snapshot",
            tool_name="yahoo_nifty_chart",
            is_vix=False,
        )
    except Exception as exc:
        logger.warning("NIFTY fetch failed: %s. Loading cache.", exc)
        rows = db.query_latest_rows("nifty_snapshot", limit=5)
        if not rows:
            raise CapitalMarketDataUnavailableError("NIFTY snapshot data unavailable.") from exc
        return [NiftySnapshotRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in rows]


# ── 2. Market History ────────────────────────────────────────────────────────

async def fetch_market_history(lookback_months: int = 12) -> list[MarketHistoryRecord]:
    db.initialise_schema()
    rows = db.query_latest_rows("market_history", lookback_months)
    return [MarketHistoryRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in rows]


# ── 3. India VIX ─────────────────────────────────────────────────────────────

async def fetch_india_vix(lookback_days: int = 30) -> list[IndiaVixRecord]:
    from capital_market_sector import client as self_mod

    db.initialise_schema()
    recent = _query_non_seed_rows("india_vix", limit=lookback_days)
    if _rows_are_recent(recent, _MARKET_CACHE_TTL_SECONDS):
        return [IndiaVixRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    range_val = "1mo" if lookback_days <= 31 else "3mo"
    try:
        return await self_mod._fetch_yahoo_chart(
            symbol="^INDIAVIX",
            range_value=range_val,
            document_title="India VIX daily chart (Yahoo Finance provider snapshot)",
            table="india_vix",
            tool_name="yahoo_india_vix_chart",
            is_vix=True,
        )
    except Exception as exc:
        logger.warning("India VIX fetch failed: %s. Loading cache.", exc)
        rows = db.query_latest_rows("india_vix", limit=lookback_days)
        if not rows:
            raise CapitalMarketDataUnavailableError("India VIX data unavailable.") from exc
        return [IndiaVixRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in rows]


# ── 4. Market Breadth ────────────────────────────────────────────────────────

async def fetch_market_breadth() -> list[MarketBreadthRecord]:
    db.initialise_schema()
    rows = _query_non_seed_rows("market_breadth", limit=5)
    if _rows_are_recent(rows, _MARKET_CACHE_TTL_SECONDS):
        return [MarketBreadthRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in rows]
    as_of = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    try:
        payload = await call_nse_tool(capital_settings.NSE_BHAVCOPY_MCP, "get_market_breadth", {"date": as_of})
        citation = Citation(
            source_authority="National Stock Exchange of India (NSE)",
            document_title="NSE Market Breadth Summary",
            table_reference="NSE Bhavcopy MCP tool: get_market_breadth",
            retrieval_url=capital_settings.NSE_BHAVCOPY_MCP,
            observation_period=str(payload.get("date") or as_of),
            fetched_at=datetime.now(timezone.utc),
            freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        )
        record = parse_market_breadth(payload, citation)
        _save_live_records("market_breadth", [record], "nse_mcp_market_breadth")
        return [record]
    except Exception as exc:
        logger.warning("NSE market breadth fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("market_breadth", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("NSE market breadth data unavailable.") from exc
        return [MarketBreadthRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 5. G-Sec Yields ──────────────────────────────────────────────────────────

async def fetch_gsec_yield_snapshot() -> list[GSecYieldRecord]:
    from capital_market_sector import client as self_mod

    db.initialise_schema()
    rows = _query_non_seed_rows("gsec_yields", limit=24)
    if _rows_are_recent(rows, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [GSecYieldRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in rows]
    try:
        async with _build_client() as http_client:
            payload = await self_mod._fetch_json(http_client, _GSEC_YIELD_API_URL, params={"limit": 2000, "offset": 0})

        def cite_fn(p: str) -> Citation:
            return Citation(
                source_authority="Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
                document_title="Month-end Yield of SGL Transactions in Government Dated Securities for Various Maturities",
                table_reference=f"financial_markets.{_GSEC_YIELD_TABLE.split('/')[-1]}",
                retrieval_url=_GSEC_YIELD_API_URL,
                observation_period=p,
                fetched_at=datetime.now(timezone.utc),
                freshness=DataFreshness.UPSTREAM_SNAPSHOT,
            )

        records = parse_gsec_yields(payload, lookback_months=24, citation_factory=cite_fn)
        if not records:
            raise ValueError("RBI DBIE returned no usable G-Sec yields.")
        _save_live_records("gsec_yields", records, "rbi_dbie_monthly_gsec_yields")
        return records
    except Exception as exc:
        logger.warning("RBI DBIE fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("gsec_yields", limit=24)
        if not cached:
            raise CapitalMarketDataUnavailableError("G-Sec yield data unavailable.") from exc
        return [GSecYieldRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 6. Mutual Fund Flows (AMFI) ──────────────────────────────────────────────

async def fetch_mutual_fund_flows() -> list[MutualFundFlowsRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("mutual_fund_flows", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [MutualFundFlowsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await get_latest_amfi_flows(client_inst)
            _save_live_records("mutual_fund_flows", [record], "amfi_mutual_fund_flows")
            return [record]
    except Exception as exc:
        logger.warning("AMFI flows fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("mutual_fund_flows", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Mutual fund flow data unavailable.") from exc
        return [MutualFundFlowsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 7. FPI Flows ─────────────────────────────────────────────────────────────

async def fetch_fpi_equity_flows() -> list[FpiFlowsRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("fpi_flows", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [FpiFlowsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await fetch_fpi_flows_data(client_inst)
            _save_live_records("fpi_flows", [record], "nsdl_sebi_fpi_flows")
            return [record]
    except Exception as exc:
        logger.warning("FPI flows fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("fpi_flows", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("FPI flow data unavailable.") from exc
        return [FpiFlowsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 8. Corporate Earnings & Valuation ────────────────────────────────────────

async def fetch_corporate_earnings_valuation() -> list[CorporateEarningsRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("corporate_earnings", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [CorporateEarningsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await fetch_corporate_earnings_data(client_inst)
            _save_live_records("corporate_earnings", [record], "nse_corporate_earnings")
            return [record]
    except Exception as exc:
        logger.warning("Corporate earnings fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("corporate_earnings", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Corporate earnings data unavailable.") from exc
        return [CorporateEarningsRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 9. Sectoral Market Performance ───────────────────────────────────────────

async def fetch_sectoral_performance() -> list[SectoralPerformanceRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("sectoral_performance", limit=5)
    if _rows_are_recent(recent, _MARKET_CACHE_TTL_SECONDS):
        return [SectoralPerformanceRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await fetch_sectoral_indices(client_inst)
            _save_live_records("sectoral_performance", [record], "nse_sectoral_performance")
            return [record]
    except Exception as exc:
        logger.warning("Sectoral performance fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("sectoral_performance", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Sectoral performance data unavailable.") from exc
        return [SectoralPerformanceRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 10. Primary Capital Markets (IPOs) ───────────────────────────────────────

async def fetch_primary_market_ipos() -> list[PrimaryMarketRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("primary_market_ipos", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [PrimaryMarketRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await fetch_primary_market_ipos_data(client_inst)
            _save_live_records("primary_market_ipos", [record], "sebi_primary_market_ipos")
            return [record]
    except Exception as exc:
        logger.warning("Primary market IPO fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("primary_market_ipos", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Primary market IPO data unavailable.") from exc
        return [PrimaryMarketRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 11. Investor Participation ───────────────────────────────────────────────

async def fetch_investor_participation() -> list[InvestorParticipationRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("investor_participation", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [InvestorParticipationRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        async with _build_client() as client_inst:
            record = await fetch_investor_participation_data(client_inst)
            _save_live_records("investor_participation", [record], "sebi_investor_participation")
            return [record]
    except Exception as exc:
        logger.warning("Investor participation fetch failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("investor_participation", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Investor participation data unavailable.") from exc
        return [InvestorParticipationRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]


# ── 12. Market-Economy Linkages ──────────────────────────────────────────────

async def fetch_market_economy_linkages() -> list[MarketEconomyLinkageRecord]:
    db.initialise_schema()
    recent = _query_non_seed_rows("market_economy_linkages", limit=5)
    if _rows_are_recent(recent, _SLOW_MARKET_CACHE_TTL_SECONDS):
        return [MarketEconomyLinkageRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in recent]
    try:
        gsec_rows = await fetch_gsec_yield_snapshot()
        gsec_10y = gsec_rows[0].ten_year_gsec_yield_pct if gsec_rows else 6.78
        earn_rows = await fetch_corporate_earnings_valuation()
        pe = earn_rows[0].pe_ratio if earn_rows else 24.75

        record = await compute_market_economy_linkages(ten_year_gsec_yield=gsec_10y, pe_ratio=pe)
        _save_live_records("market_economy_linkages", [record], "capital_market_economy_linkages")
        return [record]
    except Exception as exc:
        logger.warning("Market-economy linkages computation failed: %s. Using cache.", exc)
        cached = db.query_latest_rows("market_economy_linkages", limit=5)
        if not cached:
            raise CapitalMarketDataUnavailableError("Market-economy linkages data unavailable.") from exc
        return [MarketEconomyLinkageRecord(**{**r, "citation": _prepare_cached_citation(r.get("citation"))}) for r in cached]
