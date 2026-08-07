from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from .base import SectorAgent, sources
from .response_models import CapitalMarketsResponse


class VixAgent(SectorAgent):
    name = "vix"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> CapitalMarketsResponse:
        vix = data.get("india_vix", pd.DataFrame())
        latest_value = vix["value"].iloc[-1] if not vix.empty else None

        assessment = "India VIX data is unavailable."
        alerts: list[str] = []
        indicators: dict[str, Any] = {}

        if not vix.empty:
            indicators["india_vix"] = {
                "latest_value": latest_value,
                "latest_date": str(vix["date"].iloc[-1]),
                "source": "NSE",
            }
            if latest_value is not None:
                if latest_value > 25:
                    alerts.append("India VIX is elevated, suggesting heightened market volatility.")
                    assessment = "India VIX is elevated, indicating market volatility is high."
                else:
                    assessment = "India VIX is in a normal range."

        return CapitalMarketsResponse(
            agent=self.name,
            assessment=assessment,
            indicators=indicators,
            alerts=alerts,
            source_metadata=sources(vix),
        )
