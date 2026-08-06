from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from ..features.utils import series_summary
from .base import SectorAgent, sources
from .response_models import SectorResponse


class AgricultureAgent(SectorAgent):
    name = "agriculture"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> SectorResponse:
        start_date = getattr(options, "start_date", None) if options else None
        end_date = getattr(options, "end_date", None) if options else None

        production, yield_data, msp = data["agri_production"], data["agri_yield"], data["agri_msp"]
        production_metric = series_summary(production, "Total Foodgrains", start_date=start_date, end_date=end_date)
        yield_metric = series_summary(yield_data, "Total Foodgrains", start_date=start_date, end_date=end_date)
        msp_metric = series_summary(msp, start_date=start_date, end_date=end_date)
        
        production_change = production_metric["period_change_pct"]
        msp_change = msp_metric["period_change_pct"]
        risk = "high" if (production_change is not None and production_change < 0 and msp_change is not None and msp_change > 0) else "moderate" if production_change is not None and production_change < 0 else "low"
        
        alerts = []
        if production_change is not None and production_change < 0:
            alerts.append(f"Foodgrain production declined {abs(production_change):.2f}% in the latest annual comparison.")
        if msp_change is not None and msp_change > 5:
            alerts.append(f"Average observed MSP rose {msp_change:.2f}% in the latest annual comparison.")
            
        return SectorResponse(
            agent=self.name,
            assessment=f"Food-inflation supply risk is {risk} based on production, yield, and MSP signals.",
            indicators={"production": production_metric, "yield": yield_metric, "msp": msp_metric},
            alerts=alerts,
            source_metadata=sources(production, yield_data, msp)
        )
