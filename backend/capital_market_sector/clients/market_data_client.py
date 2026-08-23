"""Capital Markets Data Client with Yahoo Finance integration and verified DuckDB fallback."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pandas as pd
import requests
import yfinance as yf

from core.database.macro_store import macro_store


class CapitalMarketsDataClient:
    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }

    def _normalize_series(self, data: pd.DataFrame, indicator_name: str, source: str) -> pd.DataFrame:
        if data.empty or "Close" not in data.columns:
            # Query verified time series from DuckDB store
            cached = macro_store.get_time_series(sector="capital_markets", indicator=indicator_name.lower().replace(" ", "_"))
            if not cached.empty:
                return cached.assign(indicator_name=indicator_name)
            return pd.DataFrame(columns=["date", "value", "unit", "source", "data_status", "indicator_name"])

        df = data.reset_index()
        if "Date" in df.columns:
            df["date"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        else:
            df["date"] = datetime.now(timezone.utc).date().isoformat()

        df["value"] = df["Close"].astype(float)
        df["unit"] = "points"
        df["source"] = source
        df["data_status"] = "live"
        df["indicator_name"] = indicator_name

        # Cache the latest observation
        latest = df.iloc[-1]
        macro_store.insert_observation(
            sector="capital_markets",
            indicator=indicator_name.lower().replace(" ", "_"),
            sub_indicator="Index Level",
            observation_date=str(latest["date"]),
            value=float(latest["value"]),
            unit="points",
            source=source,
            data_status="live"
        )

        return df[["date", "value", "unit", "source", "data_status", "indicator_name"]]

    def _fetch_yahoo_history(self, ticker: str, period: str = "30d") -> pd.DataFrame:
        try:
            ticker_obj = yf.Ticker(ticker)
            history = ticker_obj.history(period=period, auto_adjust=False)
            return history[["Close"]] if not history.empty else pd.DataFrame(columns=["Close"])
        except Exception:
            return pd.DataFrame(columns=["Close"])

    def get_nifty_50(self) -> pd.DataFrame:
        """Fetch NIFTY 50 index series from NSE/Yahoo Finance with DuckDB store fallback."""
        data = self._fetch_yahoo_history("^NSEI")
        return self._normalize_series(data, "NIFTY 50", "NSE / Yahoo Finance")

    def get_sensex(self) -> pd.DataFrame:
        """Fetch SENSEX index series from BSE/Yahoo Finance with DuckDB store fallback."""
        data = self._fetch_yahoo_history("^BSESN")
        return self._normalize_series(data, "SENSEX", "BSE / Yahoo Finance")

    def get_india_vix(self) -> pd.DataFrame:
        """Fetch India VIX volatility index from NSE/Yahoo Finance with DuckDB store fallback."""
        data = self._fetch_yahoo_history("^INDIAVIX")
        return self._normalize_series(data, "India VIX", "NSE / Yahoo Finance")

    def get_corporate_earnings(self) -> pd.DataFrame:
        """Fetch corporate earnings fundamentals from verified historical store or composite indices."""
        cached_eps = macro_store.get_latest_observation(sector="capital_markets", indicator="corporate_earnings", sub_indicator="NIFTY 50 TTM EPS")
        cached_pat = macro_store.get_latest_observation(sector="capital_markets", indicator="corporate_earnings", sub_indicator="NIFTY 50 PAT Growth")

        rows = []
        if cached_eps:
            rows.append({
                "date": cached_eps["latest_period"],
                "indicator_name": "NIFTY 50 TTM EPS",
                "value": cached_eps["latest_value"],
                "unit": cached_eps["unit"],
                "source": cached_eps["source"],
                "data_status": cached_eps["data_status"]
            })
        if cached_pat:
            rows.append({
                "date": cached_pat["latest_period"],
                "indicator_name": "NIFTY 50 PAT Growth",
                "value": cached_pat["latest_value"],
                "unit": cached_pat["unit"],
                "source": cached_pat["source"],
                "data_status": cached_pat["data_status"]
            })

        return pd.DataFrame(rows)

    def get_primary_market_activity(self) -> pd.DataFrame:
        """Fetch primary market issuance indicators from verified SEBI data store."""
        cached = macro_store.get_latest_observation(sector="capital_markets", indicator="primary_market", sub_indicator="IPO Mobilization")
        if cached:
            return pd.DataFrame([{
                "date": cached["latest_period"],
                "indicator_name": "IPO Mobilization",
                "value": cached["latest_value"],
                "unit": cached["unit"],
                "source": cached["source"],
                "data_status": cached["data_status"]
            }])
        return pd.DataFrame(columns=["date", "indicator_name", "value", "unit", "source", "data_status"])

    def get_mf_flows(self) -> pd.DataFrame:
        """Fetch Mutual Fund & Domestic Institutional Investor (DII) flows from verified AMFI/SEBI store."""
        cached_equity = macro_store.get_latest_observation(sector="capital_markets", indicator="mf_flows", sub_indicator="Equity Net Inflows")
        cached_dii = macro_store.get_latest_observation(sector="capital_markets", indicator="mf_flows", sub_indicator="DII Net Purchases")

        rows = []
        if cached_equity:
            rows.append({
                "date": cached_equity["latest_period"],
                "indicator_name": "Equity Net Inflow",
                "value": cached_equity["latest_value"],
                "unit": cached_equity["unit"],
                "source": cached_equity["source"],
                "data_status": cached_equity["data_status"]
            })
        if cached_dii:
            rows.append({
                "date": cached_dii["latest_period"],
                "indicator_name": "DII Net Purchase",
                "value": cached_dii["latest_value"],
                "unit": cached_dii["unit"],
                "source": cached_dii["source"],
                "data_status": cached_dii["data_status"]
            })

        return pd.DataFrame(rows)
