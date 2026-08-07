from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from .base import SectorAgent, sources
from .response_models import CapitalMarketsResponse


class EquityAgent(SectorAgent):
    name = "equity"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> CapitalMarketsResponse:
        nifty = data.get("nifty_50", pd.DataFrame())
        sensex = data.get("sensex", pd.DataFrame())

        latest_nifty = nifty["value"].iloc[-1] if not nifty.empty else None
        latest_sensex = sensex["value"].iloc[-1] if not sensex.empty else None

        assessment = "Equity market indices are not available."
        indicators: dict[str, Any] = {}
        alerts: list[str] = []

        if not nifty.empty:
            indicators["nifty_50"] = {
                "latest_value": latest_nifty,
                "latest_date": str(nifty["date"].iloc[-1]),
                "source": "NSE",
            }

        if not sensex.empty:
            indicators["sensex"] = {
                "latest_value": latest_sensex,
                "latest_date": str(sensex["date"].iloc[-1]),
                "source": "NSE",
            }

        if latest_nifty is not None and latest_sensex is not None:
            assessment = f"NIFTY 50 is at {latest_nifty} and SENSEX is at {latest_sensex}."
        elif latest_nifty is not None:
            assessment = f"NIFTY 50 is at {latest_nifty}."
        elif latest_sensex is not None:
            assessment = f"SENSEX is at {latest_sensex}."

        return CapitalMarketsResponse(
            agent=self.name,
            assessment=assessment,
            indicators=indicators,
            alerts=alerts,
            source_metadata=sources(nifty, sensex),
        )
