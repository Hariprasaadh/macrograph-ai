from __future__ import annotations

from typing import Mapping
import pandas as pd

from ..features.utils import series_summary
from .base import SectorAgent, sources
from .response_models import SectorResponse


class NationalIncomeAgent(SectorAgent):
    name = "national_income"

    def analyze(self, data: Mapping[str, pd.DataFrame]) -> SectorResponse:
        gdp = data["gdp_quarterly"]
        real_gdp = gdp[gdp["subsector"].str.contains("constant prices", case=False, na=False)]
        current_gdp = gdp[gdp["subsector"].str.contains("current prices", case=False, na=False)]
        real_metric = series_summary(real_gdp, "Gross Domestic Product")
        gfcf_metric = series_summary(real_gdp, "GFCF")
        nominal_metric = series_summary(current_gdp, "Gross Domestic Product")
        growth = real_metric["year_change_pct"]
        signal = "slowing" if growth is not None and growth < 4 else "growing" if growth is not None else "insufficient data"
        alerts = []
        if real_metric["period_change_pct"] is not None and real_metric["period_change_pct"] < 0:
            alerts.append(f"Real GDP fell {abs(real_metric['period_change_pct']):.2f}% from the prior quarter.")
        return SectorResponse(agent=self.name, assessment=f"Real GDP is {signal} in the latest available quarterly data.",
            indicators={"real_gdp": real_metric, "nominal_gdp": nominal_metric, "gross_fixed_capital_formation": gfcf_metric},
            alerts=alerts, source_metadata=sources(gdp))
