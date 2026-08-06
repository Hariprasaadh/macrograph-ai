"""Finance Sector Service for data aggregation and pre-processing."""
from __future__ import annotations

from typing import Any, Dict, Optional
from ..clients.finance_data_client import FinanceDataClient


class FinanceSectorService:
    """Service layer coordinating Finance Sector data fetching, caching, and preprocessing."""

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()

    def get_all_indicators(self) -> Dict[str, Any]:
        """Fetches and normalizes all 5 core Finance Sector indicators."""
        return {
            "gdp_growth": self.client.get_gdp_growth(),
            "cpi_inflation": self.client.get_cpi_inflation(),
            "repo_rate": self.client.get_repo_rate(),
            "debt_to_gdp": self.client.get_debt_to_gdp(),
            "forex_reserves": self.client.get_forex_reserves(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "service": "FinanceSectorService",
            "active_indicators": ["gdp_growth", "cpi_inflation", "repo_rate", "debt_to_gdp", "forex_reserves"],
            "status": "operational"
        }
