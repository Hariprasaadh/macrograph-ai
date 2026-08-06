"""Finance Sector Domain Agents for GDP, Inflation CPI, Repo Rate, Debt-to-GDP, and Forex Reserves."""
from __future__ import annotations

from typing import Any, Optional
from ..clients.finance_data_client import FinanceDataClient
from .base import FinanceAgent
from .response_models import FinanceSectorResponse


class GDPGrowthAgent(FinanceAgent):
    name = "gdp_growth"

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def analyze(self, options: Optional[Any] = None) -> FinanceSectorResponse:
        prices = getattr(options, "prices", "Constant") if options else "Constant"
        gdp_data = self.client.get_gdp_growth(prices=prices)
        val = gdp_data.get("latest_value")
        
        status = "robust" if val is not None and val >= 7.0 else "moderate" if val is not None and val >= 5.0 else "sluggish"
        alerts = []
        if val is not None and val < 5.0:
            alerts.append(f"Real GDP growth is sluggish at {val}%.")
            
        return FinanceSectorResponse(
            agent=self.name,
            assessment=f"Quarterly Real GDP growth is {status} at {val}% YoY in the latest MoSPI reading.",
            indicators={"gdp_growth": gdp_data},
            alerts=alerts,
            source_metadata=[{"source": gdp_data.get("source"), "latest_period": gdp_data.get("latest_period")}]
        )


class CPIInflationAgent(FinanceAgent):
    name = "cpi_inflation"

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def analyze(self, options: Optional[Any] = None) -> FinanceSectorResponse:
        cpi_data = self.client.get_cpi_inflation()
        val = cpi_data.get("latest_value")
        
        status = "elevated" if val is not None and val >= 6.0 else "aligned with target" if val is not None and val <= 4.5 else "moderate"
        alerts = []
        if val is not None and val >= 6.0:
            alerts.append(f"Headline CPI inflation of {val}% exceeds RBI's 6% upper tolerance limit.")
            
        return FinanceSectorResponse(
            agent=self.name,
            assessment=f"Headline CPI inflation is {status} at {val}% YoY.",
            indicators={"cpi_inflation": cpi_data},
            alerts=alerts,
            source_metadata=[{"source": cpi_data.get("source"), "latest_period": cpi_data.get("latest_period")}]
        )


class RepoRateAgent(FinanceAgent):
    name = "repo_rate"

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def analyze(self, options: Optional[Any] = None) -> FinanceSectorResponse:
        repo_data = self.client.get_repo_rate()
        val = repo_data.get("latest_value")
        
        status = "restrictive" if val is not None and val >= 6.5 else "accommodative" if val is not None and val <= 5.0 else "neutral"
        alerts = []
        if val is not None and val >= 6.5:
            alerts.append(f"Repo rate is restrictive at {val}% per annum.")
            
        return FinanceSectorResponse(
            agent=self.name,
            assessment=f"RBI monetary policy stance is {status} with a Repo Rate of {val}%.",
            indicators={"repo_rate": repo_data},
            alerts=alerts,
            source_metadata=[{"source": repo_data.get("source"), "latest_period": repo_data.get("latest_period")}]
        )


class DebtToGDPAgent(FinanceAgent):
    name = "debt_to_gdp"

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def analyze(self, options: Optional[Any] = None) -> FinanceSectorResponse:
        debt_data = self.client.get_debt_to_gdp()
        val = debt_data.get("latest_value")
        
        status = "elevated" if val is not None and val >= 80.0 else "moderate" if val is not None and val >= 60.0 else "low"
        alerts = []
        if val is not None and val >= 80.0:
            alerts.append(f"General Government Debt-to-GDP ratio is elevated at {val}% of GDP.")
            
        return FinanceSectorResponse(
            agent=self.name,
            assessment=f"Fiscal debt exposure is {status} with General Government Debt at {val}% of GDP.",
            indicators={"debt_to_gdp": debt_data},
            alerts=alerts,
            source_metadata=[{"source": debt_data.get("source"), "latest_period": debt_data.get("latest_period")}]
        )


class ForexReservesAgent(FinanceAgent):
    name = "forex_reserves"

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def analyze(self, options: Optional[Any] = None) -> FinanceSectorResponse:
        forex_data = self.client.get_forex_reserves()
        val = forex_data.get("latest_value")
        
        status = "robust" if val is not None and val >= 600.0 else "adequate" if val is not None and val >= 400.0 else "vulnerable"
        alerts = []
        if val is not None and val >= 650.0:
            alerts.append(f"Foreign Exchange Reserves stand at a strong high of ${val} Billion USD.")
            
        return FinanceSectorResponse(
            agent=self.name,
            assessment=f"External sector buffer is {status} with Foreign Exchange Reserves at ${val} Billion USD.",
            indicators={"forex_reserves": forex_data},
            alerts=alerts,
            source_metadata=[{"source": forex_data.get("source"), "latest_period": forex_data.get("latest_period")}]
        )
