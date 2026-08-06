from __future__ import annotations

from typing import Any, Mapping, Optional
import pandas as pd

from ..features.utils import direct_growth_summary, series_summary
from .base import SectorAgent, sources
from .response_models import SectorResponse


class IndustryAgent(SectorAgent):
    name = "industry"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None) -> SectorResponse:
        start_date = getattr(options, "start_date", None) if options else None
        end_date = getattr(options, "end_date", None) if options else None

        iip, manufacturing = data["industry_iip"], data["industry_manufacturing"]
        iip_metric = direct_growth_summary(iip, start_date=start_date, end_date=end_date)
        manufacturing_metric = series_summary(manufacturing, start_date=start_date, end_date=end_date)
        
        growth = iip_metric["latest_growth_pct"]
        health = "contracting" if growth is not None and growth < 0 else "expanding" if growth is not None and growth >= 4 else "soft"
        alerts = [] if health == "expanding" else [f"Latest reported IIP use-based growth is {growth:.2f}%."] if growth is not None else []
        
        return SectorResponse(
            agent=self.name,
            assessment=f"Industrial activity is {health} in the latest available IIP reading.",
            indicators={"iip_growth": iip_metric, "manufacturing_index": manufacturing_metric},
            alerts=alerts,
            source_metadata=sources(iip, manufacturing)
        )
