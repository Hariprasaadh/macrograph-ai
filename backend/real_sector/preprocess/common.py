from __future__ import annotations

from datetime import date
import math
import re
from typing import Any, Iterable

import pandas as pd

COMMON_COLUMNS = ["sector", "subsector", "indicator_name", "date", "region_state", "value", "unit", "frequency", "source", "notes"]


def text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def number(value: Any) -> float | None:
    cleaned = text(value).replace(",", "")
    if cleaned.lower() in {"", "-", "na", "n/a", ".."}:
        return None
    try:
        result = float(cleaned)
        return None if math.isnan(result) else result
    except ValueError:
        return None


def financial_year_end(value: Any) -> str | None:
    found = re.search(r"(\d{4})\s*-\s*\d{2,4}", text(value))
    return None if not found else date(int(found.group(1)) + 1, 3, 1).isoformat()


def row_record(**values: Any) -> dict[str, Any]:
    return {"region_state": "All India", "notes": "", **values}


def frame(records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    result = pd.DataFrame.from_records(records, columns=COMMON_COLUMNS)
    if result.empty:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result = result.dropna(subset=["date", "value"]).drop_duplicates(
        subset=["sector", "subsector", "indicator_name", "date", "region_state"], keep="last"
    )
    return result.sort_values(["indicator_name", "date"]).reset_index(drop=True)
