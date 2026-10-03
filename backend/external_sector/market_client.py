"""Live Market Client for Spot FX Rates and Brent Crude Benchmark."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

import yfinance as yf

from external_sector.models import Citation, DataFreshness, LiveMarketRatesRecord

logger = logging.getLogger(__name__)


def _fetch_sync_market_rates() -> dict[str, float | None]:
    symbols = {
        "usd_inr": "INR=X",
        "eur_inr": "EURINR=X",
        "gbp_inr": "GBPINR=X",
        "jpy_inr": "JPYINR=X",
        "brent_crude": "BZ=F",
    }
    rates: dict[str, float | None] = {}
    for key, sym in symbols.items():
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if not hist.empty and "Close" in hist:
                rates[key] = round(float(hist["Close"].iloc[-1]), 4)
            else:
                rates[key] = None
        except Exception as exc:
            logger.warning("Failed to fetch market ticker %s: %s", sym, exc)
            rates[key] = None
    return rates


async def fetch_live_market_rates() -> LiveMarketRatesRecord:
    """Fetch real-time spot FX rates and Brent crude oil benchmark via yfinance."""
    rates = await asyncio.to_thread(_fetch_sync_market_rates)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    citation = Citation(
        source_agent="external_sector",
        source_authority="Yahoo Finance / Refinitiv FX",
        document_title="Live FX Reference Spot Rates & Brent Crude Benchmark",
        table_reference="yfinance.tickers.INR=X,BZ=F",
        retrieval_url="https://finance.yahoo.com/quote/INR=X",
        observation_period=now.strftime("%Y-%m-%d %H:%M UTC"),
        fetched_at=now,
        freshness=DataFreshness.LIVE,
    )

    return LiveMarketRatesRecord(
        timestamp=now_iso,
        usd_inr=rates.get("usd_inr"),
        eur_inr=rates.get("eur_inr"),
        gbp_inr=rates.get("gbp_inr"),
        jpy_inr=rates.get("jpy_inr"),
        brent_crude_usd=rates.get("brent_crude"),
        citation=citation,
    )
