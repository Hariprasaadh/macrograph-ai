from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from ..config import MONTH_NUMBERS
from ..ingest.xlsx_reader import read_xlsx_rows
from .common import financial_year_end, frame, number, row_record


def _month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"


def _iip_growth(path: Path) -> pd.DataFrame:
    rows = read_xlsx_rows(path)
    header_at = next(i for i, row in enumerate(rows) if any("Item Description" in str(v) for v in row))
    headers, records = rows[header_at], []
    for row in rows[header_at + 1:]:
        label = str(row[1] if len(row) > 1 else "").strip()
        if not label:
            continue
        for column, header in enumerate(headers[2:], 2):
            found, value = re.search(r"(\d{4}):(\d{2})", str(header)), number(row[column] if column < len(row) else None)
            if found and value is not None:
                records.append(row_record(sector="industry", subsector="IIP use-based", indicator_name=label,
                    date=_month(int(found.group(1)), int(found.group(2))), value=value,
                    unit="percent YoY growth", frequency="monthly", source=path.name))
    return frame(records)


def _manufacturing(path: Path) -> pd.DataFrame:
    rows, records, group = read_xlsx_rows(path), [], "Manufacturing"
    for index, row in enumerate(rows):
        first = str(row[1] if len(row) > 1 else "").strip()
        if re.match(r"^\d+\.\s", first):
            group = re.sub(r"\s*\(.*", "", first)
        if first != "Year/Month":
            continue
        for data_row in rows[index + 1:]:
            year_label = str(data_row[1] if len(data_row) > 1 else "").strip()
            if not financial_year_end(year_label):
                break
            start_year = int(year_label[:4])
            for column, month_name in enumerate(row[2:], 2):
                month, value = MONTH_NUMBERS.get(str(month_name).strip().upper()), number(data_row[column] if column < len(data_row) else None)
                if month and value is not None:
                    records.append(row_record(sector="industry", subsector="manufacturing", indicator_name=group,
                        date=_month(start_year if month >= 4 else start_year + 1, month), value=value,
                        unit="index (base 2022-23=100)", frequency="monthly", source=path.name))
    return frame(records)


def clean_industry(data_dir: Path) -> dict[str, pd.DataFrame]:
    folder = data_dir / "Ind"
    return {"industry_iip": _iip_growth(next(folder.glob("Index of Industrial Production*.xlsx"))),
            "industry_manufacturing": _manufacturing(next(folder.glob("Index Numbers*.xlsx")))}
