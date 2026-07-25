from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from ..ingest.xlsx_reader import read_xlsx_rows
from .common import financial_year_end, frame, number, row_record


def _annual_wide(path: Path, prefix: str, unit: str, subsector: str) -> pd.DataFrame:
    rows = read_xlsx_rows(path)
    header_at = next(i for i, row in enumerate(rows) if len(row) > 1 and str(row[1]).strip() == "Year")
    headers, records = rows[header_at], []
    for row in rows[header_at + 2:]:
        period = financial_year_end(row[1] if len(row) > 1 else "")
        if not period:
            continue
        for column in range(2, min(len(row), len(headers))):
            value, label = number(row[column]), str(headers[column]).strip()
            if value is not None and label:
                records.append(row_record(sector="agriculture", subsector=subsector,
                    indicator_name=f"{prefix} — {label}", date=period, value=value, unit=unit,
                    frequency="yearly", source=path.name))
    return frame(records)


def clean_agriculture(data_dir: Path) -> dict[str, pd.DataFrame]:
    folder = data_dir / "Agri"
    return {
        "agri_production": _annual_wide(next(folder.glob("Agricultural Production*.xlsx")), "Foodgrain production", "lakh tonnes", "foodgrains"),
        "agri_yield": _annual_wide(next(folder.glob("Yield Per Hectare*.xlsx")), "Foodgrain yield", "kg/hectare", "foodgrains"),
        "agri_msp": _annual_wide(next(folder.glob("Minimum Support Price*.xlsx")), "Minimum support price", "INR/quintal", "MSP"),
    }
