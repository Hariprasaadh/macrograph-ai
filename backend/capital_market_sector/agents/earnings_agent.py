from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from .base import SectorAgent, sources
from .response_models import CapitalMarketsResponse


class EarningsAgent(SectorAgent):
    name = "earnings"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> CapitalMarketsResponse:
        earnings = data.get("corporate_earnings", pd.DataFrame())
        assessment = "Corporate earnings data is unavailable."
        alerts: list[str] = []
        indicators: dict[str, Any] = {}

        if not earnings.empty:
            latest_eps = earnings.loc[earnings["indicator_name"].str.contains("EPS", case=False, na=False), "value"].iloc[-1]
            latest_pat = earnings.loc[earnings["indicator_name"].str.contains("PAT", case=False, na=False), "value"].iloc[-1]
            indicators["latest_eps"] = {"latest_value": latest_eps, "source": "NSE"}
            indicators["latest_pat"] = {"latest_value": latest_pat, "source": "NSE"}
            assessment = f"Latest aggregate EPS is {latest_eps} and PAT is {latest_pat}."
            if latest_eps is not None and latest_eps < 0:
                alerts.append("Aggregate EPS is negative, signaling earnings pressure.")

        return CapitalMarketsResponse(
            agent=self.name,
            assessment=assessment,
            indicators=indicators,
            alerts=alerts,
            source_metadata=sources(earnings),
        )
