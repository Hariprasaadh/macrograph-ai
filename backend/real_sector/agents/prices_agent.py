from __future__ import annotations

from typing import Mapping
import pandas as pd

from ..features.utils import direct_growth_summary, series_summary
from .base import SectorAgent, sources
from .response_models import SectorResponse


class PricesAgent(SectorAgent):
    name = "prices"

    def analyze(self, data: Mapping[str, pd.DataFrame]) -> SectorResponse:
        cpi, wpi, houses = data["cpi_combined"], data["wpi_monthly"], data["house_price_index"]
        headline = direct_growth_summary(cpi, "All India General Index")
        core = direct_growth_summary(cpi, "Core CPI")
        food = direct_growth_summary(cpi, "Food")
        wpi_metric = direct_growth_summary(wpi, "ALL COMMODITIES")
        housing = series_summary(houses)
        inflation = headline["latest_growth_pct"]
        assessment = "elevated" if inflation is not None and inflation >= 5 else "contained" if inflation is not None else "not available in the supplied CPI series"
        alerts = []
        if food["latest_growth_pct"] is not None and headline["latest_growth_pct"] is not None and food["latest_growth_pct"] > headline["latest_growth_pct"]:
            alerts.append("Food CPI is above headline CPI in the latest supplied reading.")
        return SectorResponse(agent=self.name, assessment=f"Consumer-price inflation is {assessment} in the latest matching source observation.",
            indicators={"headline_cpi": headline, "food_cpi": food, "core_cpi": core, "wpi": wpi_metric, "house_price_index": housing},
            alerts=alerts, source_metadata=sources(cpi, wpi, houses))
