from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..ingest.xlsx_reader import read_xlsx_rows
from .common import frame, number, row_record


def _quarter_date(year_label: str, quarter: str) -> str | None:
    if not (len(year_label) >= 4 and year_label[:4].isdigit()):
        return None
    mapping = {"Q1": (0, 6), "Q2": (0, 9), "Q3": (0, 12), "Q4": (1, 3)}
    if quarter not in mapping:
        return None
    offset, month = mapping[quarter]
    return f"{int(year_label[:4]) + offset:04d}-{month:02d}-01"


def _quarterly(path: Path, price_basis: str) -> pd.DataFrame:
    rows = read_xlsx_rows(path)
    header_at = next(i for i, row in enumerate(rows) if any("Gross Domestic Product" in str(v) for v in row) and any(str(v).strip() == "Quarter" for v in row))
    headers, active_year, records = rows[header_at], "", []
    for row in rows[header_at + 2:]:
        if len(row) > 1 and str(row[1]).strip():
            active_year = str(row[1]).strip()
        period = _quarter_date(active_year, str(row[2] if len(row) > 2 else "").strip())
        if not period:
            continue
        for column in range(3, min(len(row), len(headers))):
            value = number(row[column])
            if value is not None:
                records.append(row_record(sector="national_income", subsector=price_basis,
                    indicator_name=str(headers[column]).strip(), date=period, value=value,
                    unit="INR crore", frequency="quarterly", source=path.name))
    return frame(records)


def clean_income(data_dir: Path) -> dict[str, pd.DataFrame]:
    folder = data_dir / "Income"
    constant = _quarterly(next(folder.glob("Quarterly Estimates*Constant*.xlsx")), "constant prices (2022-23)")
    current = _quarterly(next(folder.glob("Quarterly Estimates*Current*.xlsx")), "current prices (2022-23)")
    return {"gdp_quarterly": pd.concat([constant, current], ignore_index=True)}
