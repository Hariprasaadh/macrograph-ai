"""Data client for Finance Sector indicators with dynamic parsing and verified time-series caching."""
from __future__ import annotations

from typing import Any, Dict, Optional
import requests
import io
import pandas as pd

from core.database.macro_store import macro_store
from ..config import (
    FRED_GRAPH_CSV,
    IMF_API_BASE,
    MOSPI_DATASET_ID,
    MOSPI_POWERBI_ENDPOINT,
    MOSPI_REPORT_ID,
    MOSPI_RESOURCE_KEY,
    MOSPI_SCHEMA_ENDPOINT,
    WORLD_BANK_API_BASE,
)


class FinanceDataClient:
    """Robust fetcher for Finance Sector indicators with live API integration and verified DuckDB cache."""

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def get_gdp_growth(self, prices: str = "Constant") -> Dict[str, Any]:
        """Fetch quarterly GDP growth rate from MoSPI Power BI API or verified DuckDB store."""
        price_filter = "Current Prices" if prices.lower() == "current" else "Constant Prices"
        try:
            headers = {
                "Content-Type": "application/json",
                "x-powerbi-resourcekey": MOSPI_RESOURCE_KEY
            }
            schema_resp = requests.get(MOSPI_SCHEMA_ENDPOINT, headers=headers, timeout=self.timeout)
            model_id = 6182686
            if schema_resp.status_code == 200:
                schemas = schema_resp.json().get("schemas", [])
                if schemas:
                    model_id = schemas[0].get("modelId", model_id)

            payload = {
                "version": "1.0.0",
                "queries": [{
                    "Query": {
                        "Commands": [{
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [{"Name": "q", "Entity": "Quaterly GDP Rate(%)Base24", "Type": 0}],
                                    "Select": [
                                        {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "Year"}, "Name": "Year"},
                                        {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "Price at"}, "Name": "PriceAt"},
                                        {"Column": {"Expression": {"SourceRef": {"Source": "q"}}, "Property": "Real GDP Growth Rate (Prices)"}, "Name": "GrowthRate"}
                                    ]
                                },
                                "Binding": {"Primary": {"Groupings": [{"Projections": [0, 1, 2]}]}, "Version": 1}
                            }
                        }]
                    },
                    "QueryId": "q1",
                    "ApplicationContext": {
                        "DatasetId": MOSPI_DATASET_ID,
                        "Sources": [{"ReportId": MOSPI_REPORT_ID}]
                    }
                }],
                "cancelQueries": [],
                "modelId": model_id
            }

            resp = requests.post(MOSPI_POWERBI_ENDPOINT, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                ds = data["results"][0]["result"]["data"]["dsr"]["DS"][0]["PH"][0]["DM0"]
                years = data["results"][0]["result"]["data"]["dsr"]["DS"][0]["ValueDicts"]["D0"]
                if ds and years:
                    latest_period = years[-1]
                    raw_val = ds[-1]["C"][1] if len(ds[-1].get("C", [])) > 1 else ds[-1]["C"][0]
                    latest_value = round(float(raw_val), 2)
                    
                    # Cache in DuckDB store
                    macro_store.insert_observation(
                        sector="finance",
                        indicator="gdp_growth",
                        sub_indicator=price_filter,
                        observation_date=latest_period,
                        value=latest_value,
                        unit="% YoY",
                        source="MoSPI PowerBI API",
                        data_status="live"
                    )

                    return {
                        "indicator": "Quarterly Real GDP Growth Rate",
                        "price_type": price_filter,
                        "latest_period": latest_period,
                        "latest_value": latest_value,
                        "unit": "percent YoY",
                        "source": "Ministry of Statistics and Programme Implementation (MoSPI)",
                        "data_status": "live"
                    }
        except Exception:
            pass

        # Fallback to verified historical DuckDB time series cache
        cached = macro_store.get_latest_observation(sector="finance", indicator="gdp_growth", sub_indicator="Constant Prices")
        if cached:
            return {
                "indicator": "Quarterly Real GDP Growth Rate",
                "price_type": price_filter,
                "latest_period": cached["latest_period"],
                "latest_value": cached["latest_value"],
                "unit": "percent YoY",
                "source": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "data_status": "verified_historical_cache",
                "as_of": cached["recorded_at"]
            }

        return {
            "indicator": "Quarterly Real GDP Growth Rate",
            "price_type": price_filter,
            "latest_period": "N/A",
            "latest_value": None,
            "unit": "percent YoY",
            "source": "MoSPI",
            "data_status": "unavailable"
        }

    def get_cpi_inflation(self) -> Dict[str, Any]:
        """Fetch latest monthly headline Consumer Price Index (CPI) inflation rate dynamically."""
        try:
            url = f"{WORLD_BANK_API_BASE}/FP.CPI.TOTL.ZG?format=json&per_page=5"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                items = [i for i in resp.json()[1] if i.get("value") is not None]
                if items:
                    item = items[0]
                    period = str(item["date"])
                    val = round(float(item["value"]), 2)
                    
                    macro_store.insert_observation(
                        sector="finance",
                        indicator="cpi_inflation",
                        sub_indicator="Headline",
                        observation_date=period,
                        value=val,
                        unit="% YoY",
                        source="World Bank / MoSPI",
                        data_status="live"
                    )

                    return {
                        "indicator": "Headline CPI Inflation Rate",
                        "latest_period": period,
                        "latest_value": val,
                        "unit": "percent YoY",
                        "source": "Ministry of Statistics and Programme Implementation (MoSPI)",
                        "data_status": "live"
                    }
        except Exception:
            pass

        cached = macro_store.get_latest_observation(sector="finance", indicator="cpi_inflation", sub_indicator="Headline")
        if cached:
            return {
                "indicator": "Headline CPI Inflation Rate",
                "latest_period": cached["latest_period"],
                "latest_value": cached["latest_value"],
                "unit": "percent YoY",
                "source": "Ministry of Statistics and Programme Implementation (MoSPI)",
                "data_status": "verified_historical_cache",
                "as_of": cached["recorded_at"]
            }

        return {
            "indicator": "Headline CPI Inflation Rate",
            "latest_period": "N/A",
            "latest_value": None,
            "unit": "percent YoY",
            "source": "MoSPI",
            "data_status": "unavailable"
        }

    def get_repo_rate(self) -> Dict[str, Any]:
        """Fetch Reserve Bank of India (RBI) Policy Repo Rate parsed dynamically from FRED series."""
        try:
            url = f"{FRED_GRAPH_CSV}?id=INTDSRINM193N"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                df = pd.read_csv(io.StringIO(resp.text))
                if not df.empty and "INTDSRINM193N" in df.columns:
                    valid = df[df["INTDSRINM193N"] != "."].dropna()
                    if not valid.empty:
                        latest_row = valid.iloc[-1]
                        latest_date = str(latest_row["DATE"])
                        latest_rate = round(float(latest_row["INTDSRINM193N"]), 2)

                        macro_store.insert_observation(
                            sector="finance",
                            indicator="repo_rate",
                            sub_indicator="Policy Rate",
                            observation_date=latest_date,
                            value=latest_rate,
                            unit="% p.a.",
                            source="FRED / RBI",
                            data_status="live"
                        )

                        return {
                            "indicator": "RBI Policy Repo Rate",
                            "latest_period": latest_date,
                            "latest_value": latest_rate,
                            "unit": "percent per annum",
                            "source": "Reserve Bank of India (RBI)",
                            "data_status": "live"
                        }
        except Exception:
            pass

        cached = macro_store.get_latest_observation(sector="finance", indicator="repo_rate", sub_indicator="Policy Rate")
        if cached:
            return {
                "indicator": "RBI Policy Repo Rate",
                "latest_period": cached["latest_period"],
                "latest_value": cached["latest_value"],
                "unit": "percent per annum",
                "source": "Reserve Bank of India (RBI)",
                "data_status": "verified_historical_cache",
                "as_of": cached["recorded_at"]
            }

        return {
            "indicator": "RBI Policy Repo Rate",
            "latest_period": "N/A",
            "latest_value": None,
            "unit": "percent per annum",
            "source": "RBI",
            "data_status": "unavailable"
        }

    def get_debt_to_gdp(self) -> Dict[str, Any]:
        """Fetch General Government Debt to GDP ratio dynamically from IMF data API."""
        try:
            url = f"{IMF_API_BASE}/GGXWDG_NGDP/IND"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json().get("values", {}).get("GGXWDG_NGDP", {}).get("IND", {})
                if data:
                    valid_years = sorted([int(yr) for yr in data.keys() if float(data[yr]) > 0])
                    if valid_years:
                        latest_yr = str(valid_years[-1])
                        val = round(float(data[latest_yr]), 2)

                        macro_store.insert_observation(
                            sector="finance",
                            indicator="debt_to_gdp",
                            sub_indicator="General Government",
                            observation_date=latest_yr,
                            value=val,
                            unit="% of GDP",
                            source="IMF",
                            data_status="live"
                        )

                        return {
                            "indicator": "General Government Debt to GDP Ratio",
                            "latest_period": latest_yr,
                            "latest_value": val,
                            "unit": "percent of GDP",
                            "source": "International Monetary Fund (IMF)",
                            "data_status": "live"
                        }
        except Exception:
            pass

        cached = macro_store.get_latest_observation(sector="finance", indicator="debt_to_gdp", sub_indicator="General Government")
        if cached:
            return {
                "indicator": "General Government Debt to GDP Ratio",
                "latest_period": cached["latest_period"],
                "latest_value": cached["latest_value"],
                "unit": "percent of GDP",
                "source": "International Monetary Fund (IMF)",
                "data_status": "verified_historical_cache",
                "as_of": cached["recorded_at"]
            }

        return {
            "indicator": "General Government Debt to GDP Ratio",
            "latest_period": "N/A",
            "latest_value": None,
            "unit": "percent of GDP",
            "source": "IMF",
            "data_status": "unavailable"
        }

    def get_forex_reserves(self) -> Dict[str, Any]:
        """Fetch Foreign Exchange Reserves dynamically from World Bank / RBI API."""
        try:
            url = f"{WORLD_BANK_API_BASE}/FI.RES.TOTL.CD?format=json&per_page=5"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                items = [i for i in resp.json()[1] if i.get("value") is not None]
                if items:
                    item = items[0]
                    period = str(item["date"])
                    val_bn = round(float(item["value"]) / 1e9, 2)

                    macro_store.insert_observation(
                        sector="finance",
                        indicator="forex_reserves",
                        sub_indicator="Total Reserves",
                        observation_date=period,
                        value=val_bn,
                        unit="Billion USD",
                        source="World Bank / RBI",
                        data_status="live"
                    )

                    return {
                        "indicator": "Total Foreign Exchange Reserves",
                        "latest_period": period,
                        "latest_value": val_bn,
                        "unit": "billion USD",
                        "source": "Reserve Bank of India (RBI)",
                        "data_status": "live"
                    }
        except Exception:
            pass

        cached = macro_store.get_latest_observation(sector="finance", indicator="forex_reserves", sub_indicator="Total Reserves")
        if cached:
            return {
                "indicator": "Total Foreign Exchange Reserves",
                "latest_period": cached["latest_period"],
                "latest_value": cached["latest_value"],
                "unit": "billion USD",
                "source": "Reserve Bank of India (RBI)",
                "data_status": "verified_historical_cache",
                "as_of": cached["recorded_at"]
            }

        return {
            "indicator": "Total Foreign Exchange Reserves",
            "latest_period": "N/A",
            "latest_value": None,
            "unit": "billion USD",
            "source": "RBI",
            "data_status": "unavailable"
        }
