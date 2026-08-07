from __future__ import annotations

from typing import Mapping, Optional
import pandas as pd


def sources(*frames: pd.DataFrame) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for frame in frames:
        if frame.empty or "source" not in frame.columns:
            continue
        for source in frame["source"].dropna().unique():
            latest_dt = frame.loc[frame["source"] == source, "date"].max()
            iso_date = latest_dt.date().isoformat() if hasattr(latest_dt, "date") else str(latest_dt)[:10]
            values.append({
                "source": str(source),
                "observations": int((frame["source"] == source).sum()),
                "latest_date": iso_date,
            })
    return values


class SectorAgent:
    name = "sector"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None):
        raise NotImplementedError
