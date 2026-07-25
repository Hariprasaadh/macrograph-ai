from __future__ import annotations

import pandas as pd


def series_summary(frame: pd.DataFrame, contains: str | None = None, *, aggregate: str = "mean") -> dict[str, float | str | None]:
    """Return latest value and changes for a normalized indicator selection."""
    subset = frame.copy()
    if contains:
        subset = subset[subset["indicator_name"].str.contains(contains, case=False, regex=False, na=False)]
    if subset.empty:
        return {"latest_date": None, "latest_value": None, "period_change_pct": None, "year_change_pct": None}
    grouped = subset.groupby("date", as_index=False)["value"].agg(aggregate).sort_values("date")
    latest = grouped.iloc[-1]
    previous = grouped.iloc[-2] if len(grouped) > 1 else None
    twelve_back = grouped.iloc[-13] if len(grouped) >= 13 else (grouped.iloc[-5] if len(grouped) >= 5 else None)
    def change(base: float | None) -> float | None:
        if base is None or base == 0:
            return None
        return round((float(latest.value) / base - 1) * 100, 2)
    return {
        "latest_date": latest.date.date().isoformat(), "latest_value": round(float(latest.value), 2),
        "period_change_pct": change(None if previous is None else float(previous.value)),
        "year_change_pct": change(None if twelve_back is None else float(twelve_back.value)),
    }


def direct_growth_summary(frame: pd.DataFrame, contains: str | None = None) -> dict[str, float | str | None]:
    """Return latest source-supplied growth rate and its movement."""
    result = series_summary(frame, contains)
    if result["latest_value"] is not None:
        result["latest_growth_pct"] = result.pop("latest_value")
    else:
        result["latest_growth_pct"] = None
    return result
