"""Services Sector FastAPI sub-application.

Mounted by backend/main.py at /services-sector.
Provides HTTP access to MCP tool results and sector metadata.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

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
)

app = FastAPI(
    title="Services Sector API",
    description=(
        "HTTP endpoints for the Services Sector Agent. "
        "All responses include mandatory citation metadata. "
        "No hardcoded or estimated values."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Health check for the services sector sub-application."""
    return {"status": "healthy", "sector": "services_sector", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Sector metadata — MCP registry discovery endpoint
# ---------------------------------------------------------------------------

@app.get("/metadata", tags=["Registry"])
async def sector_metadata() -> dict[str, Any]:
    """Returns sector capability metadata for MCP registry discovery.

    AI agents and developer registries can call this endpoint to understand
    what indicators this sector owns, what tools it exposes, and which
    peer sectors it collaborates with via A2A.
    """
    return {
        "sector": "services_sector",
        "version": "1.0.0",
        "domain": "India — Services Production & Activity",
        "authority": "National Statistical Office (NSO), MoSPI",
        "data_source": "MoSPI e-Sankhyiki MCP (https://mcp.mospi.gov.in/)",
        "mcp_workflow": "list_datasets -> get_indicators -> get_metadata -> get_data",
        "citation_policy": "No Source, No Answer — every value carries mandatory citation metadata.",
        "tools": [
            {
                "name": "get_isp_growth",
                "description": "Monthly Index of Service Production, General + 19 sub-sectors (IT, telecom, trade, transport).",
                "frequency": "Monthly",
                "dataset": "ISP (base_year 2024-25, frequency_code 2, type_code 1/2)",
            },
            {
                "name": "get_services_gva",
                "description": "Structural services GVA from NAS Statements 8.9-8.14 (trade, transport, finance, real estate).",
                "frequency": "Annual",
                "dataset": "NAS (Statements 8.9-8.14)",
            },
            {
                "name": "get_services_pmi",
                "description": "Services PMI headline activity, new orders, input costs, employment (S&P Global/HSBC).",
                "frequency": "Monthly",
                "dataset": "sp_global.services_pmi_india",
            },
            {
                "name": "get_transport_and_freight_indicators",
                "description": "Aviation traffic, railway freight, port cargo, telecom subscriptions.",
                "frequency": "Monthly",
                "dataset": "NSS80 (CMST) + DGCA/IPA/TRAI mirrors",
            },
        ],
        "owns": [
            "isp_general_yoy",
            "isp_sub_sector_indices",
            "services_gva_structural",
            "services_pmi_headline",
            "transport_freight_volumes",
            "telecom_subscriptions",
        ],
        "does_not_own": [
            "aggregate_services_gva_quarterly (real_sector)",
            "bank_credit_to_services (finance_sector)",
            "net_services_exports_usd (external_sector)",
            "tertiary_employment_share (labour_sector)",
            "services_cpi_inflation (prices_sector)",
        ],
        "a2a_inbound": [
            "services_credit from finance_sector",
            "services_cpi from prices_sector",
            "quarterly_gva from real_sector",
        ],
        "a2a_outbound": [
            "isp_momentum to real_sector",
            "it_capacity to external_sector",
            "services_sentiment to labour_sector",
        ],
    }


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

@app.get("/isp-growth", response_model=ISPGrowthResponse, tags=["Services"])
async def isp_growth(
    sub_sector: ServiceSubSector | None = Query(default=None),
    lookback_months: int = Query(default=12, ge=1, le=60),
) -> ISPGrowthResponse:
    """Monthly Index of Service Production (General + sub-sectors)."""
    try:
        records = await client.fetch_isp_growth(sub_sector, lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ISPGrowthResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except ServicesDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/services-gva", response_model=ServicesGVAResponse, tags=["Services"])
async def services_gva() -> ServicesGVAResponse:
    """Structural services GVA from NAS Statements 8.9-8.14."""
    try:
        records = await client.fetch_services_gva()
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ServicesGVAResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except ServicesDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/services-pmi", response_model=ServicesPMIResponse, tags=["Services"])
async def services_pmi(
    lookback_months: int = Query(default=12, ge=1, le=60),
) -> ServicesPMIResponse:
    """Services PMI headline and sub-indices."""
    try:
        records = await client.fetch_services_pmi(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ServicesPMIResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except ServicesDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/transport-freight", response_model=TransportFreightResponse, tags=["Services"])
async def transport_freight(
    lookback_months: int = Query(default=6, ge=1, le=36),
) -> TransportFreightResponse:
    """Transport, freight, and telecom volumes."""
    try:
        records = await client.fetch_transport_and_freight(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TransportFreightResponse(
            status=freshness,
            total_records=len(records),
            records=records,
        )
    except ServicesDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/market-indicators", response_model=ServicesMarketResponse, tags=["Services"])
async def market_indicators() -> ServicesMarketResponse:
    """Nifty IT index (^CNXIT) and major IT services equity valuations from yfinance."""
    return await fetch_services_market_indicators()


@app.get("/realtime-news", response_model=ServicesNewsResponse, tags=["Services"])
async def realtime_news(
    query: str = Query(
        default="India services sector PMI IT services growth MoSPI ISP",
        description="Search query for live services news",
    ),
    max_results: int = Query(default=5, ge=1, le=10),
) -> ServicesNewsResponse:
    """Real-time services and IT news from Tavily AI Search."""
    return await fetch_realtime_services_news(query=query, max_results=max_results)
