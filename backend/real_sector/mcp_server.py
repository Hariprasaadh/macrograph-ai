"""Real Sector FastMCP Server.

Exposes FastMCP tools for:
  - MoSPI IIP Sectoral (Manufacturing, Mining, Electricity)
  - MoSPI IIP Use-Based (Capital goods, Intermediate goods, Consumer durables)
  - DPIIT Eight Core Industries (Steel, Cement, Electricity, Coal, Refinery)
  - DuckDB JOIN multi-indicator view with trend analytics
  - Infrastructure & Industrial listed equity market context
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from real_sector import database as db
from real_sector import client
from real_sector.client import RealSectorDataUnavailableError
from real_sector.models import (
    CoreIndustriesResponse,
    DataFreshness,
    IIPSectoralResponse,
    IIPUseBasedResponse,
    ManufacturingGVAResponse,
    MarketContextResponse,
    RealSectorJoinedResponse,
    UnavailableResponse,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP(
    name="Real Sector & Industrial Output MCP Server",
    instructions=(
        "and industrial market context. All observations include mandatory provenance citations."
    ),
    version="1.0.0",
)
mcp = mcp_server
server = mcp_server

db.initialise_schema()


@mcp_server.tool(
    name="get_iip_sectoral",
    title="MoSPI IIP Sectoral Breakdown",
    description=(
        "Fetches Index of Industrial Production (IIP) broken down by Mining, Manufacturing, "
        "and Electricity. Source: MoSPI Quick Estimates of IIP (2011-12=100)."
    ),
    tags={"real_sector", "iip", "manufacturing", "mining", "electricity", "mospi"},
)
async def get_iip_sectoral(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> IIPSectoralResponse | UnavailableResponse:
    try:
        records = await client.fetch_iip_sectoral(lookback_months)
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IIPSectoralResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_iip_sectoral", reason=str(exc))


@mcp_server.tool(
    name="get_iip_use_based",
    title="MoSPI IIP Use-Based Classification",
    description=(
        "Fetches Use-Based IIP series: Primary goods, Capital goods, Intermediate goods, "
        "Infrastructure/construction goods, Consumer durables, and Consumer non-durables. "
        "Source: MoSPI (2011-12=100)."
    ),
    tags={"real_sector", "iip", "use_based", "capital_goods", "consumer_durables", "mospi"},
)
async def get_iip_use_based(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> IIPUseBasedResponse | UnavailableResponse:
    try:
        records = await client.fetch_iip_use_based(lookback_months)
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IIPUseBasedResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_iip_use_based", reason=str(exc))


@mcp_server.tool(
    name="get_core_industries",
    title="DPIIT Index of Eight Core Industries (ICI)",
    description=(
        "Fetches output and YoY growth for the 8 Core Industries: Coal, Crude Oil, Natural Gas, "
        "Refinery Products, Fertilizers, Steel, Cement, and Electricity. "
        "Source: DPIIT / Office of Economic Adviser."
    ),
    tags={"real_sector", "core_industries", "steel", "cement", "coal", "ici", "dpiit"},
)
async def get_core_industries(
    lookback_months: Annotated[int, Field(default=12, ge=1, le=60)] = 12,
) -> CoreIndustriesResponse | UnavailableResponse:
    try:
        records = await client.fetch_core_industries(lookback_months)
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return CoreIndustriesResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_core_industries", reason=str(exc))


@mcp_server.tool(
    name="get_manufacturing_gva",
    title="Manufacturing GVA Growth & Share",
    description="Fetches Real and Nominal Manufacturing Gross Value Added (GVA) from NSO / RBI DBIE.",
    tags={"real_sector", "gva", "manufacturing", "rbi", "nso"},
)
async def get_manufacturing_gva(
    lookback_quarters: Annotated[int, Field(default=8, ge=1, le=32)] = 8,
) -> ManufacturingGVAResponse | UnavailableResponse:
    try:
        records = await client.fetch_manufacturing_gva(lookback_quarters)
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ManufacturingGVAResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_manufacturing_gva", reason=str(exc))


@mcp_server.tool(
    name="get_joined_real_sector_indicators",
    title="Composite Multi-Indicator Real Sector View",
    description=(
        "Executes a multi-indicator composite view linking IIP Sectoral, Use-Based, Core Industries, "
        "and GVA by period with automated Step 6 trend direction analytics."
    ),
    tags={"real_sector", "joined_view", "composite", "trend_analytics"},
)
async def get_joined_real_sector_indicators() -> RealSectorJoinedResponse | UnavailableResponse:
    try:
        records = await client.fetch_joined_real_indicators()
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return RealSectorJoinedResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_joined_real_sector_indicators", reason=str(exc))


@mcp_server.tool(
    name="get_infrastructure_market_context",
    title="Infrastructure & Industrial Listed Equity Context",
    description="Fetches market returns and valuations for Steel, Cement, and Capital Goods listed bellwethers.",
    tags={"real_sector", "market_context", "steel_stocks", "cement_stocks", "capital_goods"},
)
async def get_infrastructure_market_context() -> MarketContextResponse | UnavailableResponse:
    try:
        records = await client.fetch_infrastructure_market_context()
        freshness = records[-1].citation.freshness if records else DataFreshness.UNAVAILABLE
        return MarketContextResponse(status=freshness, records=records, total_records=len(records))
    except Exception as exc:
        return UnavailableResponse(tool="get_infrastructure_market_context", reason=str(exc))


@mcp.resource("real://catalog")
def get_catalog() -> str:
    """Catalog of official Real Sector data tables and provenance mappings."""
    import json
    return json.dumps(
        {
            "sector": "real_sector",
            "authorities": [
                "Ministry of Statistics and Programme Implementation (MoSPI)",
                "DPIIT / Office of Economic Adviser",
                "Reserve Bank of India (RBI)",
                "National Stock Exchange of India (NSE)",
            ],
            "pillars": {
                "iip_sectoral": "Quick Estimates of Index of Industrial Production (Mining, Manufacturing, Electricity)",
                "iip_use_based": "IIP Use-Based Classification (Primary, Capital, Intermediate, Infra, Durables)",
                "eight_core_industries": "DPIIT ICI (Coal, Crude, Gas, Refinery, Fertilizer, Steel, Cement, Electricity)",
                "gva_manufacturing": "Quarterly Estimates of GVA at Basic Prices (Manufacturing)",
                "market_context": "Infrastructure, Steel, Cement & Capital Goods Equity Bellwethers",
            },
        },
        indent=2,
    )


@mcp.prompt()
def analyze_industrial_and_manufacturing_trends() -> str:
    """Prompt template for industrial output and manufacturing diagnostic analysis."""
    return (
        "Conduct a comprehensive diagnostic of India's real sector and industrial momentum. "
        "Formulate an evidence-grounded synthesis following the structured pattern with trend directions and market context."
    )
