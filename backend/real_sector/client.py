"""Async Client for the Real Sector & Industrial Output.

Retrieves real sector data directly from official MCP servers:
  1. MoSPI FastMCP Server (https://mcp.mospi.gov.in/) -> IIP Sectoral & Use-Based
  2. DBIE FastMCP Server (@reserve-bank-innovation-hub/dbie-mcp) -> Manufacturing GVA & Core Industries
  3. MCP India Stack (mcp-india-stack) -> Infrastructure/Industrial listed stock bellwethers
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

from fastmcp import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from real_sector.config import real_settings
from real_sector.models import (
    Citation,
    CompanyMarketRecord,
    CoreIndustriesRecord,
    DataFreshness,
    IIPSectoralRecord,
    IIPUseBasedRecord,
    ManufacturingGVARecord,
    MarketContextRecord,
    RealSectorJoinedRecord,
)
from real_sector.parsers import evaluate_industrial_trends, make_citation, safe_float_val

logger = logging.getLogger(__name__)


class RealSectorDataUnavailableError(Exception):
    """Raised when data cannot be retrieved from any authorized MCP server."""


_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

_CACHE: dict[str, tuple[float, Any]] = {}


def _get_cached(key: str) -> Any | None:
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.monotonic() - ts < real_settings.CACHE_TTL_SECONDS:
            return val
    return None


def _set_cached(key: str, val: Any) -> None:
    _CACHE[key] = (time.monotonic(), val)


def _parse_mospi_period(year: Any, month: Any) -> str:
    m_str = str(month).strip().lower()
    m_num = _MONTH_MAP.get(m_str)
    if m_num:
        return f"{year}-{m_num:02d}"
    return f"{year}-{month}"


# ---------------------------------------------------------------------------
# MCP Protocol Invocation Helpers
# ---------------------------------------------------------------------------

async def _call_mospi_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with Client(real_settings.MOSPI_MCP_URL, timeout=real_settings.MCP_TIMEOUT) as client:
        res = await client.call_tool(tool_name, arguments)
        if res.is_error:
            raise RuntimeError(f"MoSPI MCP tool {tool_name} returned error: {res.content}")
        text = res.content[0].text if res.content and hasattr(res.content[0], "text") else ""
        return json.loads(text) if text else {}


async def _call_dbie_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cfg = {
        "mcpServers": {
            "dbie": {
                "command": real_settings.DBIE_MCP_COMMAND,
                "args": real_settings.DBIE_MCP_ARGS,
            }
        }
    }
    async with Client(cfg, timeout=real_settings.MCP_TIMEOUT) as client:
        res = await client.call_tool(tool_name, arguments)
        if res.is_error:
            raise RuntimeError(f"DBIE MCP tool {tool_name} returned error: {res.content}")
        text = res.content[0].text if res.content and hasattr(res.content[0], "text") else ""
        return json.loads(text) if text else {}


async def _call_india_stack_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cfg = {
        "mcpServers": {
            "india_stack": {
                "command": real_settings.INDIA_STACK_COMMAND,
                "args": real_settings.INDIA_STACK_ARGS,
            }
        }
    }
    async with Client(cfg, timeout=real_settings.MCP_TIMEOUT) as client:
        res = await client.call_tool(tool_name, arguments)
        if res.is_error:
            raise RuntimeError(f"India Stack MCP tool {tool_name} returned error: {res.content}")
        text = res.content[0].text if res.content and hasattr(res.content[0], "text") else ""
        return json.loads(text) if text else {}


# ---------------------------------------------------------------------------
# 1. MoSPI IIP Sectoral Breakdown
# ---------------------------------------------------------------------------

async def fetch_iip_sectoral(lookback_months: int = 12) -> list[IIPSectoralRecord]:
    """Fetch MoSPI IIP Sectoral breakdown live from MoSPI MCP server."""
    cached = _get_cached("iip_sectoral")
    if cached is not None:
        return cached[-lookback_months:] if len(cached) > lookback_months else cached

    try:
        payload_sec = await _call_mospi_mcp(
            "get_data",
            {
                "dataset": "IIP",
                "filters": {
                    "base_year": "2011-12",
                    "frequency": "Monthly",
                    "financial_year": "2024-25",
                    "type": "Sectoral",
                    "limit": 100,
                },
            },
        )
        payload_gen = await _call_mospi_mcp(
            "get_data",
            {
                "dataset": "IIP",
                "filters": {
                    "base_year": "2011-12",
                    "frequency": "Monthly",
                    "financial_year": "2024-25",
                    "type": "General",
                    "limit": 100,
                },
            },
        )
        sec_rows = payload_sec.get("data", [])
        gen_rows = payload_gen.get("data", [])

        grouped: dict[str, dict[str, Any]] = {}
        for r in gen_rows:
            p = _parse_mospi_period(r.get("year"), r.get("month"))
            grouped.setdefault(p, {})["general_iip"] = safe_float_val(r.get("index"))
            grouped[p]["general_iip_yoy_pct"] = safe_float_val(r.get("growth_rate"))

        for r in sec_rows:
            p = _parse_mospi_period(r.get("year"), r.get("month"))
            cat = str(r.get("category", "")).strip().lower()
            sub = str(r.get("sub_category", "")).strip()
            if sub:
                continue
            if cat == "mining":
                grouped.setdefault(p, {})["mining_iip"] = safe_float_val(r.get("index"))
                grouped[p]["mining_yoy_pct"] = safe_float_val(r.get("growth_rate"))
            elif cat == "manufacturing":
                grouped.setdefault(p, {})["manufacturing_iip"] = safe_float_val(r.get("index"))
                grouped[p]["manufacturing_yoy_pct"] = safe_float_val(r.get("growth_rate"))
            elif cat == "electricity":
                grouped.setdefault(p, {})["electricity_iip"] = safe_float_val(r.get("index"))
                grouped[p]["electricity_yoy_pct"] = safe_float_val(r.get("growth_rate"))

        records: list[IIPSectoralRecord] = []
        for period in sorted(grouped.keys()):
            data = grouped[period]
            cit = make_citation(
                authority="Ministry of Statistics and Programme Implementation (MoSPI)",
                document_title="Index of Industrial Production (IIP) Sectoral Breakdown",
                table_reference="MoSPI eSankhyiki IIP (Monthly, Base 2011-12)",
                retrieval_url="https://mcp.mospi.gov.in/",
                observation_period=period,
                freshness=DataFreshness.LIVE,
                dataset="iip_sectoral",
                frequency="Monthly",
                unit="%",
                as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            records.append(
                IIPSectoralRecord(
                    period=period,
                    general_iip=data.get("general_iip"),
                    general_iip_yoy_pct=data.get("general_iip_yoy_pct"),
                    mining_iip=data.get("mining_iip"),
                    mining_yoy_pct=data.get("mining_yoy_pct"),
                    manufacturing_iip=data.get("manufacturing_iip"),
                    manufacturing_yoy_pct=data.get("manufacturing_yoy_pct"),
                    electricity_iip=data.get("electricity_iip"),
                    electricity_yoy_pct=data.get("electricity_yoy_pct"),
                    citation=cit,
                )
            )

        if not records:
            raise RealSectorDataUnavailableError("No IIP Sectoral records returned from MoSPI MCP.")

        _set_cached("iip_sectoral", records)
        return records[-lookback_months:] if len(records) > lookback_months else records

    except Exception as exc:
        logger.warning("Live MoSPI IIP Sectoral fetch failed: %s", exc)
        old = _CACHE.get("iip_sectoral")
        if old:
            return old[1][-lookback_months:] if len(old[1]) > lookback_months else old[1]
        raise RealSectorDataUnavailableError(f"IIP Sectoral data unavailable from MoSPI MCP: {exc}") from exc


# ---------------------------------------------------------------------------
# 2. MoSPI IIP Use-Based Classification
# ---------------------------------------------------------------------------

async def fetch_iip_use_based(lookback_months: int = 12) -> list[IIPUseBasedRecord]:
    """Fetch MoSPI IIP Use-Based breakdown live from MoSPI MCP server."""
    cached = _get_cached("iip_use_based")
    if cached is not None:
        return cached[-lookback_months:] if len(cached) > lookback_months else cached

    try:
        payload = await _call_mospi_mcp(
            "get_data",
            {
                "dataset": "IIP",
                "filters": {
                    "base_year": "2011-12",
                    "frequency": "Monthly",
                    "financial_year": "2024-25",
                    "type": "Use-based category",
                    "limit": 100,
                },
            },
        )
        rows = payload.get("data", [])
        grouped: dict[str, dict[str, Any]] = {}
        for r in rows:
            p = _parse_mospi_period(r.get("year"), r.get("month"))
            cat = str(r.get("category", "")).strip().lower()
            gr = safe_float_val(r.get("growth_rate"))
            if "primary" in cat:
                grouped.setdefault(p, {})["primary"] = gr
            elif "capital" in cat:
                grouped.setdefault(p, {})["capital"] = gr
            elif "intermediate" in cat:
                grouped.setdefault(p, {})["intermediate"] = gr
            elif "infra" in cat or "construction" in cat:
                grouped.setdefault(p, {})["infra"] = gr
            elif "consumer durables" in cat:
                grouped.setdefault(p, {})["durables"] = gr
            elif "consumer non" in cat:
                grouped.setdefault(p, {})["non_durables"] = gr

        records: list[IIPUseBasedRecord] = []
        for period in sorted(grouped.keys()):
            data = grouped[period]
            cit = make_citation(
                authority="Ministry of Statistics and Programme Implementation (MoSPI)",
                document_title="Index of Industrial Production (IIP) Use-Based Classification",
                table_reference="MoSPI eSankhyiki IIP Use-Based (Monthly, Base 2011-12)",
                retrieval_url="https://mcp.mospi.gov.in/",
                observation_period=period,
                freshness=DataFreshness.LIVE,
                dataset="iip_use_based",
                frequency="Monthly",
                unit="%",
                as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            records.append(
                IIPUseBasedRecord(
                    period=period,
                    primary_goods_yoy_pct=data.get("primary"),
                    capital_goods_yoy_pct=data.get("capital"),
                    intermediate_goods_yoy_pct=data.get("intermediate"),
                    infrastructure_goods_yoy_pct=data.get("infra"),
                    consumer_durables_yoy_pct=data.get("durables"),
                    consumer_non_durables_yoy_pct=data.get("non_durables"),
                    citation=cit,
                )
            )

        if not records:
            raise RealSectorDataUnavailableError("No IIP Use-Based records returned from MoSPI MCP.")

        _set_cached("iip_use_based", records)
        return records[-lookback_months:] if len(records) > lookback_months else records

    except Exception as exc:
        logger.warning("Live MoSPI IIP Use-Based fetch failed: %s", exc)
        old = _CACHE.get("iip_use_based")
        if old:
            return old[1][-lookback_months:] if len(old[1]) > lookback_months else old[1]
        raise RealSectorDataUnavailableError(f"IIP Use-Based data unavailable from MoSPI MCP: {exc}") from exc


# ---------------------------------------------------------------------------
# 3. Eight Core Industries (ICI)
# ---------------------------------------------------------------------------

async def fetch_core_industries(lookback_months: int = 12) -> list[CoreIndustriesRecord]:
    """Fetch DPIIT Eight Core Industries series live from DBIE MCP server."""
    cached = _get_cached("core_industries")
    if cached is not None:
        return cached[-lookback_months:] if len(cached) > lookback_months else cached

    try:
        payload = await _call_dbie_mcp(
            "get_table",
            {
                "table": "/tables/index-numbers-of-core-infrastructure-industries-growth-rates",
                "max_array_items": 200,
            },
        )
        data = payload.get("data") or payload.get("payload") or {}
        dates = data.get("dates", [])
        values = data.get("values", [])
        columns = data.get("columns", [])
        cols = {c.get("key"): i for i, c in enumerate(columns)}

        def _val(col_key: str, d_idx: int) -> float | None:
            idx = cols.get(col_key)
            if idx is not None and idx < len(values) and d_idx < len(values[idx]):
                return safe_float_val(values[idx][d_idx])
            return None

        records: list[CoreIndustriesRecord] = []
        for d_idx, d_str in enumerate(dates):
            ici = _val("BY_2011_12|40.27|INF_COMP_INDX", d_idx)
            steel = _val("BY_2011_12|7.22|INF_STL", d_idx)
            cement = _val("BY_2011_12|2.16|INF_CEMENT", d_idx)
            coal = _val("BY_2011_12|4.16|INF_COAL", d_idx)
            electy = _val("BY_2011_12|7.99|INF_ELECTY", d_idx)
            oil = _val("BY_2011_12|3.62|INF_CRD_OIL", d_idx)
            gas = _val("BY_2011_12|2.77|INF_NAT_GAS", d_idx)
            refinery = _val("BY_2011_12|11.29|INF_REF_PRD", d_idx)
            fertilizer = _val("BY_2011_12|1.06|INF_FRTZ", d_idx)

            if ici is None and steel is None and cement is None:
                continue

            period = str(d_str)[:7]
            cit = make_citation(
                authority="DPIIT / Reserve Bank of India (RBI)",
                document_title="Index Numbers of Core/Infrastructure Industries - Growth Rates",
                table_reference="DBIE /tables/index-numbers-of-core-infrastructure-industries-growth-rates",
                retrieval_url="https://dbie.rbihub.in/tables/index-numbers-of-core-infrastructure-industries-growth-rates",
                observation_period=period,
                freshness=DataFreshness.LIVE,
                dataset="core_industries",
                frequency="Annual / Financial Year",
                unit="%",
                as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            records.append(
                CoreIndustriesRecord(
                    period=period,
                    overall_ici_yoy_pct=ici,
                    coal_yoy_pct=coal,
                    crude_oil_yoy_pct=oil,
                    natural_gas_yoy_pct=gas,
                    refinery_products_yoy_pct=refinery,
                    fertilizers_yoy_pct=fertilizer,
                    steel_yoy_pct=steel,
                    cement_yoy_pct=cement,
                    electricity_yoy_pct=electy,
                    citation=cit,
                )
            )

        if not records:
            raise RealSectorDataUnavailableError("No Core Industries records found in DBIE table.")

        _set_cached("core_industries", records)
        return records[-lookback_months:] if len(records) > lookback_months else records

    except Exception as exc:
        logger.warning("Live DBIE Core Industries fetch failed: %s", exc)
        old = _CACHE.get("core_industries")
        if old:
            return old[1][-lookback_months:] if len(old[1]) > lookback_months else old[1]
        raise RealSectorDataUnavailableError(f"Core Industries data unavailable from DBIE MCP: {exc}") from exc


# ---------------------------------------------------------------------------
# 4. RBI DBIE Manufacturing GVA
# ---------------------------------------------------------------------------

async def fetch_manufacturing_gva(lookback_quarters: int = 8) -> list[ManufacturingGVARecord]:
    """Fetch Quarterly Manufacturing GVA series live from DBIE MCP server."""
    cached = _get_cached("manufacturing_gva")
    if cached is not None:
        return cached[-lookback_quarters:] if len(cached) > lookback_quarters else cached

    try:
        payload = await _call_dbie_mcp(
            "get_table",
            {
                "table": "/tables/quarterly-gross-domestic-product-at-factor-cost-gross-value-added-at-basic-price",
                "max_array_items": 200,
            },
        )
        data = payload.get("data") or payload.get("payload") or {}
        dates = data.get("dates", [])
        values = data.get("values", [])
        columns = data.get("columns", [])
        cols = {c.get("key"): i for i, c in enumerate(columns)}

        col_mfg_c = cols.get("BY_2011_12|CECN_MANFRNG|FACT_CST|CNST_PRC")
        col_mfg_n = cols.get("BY_2011_12|CECN_MANFRNG|FACT_CST|CURR_PRC")
        col_ttl_c = cols.get("BY_2011_12|CECN_TTL_GRS_VAL_ADD_BAS_PRC|FACT_CST|CNST_PRC")

        if col_mfg_c is None or col_mfg_n is None or col_ttl_c is None:
            raise RealSectorDataUnavailableError("Required GVA column keys missing from DBIE table.")

        records: list[ManufacturingGVARecord] = []
        for d_idx, d_str in enumerate(dates):
            v_c = safe_float_val(values[col_mfg_c][d_idx]) if col_mfg_c < len(values) and d_idx < len(values[col_mfg_c]) else None
            v_n = safe_float_val(values[col_mfg_n][d_idx]) if col_mfg_n < len(values) and d_idx < len(values[col_mfg_n]) else None
            v_t = safe_float_val(values[col_ttl_c][d_idx]) if col_ttl_c < len(values) and d_idx < len(values[col_ttl_c]) else None

            if v_c is None and v_n is None:
                continue

            v_c_prev = safe_float_val(values[col_mfg_c][d_idx - 4]) if d_idx >= 4 and col_mfg_c < len(values) and (d_idx - 4) < len(values[col_mfg_c]) else None
            yoy = ((v_c - v_c_prev) / v_c_prev * 100.0) if v_c and v_c_prev else None
            share = (v_c / v_t * 100.0) if v_c and v_t else None
            cr = round(v_n / 1e7, 1) if v_n else None

            period = str(d_str)[:10]
            cit = make_citation(
                authority="National Statistical Office (NSO) / Reserve Bank of India (RBI)",
                document_title="Quarterly Gross Value Added at Basic Price by Economic Activity",
                table_reference="DBIE /tables/quarterly-gross-domestic-product-at-factor-cost-gross-value-added-at-basic-price",
                retrieval_url="https://dbie.rbihub.in/tables/quarterly-gross-domestic-product-at-factor-cost-gross-value-added-at-basic-price",
                observation_period=period,
                freshness=DataFreshness.LIVE,
                dataset="manufacturing_gva",
                frequency="Quarterly",
                unit="%",
                as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            records.append(
                ManufacturingGVARecord(
                    period=period,
                    manufacturing_gva_real_yoy_pct=yoy,
                    manufacturing_gva_cr=cr,
                    manufacturing_share_in_gva_pct=share,
                    citation=cit,
                )
            )

        if not records:
            raise RealSectorDataUnavailableError("No Manufacturing GVA records found in DBIE table.")

        _set_cached("manufacturing_gva", records)
        return records[-lookback_quarters:] if len(records) > lookback_quarters else records

    except Exception as exc:
        logger.warning("Live DBIE Manufacturing GVA fetch failed: %s", exc)
        old = _CACHE.get("manufacturing_gva")
        if old:
            return old[1][-lookback_quarters:] if len(old[1]) > lookback_quarters else old[1]
        raise RealSectorDataUnavailableError(f"Manufacturing GVA data unavailable from DBIE MCP: {exc}") from exc



# ---------------------------------------------------------------------------
# 6. Infrastructure & Industrial Market Bellwethers
# ---------------------------------------------------------------------------

async def fetch_infrastructure_market_context() -> list[MarketContextRecord]:
    """Fetch listed equity context live via MCP India Stack."""
    cached = _get_cached("market_context")
    if cached is not None:
        return cached

    symbols = [
        ("TATASTEEL.NS", "Tata Steel Ltd", "Steel"),
        ("JSWSTEEL.NS", "JSW Steel Ltd", "Steel"),
        ("ULTRACEMCO.NS", "UltraTech Cement Ltd", "Cement"),
        ("LT.NS", "Larsen & Toubro Ltd", "Capital Goods & Infrastructure"),
        ("BHEL.NS", "Bharat Heavy Electricals Ltd", "Capital Goods"),
    ]

    async def _fetch_quote(sym: str, name: str, cat: str) -> CompanyMarketRecord | None:
        try:
            payload = await _call_india_stack_mcp("get_stock_quote", {"symbol": sym})
            data = payload.get("data", {})
            price = safe_float_val(data.get("currentPrice"))
            prev = safe_float_val(data.get("previousClose"))
            chg = round(((price - prev) / prev * 100), 2) if price and prev else None
            return CompanyMarketRecord(
                symbol=sym,
                company_name=name,
                sector_category=cat,
                current_price=price,
                change_pct_1m=chg,
                change_pct_1y=None,
                pe_ratio=safe_float_val(data.get("trailingPE")),
            )
        except Exception as exc:
            logger.warning("Quote failed for %s: %s", sym, exc)
            return None

    results = await asyncio.gather(*(_fetch_quote(s, n, c) for s, n, c in symbols))
    companies = [c for c in results if c is not None]

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cit = make_citation(
        authority="National Stock Exchange of India (NSE) via MCP India Stack",
        document_title="Infrastructure & Industrial Listed Equity Bellwethers",
        table_reference="mcp_india_stack:get_stock_quote",
        retrieval_url="https://www.nseindia.com",
        observation_period=today_str,
        freshness=DataFreshness.LIVE,
        dataset="market_context",
        frequency="Daily / Live",
        unit="INR",
        as_of=today_str,
    )

    records = [
        MarketContextRecord(
            period=today_str,
            nifty_infra_change_pct=None,
            nifty_metal_change_pct=None,
            bellwether_companies=companies,
            citation=cit,
        )
    ]
    _set_cached("market_context", records)
    return records


# ---------------------------------------------------------------------------
# 7. Joined Real Sector Indicator Composite View
# ---------------------------------------------------------------------------

async def fetch_joined_real_indicators() -> list[RealSectorJoinedRecord]:
    """Join live real sector indicators in memory across MoSPI and DBIE MCP servers."""
    results = await asyncio.gather(
        fetch_iip_sectoral(lookback_months=6),
        fetch_iip_use_based(lookback_months=6),
        fetch_core_industries(lookback_months=6),
        fetch_manufacturing_gva(lookback_quarters=4),
        return_exceptions=True,
    )
    iip_sec = results[0] if not isinstance(results[0], Exception) and results[0] else []
    iip_use = results[1] if not isinstance(results[1], Exception) and results[1] else []
    core = results[2] if not isinstance(results[2], Exception) and results[2] else []
    gva = results[3] if not isinstance(results[3], Exception) and results[3] else []

    periods: set[str] = set()
    sec_map = {r.period: r for r in iip_sec}
    use_map = {r.period: r for r in iip_use}
    core_map = {r.period: r for r in core}
    periods.update(sec_map.keys())
    periods.update(use_map.keys())
    periods.update(core_map.keys())

    latest_gva = gva[-1] if gva else None

    joined: list[RealSectorJoinedRecord] = []
    for p in sorted(periods):
        s_rec = sec_map.get(p)
        u_rec = use_map.get(p)
        c_rec = core_map.get(p)

        mfg_yoy = s_rec.manufacturing_yoy_pct if s_rec else None
        cap_yoy = u_rec.capital_goods_yoy_pct if u_rec else None
        steel_yoy = c_rec.steel_yoy_pct if c_rec else None
        cement_yoy = c_rec.cement_yoy_pct if c_rec else None

        trends = evaluate_industrial_trends(
            mfg_yoy, cap_yoy, steel_yoy, cement_yoy
        )
        trend_summary = f"Mfg: {trends['Manufacturing IIP']}, CapGoods: {trends['Capital Goods IIP']}, Steel: {trends['Core Steel']}"

        cit = (
            s_rec.citation if s_rec else (
                u_rec.citation if u_rec else (
                    c_rec.citation if c_rec else make_citation(
                        authority="MoSPI / RBI",
                        document_title="Composite Real Sector Indicator Join",
                        table_reference="multi_mcp_composite",
                        retrieval_url="https://mcp.mospi.gov.in/",
                        observation_period=p,
                        freshness=DataFreshness.LIVE,
                    )
                )
            )
        )

        joined.append(
            RealSectorJoinedRecord(
                period=p,
                manufacturing_iip_yoy_pct=mfg_yoy,
                capital_goods_iip_yoy_pct=cap_yoy,
                intermediate_goods_yoy_pct=u_rec.intermediate_goods_yoy_pct if u_rec else None,
                consumer_durables_yoy_pct=u_rec.consumer_durables_yoy_pct if u_rec else None,
                core_steel_yoy_pct=steel_yoy,
                core_cement_yoy_pct=cement_yoy,
                core_electricity_yoy_pct=c_rec.electricity_yoy_pct if c_rec else None,
                core_coal_yoy_pct=c_rec.coal_yoy_pct if c_rec else None,
                overall_ici_yoy_pct=c_rec.overall_ici_yoy_pct if c_rec else None,
                manufacturing_gva_yoy_pct=latest_gva.manufacturing_gva_real_yoy_pct if latest_gva else None,
                trend_summary=trend_summary,
                citation=cit,
            )
        )

    return joined[-12:] if len(joined) > 12 else joined
