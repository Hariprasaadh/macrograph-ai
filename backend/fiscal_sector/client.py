"""Async client for the Fiscal & Public Finance Sector.

Retrieval strategy (multi-source resilient caching):
  1. Sovereign Debt & Balances: Live fetch from IMF SDMX / MCP server; fallback to DuckDB.
  2. National Accounts Product Taxes: Live fetch from MoSPI eSankhyiki FastMCP; fallback to DuckDB.
  3. Union Budget & CGA Accounts: Verified DuckDB store with CGA/Union Budget accounts at a glance.
  4. GST Collections: Verified monthly series with DuckDB fallback.
  5. Tax Policy & Computation: Real-time calculators via eco-policy-mcp (CBIC/CBDT rules).
  6. Real-time Gazette & PIB Releases: Tavily AI search.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fiscal_sector import database as db
from fiscal_sector.cache_loaders import (
    FiscalDataUnavailableError,
    load_fiscal_deficit_from_cache,
    load_gst_collections_from_cache,
    load_mospi_tax_from_cache,
    load_sovereign_debt_from_cache,
)
from fiscal_sector.config import fiscal_settings
from fiscal_sector.models import (
    Citation,
    DataFreshness,
    FiscalDeficitRecord,
    FiscalNewsItem,
    FiscalNewsResponse,
    GSTCollectionRecord,
    GSTINValidationResponse,
    GSTSplitBreakdown,
    GSTSplitResponse,
    IncomeTaxComparisonResponse,
    MoSPITaxAggregateRecord,
    SovereignDebtRecord,
    TaxProvenance,
    TaxRegimeComparison,
)
from fiscal_sector.parsers import (
    parse_imf_weo_observations,
    parse_mospi_nas_tax_records,
)

logger = logging.getLogger(__name__)


def _make_retry():
    return retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            fiscal_settings.DBIE_TIMEOUT,
            connect=fiscal_settings.HTTP_CONNECT_TIMEOUT,
            read=fiscal_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/fiscal-sector"},
        follow_redirects=True,
    )


# ── Pillar 1: Union Accounts & Fiscal Deficit (CGA & Budget) ────────────────

async def fetch_union_fiscal_deficit(lookback_records: int = 5) -> list[FiscalDeficitRecord]:
    """Fetch Union fiscal deficit and budgetary accounts from verified store."""
    try:
        records = load_fiscal_deficit_from_cache(lookback_records)
        db.log_fetch("get_union_fiscal_deficit", "cached_store", rows_written=len(records))
        return records
    except Exception as exc:
        logger.error("Failed to load union fiscal deficit: %s", exc)
        db.log_fetch("get_union_fiscal_deficit", "failed", error_msg=str(exc))
        raise FiscalDataUnavailableError(str(exc)) from exc


# ── Pillar 2: Sovereign Debt & International Balance (IMF MCP) ─────────────

async def fetch_sovereign_debt_imf(
    start_year: int = 2018,
    end_year: int = 2025,
) -> list[SovereignDebtRecord]:
    """Fetch General Government Gross Debt & Net Lending/Borrowing from IMF MCP server."""
    try:
        async with _build_client() as http_client:
            # Query Gross Debt (% of GDP)
            debt_res = await http_client.post(
                fiscal_settings.IMF_MCP_URL,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "imf_query_dataset",
                        "arguments": {
                            "dataflow_id": "WEO",
                            "key": "IND.GGXWDG_NGDP.A",
                            "start_period": str(start_year),
                            "end_period": str(end_year),
                        },
                    },
                },
            )
            debt_text = ""
            for line in debt_res.text.strip().split("\n"):
                if line.startswith("data:"):
                    res_json = json.loads(line[5:].strip())
                    debt_text += res_json.get("result", {}).get("content", [{}])[0].get("text", "")

            # Query Net Lending/Borrowing (% of GDP)
            deficit_res = await http_client.post(
                fiscal_settings.IMF_MCP_URL,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "imf_query_dataset",
                        "arguments": {
                            "dataflow_id": "WEO",
                            "key": "IND.GGXCNL_NGDP.A",
                            "start_period": str(start_year),
                            "end_period": str(end_year),
                        },
                    },
                },
            )
            deficit_text = ""
            for line in deficit_res.text.strip().split("\n"):
                if line.startswith("data:"):
                    res_json = json.loads(line[5:].strip())
                    deficit_text += res_json.get("result", {}).get("content", [{}])[0].get("text", "")

            records = parse_imf_weo_observations(debt_text, deficit_text, freshness=DataFreshness.LIVE)
            if records:
                db_rows = [
                    {
                        "period": r.period,
                        "general_govt_gross_debt_gdp_pct": r.general_govt_gross_debt_gdp_pct,
                        "net_lending_borrowing_gdp_pct": r.net_lending_borrowing_gdp_pct,
                        "revenue_gdp_pct": r.revenue_gdp_pct,
                        "expenditure_gdp_pct": r.expenditure_gdp_pct,
                        "citation": r.citation.model_dump_json(),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                    for r in records
                ]
                written = db.upsert_rows("general_govt_debt", db_rows)
                db.log_fetch("get_general_government_debt", "live", rows_written=written)
                return records

        raise ValueError("IMF MCP returned empty or unparseable observations.")

    except Exception as exc:
        logger.warning("Live IMF debt fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_general_government_debt", "cache_fallback", error_msg=str(exc))
        return load_sovereign_debt_from_cache(end_year - start_year + 1)


# ── Pillar 3: Goods & Services Tax (GST Collections) ─────────────────────────

async def fetch_gst_collections(lookback_months: int = 12) -> list[GSTCollectionRecord]:
    """Fetch monthly GST revenue collections from verified DuckDB store."""
    try:
        records = load_gst_collections_from_cache(lookback_months)
        db.log_fetch("get_gst_collections", "cached_store", rows_written=len(records))
        return records
    except Exception as exc:
        logger.error("Failed to load GST collections: %s", exc)
        db.log_fetch("get_gst_collections", "failed", error_msg=str(exc))
        raise FiscalDataUnavailableError(str(exc)) from exc


# ── Pillar 4: MoSPI Product Taxes & Subsidies (NAS MCP) ──────────────────────

async def fetch_mospi_product_taxes(lookback_years: int = 5) -> list[MoSPITaxAggregateRecord]:
    """Fetch Net Taxes on Products from official MoSPI FastMCP server."""
    try:
        async with _build_client() as http_client:
            filters = {
                "indicator_code": 2,
                "base_year": "2011-12",
                "series": "Current",
                "frequency_code": 1,
                "limit": str(lookback_years * 2),
            }
            res = await http_client.post(
                fiscal_settings.MOSPI_MCP_URL,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "get_data",
                        "arguments": {"dataset": "NAS", "filters": filters},
                    },
                },
            )
            raw_text = ""
            for line in res.text.strip().split("\n"):
                if line.startswith("data:"):
                    res_json = json.loads(line[5:].strip())
                    content = res_json.get("result", {}).get("content", [])
                    if content:
                        raw_text = content[0].get("text", "")

            if raw_text:
                payload = json.loads(raw_text)
                records = parse_mospi_nas_tax_records(payload, freshness=DataFreshness.LIVE)
                if records:
                    db_rows = [
                        {
                            "year": r.year,
                            "indicator": r.indicator,
                            "current_price_cr": r.current_price_cr,
                            "constant_price_cr": r.constant_price_cr,
                            "frequency": r.frequency,
                            "revision": r.revision,
                            "citation": r.citation.model_dump_json(),
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        }
                        for r in records
                    ]
                    written = db.upsert_rows("mospi_tax_aggregates", db_rows)
                    db.log_fetch("get_mospi_product_taxes", "live", rows_written=written)
                    return records[:lookback_years]

        raise ValueError("MoSPI MCP returned empty product tax data.")

    except Exception as exc:
        logger.warning("Live MoSPI product tax fetch failed: %s. Falling back to cache.", exc)
        db.log_fetch("get_mospi_product_taxes", "cache_fallback", error_msg=str(exc))
        return load_mospi_tax_from_cache(lookback_years)


# ── Pillar 5: Tax Policy & Calculators (eco-policy-mcp) ─────────────────────

def calculate_gst_breakdown(
    amount: float,
    rate_percent: float,
    intra_state: bool = True,
) -> GSTSplitResponse:
    """Calculate GST breakup (CGST+SGST vs IGST) using verified CBIC rules."""
    from eco_policy_mcp.providers.gst import gst_split
    res = gst_split(amount, rate_percent, intra_state=intra_state)
    return GSTSplitResponse(
        data=GSTSplitBreakdown.model_validate(res["data"]),
        provenance=TaxProvenance.model_validate(res["provenance"]),
    )


def validate_gstin_number(gstin: str) -> GSTINValidationResponse:
    """Validate GSTIN structure, mod-36 checksum, and extract state metadata."""
    from eco_policy_mcp.providers.gst import validate_gstin, state_code_from_gstin
    is_valid = validate_gstin(gstin)
    state_code = None
    state_name = None
    if is_valid:
        sc = state_code_from_gstin(gstin)
        state_code = str(sc) if sc else None
        # Standard GST state code mapping
        _STATE_MAP = {
            "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
            "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
            "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
            "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
            "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
            "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
            "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "32": "Kerala",
            "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh",
        }
        state_name = _STATE_MAP.get(state_code, f"State Code {state_code}")

    return GSTINValidationResponse(
        gstin=gstin,
        is_valid=is_valid,
        state_code=state_code,
        state_name=state_name,
        provenance=TaxProvenance(
            source="eco-policy-mcp (GSTIN mod-36 checksum & state decoding)",
            as_of=datetime.now(timezone.utc).isoformat(),
            reference="https://services.gst.gov.in/",
        ),
    )


def compare_income_tax_regimes(
    gross_salary: float,
    deductions_80c: float = 150000.0,
    other_deductions: float = 0.0,
    age: int = 35,
) -> IncomeTaxComparisonResponse:
    """Compare New vs Old Tax Regimes under the Indian Finance Act."""
    from eco_policy_mcp.providers.income_tax import compare_regimes
    res = compare_regimes(gross_salary, deductions_80c=deductions_80c, other_deductions=other_deductions, age=age)
    res_data = dict(res["data"])
    res_data["gross_salary"] = gross_salary
    return IncomeTaxComparisonResponse(
        data=TaxRegimeComparison.model_validate(res_data),
        provenance=TaxProvenance.model_validate(res["provenance"]),
    )


# ── Pillar 6: Real-time News & Notifications (Tavily AI) ────────────────────

async def fetch_realtime_fiscal_news(
    query: str = "site:pib.gov.in Ministry of Finance monthly gross GST revenue collection fiscal deficit",
    max_results: int = 5,
) -> FiscalNewsResponse:
    """Fetch official Ministry of Finance / PIB fiscal news releases using Tavily."""
    key = fiscal_settings.TVLY_KEY_1 or fiscal_settings.TVLY_KEY_2 or fiscal_settings.TVLY_KEY_3
    now_ts = datetime.now(timezone.utc).isoformat()
    if not key:
        return FiscalNewsResponse(
            query=query,
            total_results=0,
            items=[],
            fetched_at=now_ts,
        )

    try:
        async with _build_client() as http_client:
            res = await http_client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                },
            )
            if res.is_success:
                data = res.json()
                items = [
                    FiscalNewsItem(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        published_date=item.get("published_date"),
                        source="PIB / Ministry of Finance (via Tavily)",
                    )
                    for item in data.get("results", [])
                ]
                return FiscalNewsResponse(
                    query=query,
                    total_results=len(items),
                    items=items,
                    fetched_at=now_ts,
                )
    except Exception as exc:
        logger.warning("Tavily fiscal news search failed: %s", exc)

    return FiscalNewsResponse(
        query=query,
        total_results=0,
        items=[],
        fetched_at=now_ts,
    )
