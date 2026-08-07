from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from .base import SectorAgent, sources
from .response_models import CapitalMarketsResponse


class PrimaryMarketAgent(SectorAgent):
    name = "primary_market"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> CapitalMarketsResponse:
        primary = data.get("primary_market", pd.DataFrame())
        assessment = "Primary market data is unavailable."
        alerts: list[str] = []
        indicators: dict[str, Any] = {}

        if not primary.empty:
            latest_ipo_count = primary.loc[primary["indicator_name"].str.contains("IPO", case=False, na=False), "value"].iloc[-1]
            latest_debt = primary.loc[primary["indicator_name"].str.contains("Debt", case=False, na=False), "value"].iloc[-1]
            indicators["ipo_count"] = {"latest_value": latest_ipo_count, "source": "NSE"}
            indicators["debt_issuance"] = {"latest_value": latest_debt, "source": "NSE"}
            assessment = f"Latest primary market activity shows {latest_ipo_count} IPOs and {latest_debt} in debt issuance." 
            if latest_ipo_count is not None and latest_ipo_count > 10:
                alerts.append("IPO activity is elevated, suggesting strong primary market demand.")

        return CapitalMarketsResponse(
            agent=self.name,
            assessment=assessment,
            indicators=indicators,
            alerts=alerts,
            source_metadata=sources(primary),
        )
