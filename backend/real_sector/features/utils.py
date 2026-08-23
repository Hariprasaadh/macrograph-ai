"""Statistical feature extraction utilities for macroeconomic time series."""
from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats


def series_summary(
    frame: pd.DataFrame,
    contains: Optional[str] = None,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    aggregate: str = "mean"
) -> dict[str, float | str | None]:
    """Return latest value, YoY change, period change, rolling Z-score, and historical percentile ranking."""
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
            "trend": None,
            "z_score": None,
            "percentile_rank": None
        }

    grouped = subset.groupby("date", as_index=False)["value"].agg(aggregate).sort_values("date")
    if grouped.empty:
        return {
            "latest_date": None,
            "latest_value": None,
            "period_change_pct": None,
            "year_change_pct": None,
            "three_period_avg": None,
            "trend": None,
            "z_score": None,
            "percentile_rank": None
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

    # Determine trend
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

    # Statistical distribution (Z-score & Percentile rank over historical series)
    vals = grouped["value"].dropna().values
    if len(vals) >= 5 and np.std(vals) > 0:
        latest_val = float(latest.value)
        z_score = round(float((latest_val - np.mean(vals)) / np.std(vals)), 2)
        pct_rank = round(float(stats.percentileofscore(vals, latest_val)), 1)
    else:
        z_score = None
        pct_rank = None

    return {
        "latest_date": str(latest.date)[:10],
        "latest_value": round(float(latest.value), 2),
        "period_change_pct": period_change,
        "year_change_pct": change(None if year_back is None else float(year_back.value)),
        "three_period_avg": three_avg,
        "trend": trend,
        "z_score": z_score,
        "percentile_rank": pct_rank
    }


def direct_growth_summary(
    frame: pd.DataFrame,
    contains: Optional[str] = None,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict[str, float | str | None]:
    """Return latest source-supplied growth rate with statistical percentile rankings."""
    result = series_summary(frame, contains, start_date=start_date, end_date=end_date)
    if result["latest_value"] is not None:
        result["latest_growth_pct"] = result.pop("latest_value")
    else:
        result["latest_growth_pct"] = None
    return result
