from __future__ import annotations

from typing import Optional
import pandas as pd


def series_summary(
    frame: pd.DataFrame,
    contains: Optional[str] = None,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    aggregate: str = "mean"
) -> dict[str, float | str | None]:
    """Return latest value, YoY change, period change, and trend direction for a selection."""
    subset = frame.copy()
    if contains:
        subset = subset[subset["indicator_name"].str.contains(contains, case=False, regex=False, na=False)]
    
    if start_date:
        subset = subset[subset["date"] >= pd.to_datetime(start_date)]
    if end_date:
        subset = subset[subset["date"] <= pd.to_datetime(end_date)]

    if subset.empty:
        return {
            "latest_date": None,
            "latest_value": None,
            "period_change_pct": None,
            "year_change_pct": None,
            "three_period_avg": None,
            "trend": None
        }

    grouped = subset.groupby("date", as_index=False)["value"].agg(aggregate).sort_values("date")
    if grouped.empty:
        return {
            "latest_date": None,
            "latest_value": None,
            "period_change_pct": None,
            "year_change_pct": None,
            "three_period_avg": None,
            "trend": None
        }

    latest = grouped.iloc[-1]
    previous = grouped.iloc[-2] if len(grouped) > 1 else None

    # Determine frequency for accurate 1-Year-Ago (YoY) calculation
    freq_values = subset["frequency"].dropna().unique() if "frequency" in subset.columns else []
    frequency = str(freq_values[0]).lower() if len(freq_values) > 0 else "monthly"

    if "quarter" in frequency or "quarterly" in frequency:
        year_back_offset = -5  # 4 quarters ago
    elif "annual" in frequency or "yearly" in frequency:
        year_back_offset = -2  # 1 year ago
    else:
        year_back_offset = -13  # 12 months ago

    year_back = grouped.iloc[year_back_offset] if len(grouped) >= abs(year_back_offset) else None

    def change(base: float | None) -> float | None:
        if base is None or base == 0:
            return None
        return round((float(latest.value) / base - 1) * 100, 2)

    # 3-period moving average
    three_avg = round(float(grouped.tail(3)["value"].mean()), 2) if len(grouped) >= 3 else None

    # Determine trend (accelerating, decelerating, or stable)
    period_change = change(None if previous is None else float(previous.value))
    if period_change is not None:
        if period_change > 1.0:
            trend = "accelerating"
        elif period_change < -1.0:
            trend = "decelerating"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {
        "latest_date": latest.date.date().isoformat(),
        "latest_value": round(float(latest.value), 2),
        "period_change_pct": period_change,
        "year_change_pct": change(None if year_back is None else float(year_back.value)),
        "three_period_avg": three_avg,
        "trend": trend
    }


def direct_growth_summary(
    frame: pd.DataFrame,
    contains: Optional[str] = None,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict[str, float | str | None]:
    """Return latest source-supplied growth rate and its movement."""
    result = series_summary(frame, contains, start_date=start_date, end_date=end_date)
    if result["latest_value"] is not None:
        result["latest_growth_pct"] = result.pop("latest_value")
    else:
        result["latest_growth_pct"] = None
    return result
