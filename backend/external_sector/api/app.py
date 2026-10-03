"""External Sector FastAPI Sub-Application."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from external_sector import client
from external_sector.client import ExternalDataUnavailableError
from external_sector.models import (
    BoPResponse,
    DataFreshness,
    ExchangeRatesResponse,
    ExternalDebtResponse,
    ExternalFlowsResponse,
    ForexReservesResponse,
    IMFExternalOutlookResponse,
    LiveMarketRatesResponse,
    RealtimeIntelligenceResponse,
    RemittancesResponse,
    TradeBalanceResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="External Sector API",
    description="HTTP endpoints for External Sector macroeconomic data, trade, reserves, and real-time intelligence.",
    version="1.1.0",
)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Health check endpoint for the external sector sub-application."""
    return {"status": "healthy", "sector": "external_sector", "version": "1.1.0"}


@app.get("/metadata", tags=["Registry"])
async def metadata() -> dict[str, Any]:
    """Registry metadata for indicators owned exclusively by the external sector."""
    return {
        "sector": "external_sector",
        "version": "1.1.0",
        "authority": "Reserve Bank of India (RBI) / MoSPI eSankhyiki",
        "owns": [
            "forex_reserves", "exports", "imports", "trade_balance",
            "bop", "usd_inr", "reer", "neer", "fdi", "fpi",
            "remittances", "external_debt", "live_market_rates", "realtime_intelligence"
        ],
    }


@app.get("/forex-reserves", response_model=ForexReservesResponse, tags=["External"])
async def forex_reserves(lookback_weeks: int = Query(default=12, ge=1, le=52)) -> ForexReservesResponse:
    """Fetch weekly foreign exchange reserves and import cover."""
    try:
        records = await client.fetch_forex_reserves(lookback_weeks)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ForexReservesResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /forex-reserves")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving foreign exchange reserves data.")


@app.get("/trade-balance", response_model=TradeBalanceResponse, tags=["External"])
async def trade_balance(lookback_months: int = Query(default=12, ge=1, le=60)) -> TradeBalanceResponse:
    """Fetch monthly merchandise exports, imports, and trade balance."""
    try:
        records = await client.fetch_trade_balance(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return TradeBalanceResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /trade-balance")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving trade balance data.")


@app.get("/balance-of-payments", response_model=BoPResponse, tags=["External"])
async def balance_of_payments(lookback_quarters: int = Query(default=8, ge=1, le=32)) -> BoPResponse:
    """Fetch quarterly balance of payments and current account deficit."""
    try:
        records = await client.fetch_balance_of_payments(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return BoPResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /balance-of-payments")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving balance of payments data.")


@app.get("/exchange-rates", response_model=ExchangeRatesResponse, tags=["External"])
async def exchange_rates(lookback_days: int = Query(default=90, ge=1, le=365)) -> ExchangeRatesResponse:
    """Fetch daily USD/INR reference rates and REER/NEER indices."""
    try:
        records = await client.fetch_exchange_rates(lookback_days)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExchangeRatesResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /exchange-rates")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving exchange rate data.")


@app.get("/live-market-rates", response_model=LiveMarketRatesResponse, tags=["External"])
async def live_market_rates() -> LiveMarketRatesResponse:
    """Fetch real-time spot FX rates (USD/INR, EUR/INR, GBP/INR, JPY/INR) and Brent crude oil benchmark."""
    try:
        record = await client.fetch_live_market_rates()
        return LiveMarketRatesResponse(status=DataFreshness.LIVE, record=record)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /live-market-rates")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving live market rates.")


@app.get("/remittances", response_model=RemittancesResponse, tags=["External"])
async def remittances(lookback_years: int = Query(default=5, ge=1, le=20)) -> RemittancesResponse:
    """Fetch private remittances and services invisibles from MoSPI eSankhyiki."""
    try:
        records = await client.fetch_remittances_and_invisibles(lookback_years)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return RemittancesResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /remittances")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving remittances data.")


@app.get("/external-debt", response_model=ExternalDebtResponse, tags=["External"])
async def external_debt(lookback_quarters: int = Query(default=8, ge=1, le=32)) -> ExternalDebtResponse:
    """Fetch quarterly external debt stock and vulnerability indicators from MoSPI eSankhyiki."""
    try:
        records = await client.fetch_external_debt(lookback_quarters)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExternalDebtResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /external-debt")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving external debt data.")


@app.get("/external-flows", response_model=ExternalFlowsResponse, tags=["External"])
async def external_flows(lookback_months: int = Query(default=12, ge=1, le=60)) -> ExternalFlowsResponse:
    """Fetch cross-border FDI and FPI investment flows."""
    try:
        records = await client.fetch_external_flows(lookback_months)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return ExternalFlowsResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /external-flows")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving external flows data.")


@app.get("/realtime-intelligence", response_model=RealtimeIntelligenceResponse, tags=["External"])
async def realtime_intelligence(
    query: str = Query(default="India foreign trade, forex reserves and rupee outlook"),
) -> RealtimeIntelligenceResponse:
    """Fetch real-time web intelligence and news articles using Tavily."""
    try:
        record = await client.fetch_realtime_intelligence(query=query)
        return RealtimeIntelligenceResponse(status=DataFreshness.LIVE, record=record)
    except (ExternalDataUnavailableError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Real-time intelligence unavailable: {exc}")
    except Exception:
        logger.exception("Internal error in GET /realtime-intelligence")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving real-time intelligence.")


@app.get("/imf-outlook", response_model=IMFExternalOutlookResponse, tags=["External"])
async def imf_outlook(
    start_year: str = Query(default="2022"),
    end_year: str = Query(default="2027"),
) -> IMFExternalOutlookResponse:
    """Fetch multilateral medium-term external outlook from IMF SDMX MCP server."""
    try:
        records = await client.fetch_imf_external_outlook(start_year, end_year)
        freshness = records[0].citation.freshness if records else DataFreshness.UNAVAILABLE
        return IMFExternalOutlookResponse(status=freshness, total_records=len(records), records=records)
    except ExternalDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Internal error in GET /imf-outlook")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving IMF external outlook data.")
