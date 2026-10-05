"""Services Sector FastMCP Server.

Exposes official MoSPI e-Sankhyiki MCP data (ISP + NAS services GVA),
curated PMI sentiment, high-frequency volumes, yfinance market context,
and Tavily real-time news tools.
Strict Provenance: every response includes Citation metadata.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from services_sector import client
from services_sector.cache_loaders import ServicesDataUnavailableError
from services_sector.market_client import (
    fetch_realtime_services_news,
    fetch_services_market_indicators,
)
from services_sector.models import (
    DataFreshness,
    ISPGrowthResponse,
    ServicesGVAResponse,
    ServicesMarketResponse,
    ServicesNewsResponse,
    ServicesPMIResponse,
    ServiceSubSector,
    TransportFreightResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP Server — metadata used by MCP registries and discovery layers
# ---------------------------------------------------------------------------

mcp_server = FastMCP(
    name="Services Sector MCP Server",
    instructions=(
        "Provides official MoSPI macroeconomic data for India's services sector: "
        "Index of Service Production (ISP, monthly, base 2024-25), Services GVA "
        "from National Accounts Statistics (Statements 8.9-8.14), Services PMI "
        "sentiment, and high-frequency transport/freight/telecom volumes. "
        "All values carry mandatory citation metadata (source, table, period, URL). "
        "No Source, No Answer: values without citations are a protocol violation. "
        "Data is fetched live from the MoSPI e-Sankhyiki MCP (https://mcp.mospi.gov.in/) "
        "via the list_datasets -> get_indicators -> get_metadata -> get_data workflow; "
        "on failure, the most recent cached data from the sector's dedicated "
        "DuckDB store is returned with freshness=CACHED."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server


# ---------------------------------------------------------------------------
# Tool 1 — ISP Growth (MoSPI ISP: General + 19 sub-sectors)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_isp_growth",
    title="Index of Service Production (ISP) Growth",
    description=(
        "Fetches monthly Index of Service Production (Base 2024-25 = 100) with "
        "YoY/MoM growth for 19 broad sub-sectors (wholesale/retail trade, "
        "transport, telecom, IT, banking, real estate, professional services, "
        "etc.) from the MoSPI e-Sankhyiki MCP (dataset ISP, "
        "filters frequency_code=2 + FY year). "
        "Live fetch from https://mcp.mospi.gov.in/ with DuckDB fallback. "
        "NOTE: the MCP view publishes sub-sectors only — no General row."
    ),
    tags={"services", "isp", "services-production", "india", "mospi"},
)
async def get_isp_growth(
    sub_sector: Annotated[
        ServiceSubSector | None,
        Field(
            default=None,
            description="Filter to one sub-sector (e.g. IT_COMPUTER, TELECOMMUNICATIONS). Omit for all.",
        ),
    ] = None,
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=60, description="Number of months of history to return."),
    ] = 12,
) -> ISPGrowthResponse | UnavailableResponse:
    """Return monthly ISP index and growth for the past N months.

    Every record includes a Citation with source authority, dataset reference,
    observation period, and retrieval URL.
    """
    try:
        records = await client.fetch_isp_growth(sub_sector, lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ISPGrowthResponse(
            status=freshness,
            records=records,
            total_records=len(records),
        )
    except ServicesDataUnavailableError as exc:
        logger.error("get_isp_growth: %s", exc)
        return UnavailableResponse(tool="get_isp_growth", reason=str(exc))
    except Exception as exc:
        logger.exception("get_isp_growth: unexpected error")
        return UnavailableResponse(
            tool="get_isp_growth", reason=f"Unexpected error: {exc}", error_detail=repr(exc)
        )


# ---------------------------------------------------------------------------
# Tool 2 — Services GVA (MoSPI NAS Statements 8.9–8.14)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_services_gva",
    title="Services GVA from National Accounts (NAS 8.9–8.14)",
    description=(
        "Fetches services-sector GVA at current and constant prices "
        "from MoSPI National Accounts Statistics (indicator_code 1 = GVA, "
        "base 2011-12 Current series, annual) for services industries: trade "
        "& hotels, transport & communication, financial services, real estate "
        "& professional services, public administration and other services. "
        "Structural/macroeconomic measure — complements high-frequency ISP. "
        "Live fetch from https://mcp.mospi.gov.in/ with DuckDB fallback."
    ),
    tags={"services", "gva", "national-accounts", "nas", "india", "mospi"},
)
async def get_services_gva() -> ServicesGVAResponse | UnavailableResponse:
    """Return services GVA by NAS statement (structural annual measure)."""
    try:
        records = await client.fetch_services_gva()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ServicesGVAResponse(
            status=freshness, records=records, total_records=len(records)
        )
    except ServicesDataUnavailableError as exc:
        logger.error("get_services_gva: %s", exc)
        return UnavailableResponse(tool="get_services_gva", reason=str(exc))
    except Exception as exc:
        logger.exception("get_services_gva: unexpected error")
        return UnavailableResponse(
            tool="get_services_gva", reason=f"Unexpected error: {exc}", error_detail=repr(exc)
        )


# ---------------------------------------------------------------------------
# Tool 3 — Services PMI Sentiment
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_services_pmi",
    title="Services PMI Business Activity & Sentiment",
    description=(
        "Fetches headline Services PMI (50 = no change), new orders, input costs, "
        "and employment sentiment from the sector's curated S&P Global / HSBC "
        "press-release mirror. NOTE: PMI is proprietary survey data with no "
        "MoSPI MCP dataset — observations are honestly reported as CACHED, "
        "with real-time headlines via get_realtime_services_news."
    ),
    tags={"services", "pmi", "sentiment", "business-activity", "india"},
)
async def get_services_pmi(
    lookback_months: Annotated[
        int,
        Field(default=12, ge=1, le=60, description="Number of months of history to return."),
    ] = 12,
) -> ServicesPMIResponse | UnavailableResponse:
    """Return Services PMI headline and sub-indices for the past N months."""
    try:
        records = await client.fetch_services_pmi(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ServicesPMIResponse(
            status=freshness, records=records, total_records=len(records)
        )
    except ServicesDataUnavailableError as exc:
        logger.error("get_services_pmi: %s", exc)
        return UnavailableResponse(tool="get_services_pmi", reason=str(exc))
    except Exception as exc:
        logger.exception("get_services_pmi: unexpected error")
        return UnavailableResponse(
            tool="get_services_pmi", reason=f"Unexpected error: {exc}", error_detail=repr(exc)
        )


# ---------------------------------------------------------------------------
# Tool 4 — Transport, Freight & Telecom Volumes
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_transport_and_freight_indicators",
    title="Transport, Freight & Telecom Volumes",
    description=(
        "Fetches All-India telecom & digital penetration (% of households: "
        "phone connectivity, internet facility, rural/urban) from the NSS 80th "
        "round CMST module via the MoSPI MCP (dataset NSS80, All-India "
        "state_code 37). Point-in-time survey wave. "
        "Live fetch with DuckDB fallback."
    ),
    tags={"services", "transport", "freight", "aviation", "telecom", "india", "mospi"},
)
async def get_transport_and_freight_indicators(
    lookback_months: Annotated[
        int,
        Field(default=6, ge=1, le=36, description="Number of months of history to return."),
    ] = 6,
) -> TransportFreightResponse | UnavailableResponse:
    """Return transport/freight/telecom volumes for the past N months."""
    try:
        records = await client.fetch_transport_and_freight(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TransportFreightResponse(
            status=freshness, records=records, total_records=len(records)
        )
    except ServicesDataUnavailableError as exc:
        logger.error("get_transport_and_freight_indicators: %s", exc)
        return UnavailableResponse(tool="get_transport_and_freight_indicators", reason=str(exc))
    except Exception as exc:
        logger.exception("get_transport_and_freight_indicators: unexpected error")
        return UnavailableResponse(
            tool="get_transport_and_freight_indicators",
            reason=f"Unexpected error: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 5 — Services Market Context (yfinance: NIFTY IT + IT stocks)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_services_market_indicators",
    title="Services Market Context (Nifty IT & IT Stocks)",
    description=(
        "Fetches live market valuation, current price, day return, P/E, P/B, and 52-week "
        "range for the Nifty IT index (^CNXIT) and major Indian IT services stocks "
        "(TCS, Infosys, HCLTech, Wipro, Tech Mahindra) via Yahoo Finance, as a "
        "momentum cross-check on IT services activity."
    ),
    tags={"services", "market", "equities", "nifty-it", "valuation", "yfinance"},
)
async def get_services_market_indicators() -> ServicesMarketResponse | UnavailableResponse:
    """Return live quotes and valuation metrics for services-linked equities."""
    try:
        return await fetch_services_market_indicators()
    except Exception as exc:
        logger.exception("get_services_market_indicators: unexpected error")
        return UnavailableResponse(
            tool="get_services_market_indicators",
            reason=f"Market data fetch failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Tool 6 — Real-Time Services News & Intelligence (Tavily)
# ---------------------------------------------------------------------------

@mcp_server.tool(
    name="get_realtime_services_news",
    title="Real-Time Services & IT Intelligence",
    description=(
        "Enriches services intelligence with real-time news, MoSPI release coverage, "
        "and IT/services policy commentary using Tavily AI Search (TVLY_KEY_1)."
    ),
    tags={"services", "news", "policy", "pmi", "realtime", "tavily"},
)
async def get_realtime_services_news(
    query: Annotated[
        str,
        Field(default="India services sector PMI IT services growth MoSPI ISP", description="Services search query."),
    ] = "India services sector PMI IT services growth MoSPI ISP",
    max_results: Annotated[
        int,
        Field(default=5, ge=1, le=10, description="Maximum news articles to retrieve."),
    ] = 5,
) -> ServicesNewsResponse | UnavailableResponse:
    """Return real-time services news and policy updates for a topic."""
    try:
        return await fetch_realtime_services_news(query=query, max_results=max_results)
    except Exception as exc:
        logger.exception("get_realtime_services_news: unexpected error")
        return UnavailableResponse(
            tool="get_realtime_services_news",
            reason=f"News search failed: {exc}",
            error_detail=repr(exc),
        )


# ---------------------------------------------------------------------------
# Resources — Read-only reference catalogs (FastMCP Resource)
# ---------------------------------------------------------------------------

@mcp.resource("services://catalog")
def get_catalog() -> str:
    """Read-only catalog of official MoSPI dataset references and indicator mappings."""
    import json
    return json.dumps(
        {
            "sector": "services_sector",
            "authority": "National Statistical Office (NSO), MoSPI",
            "mcp_endpoint": "https://mcp.mospi.gov.in/",
            "mcp_workflow": "list_datasets -> get_indicators -> get_metadata -> get_data",
            "datasets": {
                "ISP": {
                    "title": "Index of Service Production",
                    "base_year": "2024-25",
                    "filters": {"frequency_code": 2, "year": "YYYY-YY (FY)", "limit": 500},
                    "month_code": "Indian FY: 1=April ... 12=March",
                    "broad_sub_sector_code": "1-19 (see ISP_SUB_SECTOR_CODES)",
                    "note": "MCP view publishes the 19 sub-sectors only; no General row.",
                },
                "NAS": {
                    "title": "National Accounts Statistics — Services GVA",
                    "filters": {"indicator_code": 1, "base_year": "2011-12",
                                "series": "Current", "frequency_code": 1,
                                "industry_code": "6,7,8,9,10,11,12,14 (services)"},
                    "statement_labels": {
                        "8.9": "Trade, Repair, Hotels and Restaurants",
                        "8.10-8.11": "Transport, Storage, Communication & Broadcasting",
                        "8.12": "Financial Services",
                        "8.13": "Real Estate, Ownership of Dwelling & Professional Services",
                        "8.14": "Public Administration, Defence & Other Services",
                    },
                },
                "NSS80": {
                    "title": "Comprehensive Modular Survey: Telecom (CMST)",
                    "filters": {"indicator_code": "17 (phones) / 18 (internet)",
                                "state_code": "37 (All-India)"},
                },
            },
            "pmi_note": "No PMI dataset exists on the MoSPI MCP (verified). PMI is served from the curated S&P Global/HSBC mirror as CACHED.",
            "citation_policy": "Strict provenance citation required for all observations.",
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompts — Reusable analysis prompt templates (FastMCP Prompt)
# ---------------------------------------------------------------------------

@mcp.prompt()
def analyze_services_activity(focus_area: str = "isp_and_it_services") -> str:
    """Prompt template for analyzing India's services production and momentum."""
    return (
        f"Perform a comprehensive review of India's services sector "
        f"focusing on {focus_area}. "
        f"Fetch latest ISP General index and IT/telecom/professional sub-sectors, "
        f"Services GVA (NAS 8.9-8.14), Services PMI sentiment, and transport volumes. "
        f"Strictly enforce the 'No Source, No Answer' policy with official MoSPI citations. "
        f"Distinguish high-frequency ISP (monthly production) from structural NAS GVA."
    )
