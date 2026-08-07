from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from .base import SectorAgent, sources
from .response_models import CapitalMarketsResponse


class MFFlowsAgent(SectorAgent):
    name = "mf_flows"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> CapitalMarketsResponse:
        flows = data.get("mf_flows", pd.DataFrame())
        assessment = "Mutual fund flows data is unavailable."
        alerts: list[str] = []
        indicators: dict[str, Any] = {}

        if not flows.empty:
            latest_equity_flow = flows.loc[flows["indicator_name"].str.contains("Equity", case=False, na=False), "value"].iloc[-1]
            latest_dii = flows.loc[flows["indicator_name"].str.contains("DII", case=False, na=False), "value"].iloc[-1]
            indicators["equity_net_flow"] = {"latest_value": latest_equity_flow, "source": "AMFI"}
            indicators["dii_net_purchase"] = {"latest_value": latest_dii, "source": "AMFI"}
            assessment = f"Latest flows show equity net flow of {latest_equity_flow} and DII net purchase of {latest_dii}."
            if latest_dii is not None and latest_dii > 0:
                alerts.append("DII net purchase remains positive, supporting domestic institutional demand.")

        return CapitalMarketsResponse(
            agent=self.name,
            assessment=assessment,
            indicators=indicators,
            alerts=alerts,
            source_metadata=sources(flows),
        )
