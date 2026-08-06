from __future__ import annotations

from typing import Mapping, Optional
import pandas as pd


def sources(*frames: pd.DataFrame) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for frame in frames:
        if frame.empty:
            continue
        for source in frame["source"].dropna().unique():
            values.append({
                "source": str(source),
                "observations": int((frame["source"] == source).sum()),
                "latest_date": frame.loc[frame["source"] == source, "date"].max().date().isoformat()
            })
    return values


class SectorAgent:
    name = "sector"

    def analyze(self, data: Mapping[str, pd.DataFrame], options: Optional[Any] = None):  # pragma: no cover
        raise NotImplementedError
