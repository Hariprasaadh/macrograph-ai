from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from ..config import MONTH_NUMBERS
from ..ingest.xlsx_reader import read_xlsx_rows
from .common import frame, number, row_record


def _month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"


def _annual_cpi(path: Path) -> pd.DataFrame:
    rows, records, series = read_xlsx_rows(path), [], "CPI annual variation"
    for index, row in enumerate(rows):
        first = str(row[1] if len(row) > 1 else "").strip()
        if first and "CPI" in first and "Year/ Month" not in first:
            series = first
        if first != "Year/ Month":
            continue
        for data_row in rows[index + 2:]:
            year_label = str(data_row[1] if len(data_row) > 1 else "").strip()
            found = re.match(r"(\d{4})\s*-", year_label)
            if not found:
                break
            start = int(found.group(1))
            for column, month_name in enumerate(row[2:14], 2):
                month, value = MONTH_NUMBERS.get(str(month_name).strip(". ").upper()), number(data_row[column] if column < len(data_row) else None)
                if month and value is not None:
                    records.append(row_record(sector="prices", subsector="CPI", indicator_name=series,
                        date=_month(start if month >= 4 else start + 1, month), value=value,
                        unit="percent YoY inflation", frequency="monthly", source=path.name))
    return frame(records)


def _core_cpi(path: Path) -> pd.DataFrame:
    records = []
    for row in read_xlsx_rows(path)[6:]:
        found = re.match(r"([A-Z]{3})-(\d{4})", str(row[1] if len(row) > 1 else "").strip())
        value = number(row[7] if len(row) > 7 else None)
        if found and value is not None:
            records.append(row_record(sector="prices", subsector="CPI",
                indicator_name="Core CPI excluding food and fuel — Combined",
                date=_month(int(found.group(2)), MONTH_NUMBERS[found.group(1)]), value=value,
                unit="percent YoY inflation", frequency="monthly", source=path.name))
    return frame(records)


def _house_prices(path: Path) -> pd.DataFrame:
    rows, records = read_xlsx_rows(path), []
    headers = rows[5]
    for row in rows[6:]:
        found = re.match(r"Q([1-4])\.(\d{4})-\d{2}", str(row[1] if len(row) > 1 else "").strip())
        if not found:
            continue
        quarter, start = int(found.group(1)), int(found.group(2))
        month, year = {1: (6, start), 2: (9, start), 3: (12, start), 4: (3, start + 1)}[quarter]
        for column in range(2, min(len(row), len(headers))):
            city, value = str(headers[column]).strip(), number(row[column])
            if city and value is not None:
                records.append(row_record(sector="prices", subsector="housing", indicator_name="House price index",
                    date=_month(year, month), region_state=city, value=value,
                    unit="index (base 2008-09=100)", frequency="quarterly", source=path.name))
    return frame(records)


def _wpi(path: Path) -> pd.DataFrame:
    rows, records = read_xlsx_rows(path), []
    # The workbook starts with title/base-year spacer rows; its paired date/status
    # columns are rows 5 and 6 in the parsed sheet (zero-based indexes 5 and 6).
    dates, statuses = rows[5], rows[6]
    for row in rows[7:]:
        commodity = str(row[1] if len(row) > 1 else "").strip()
        if not commodity:
            continue
        for column in range(3, min(len(row), len(dates))):
            if str(statuses[column]).strip().lower() != "final":
                continue
            found = re.match(r"([A-Za-z]{3})-(\d{4})", str(dates[column]).strip())
            value = number(row[column])
            if found and value is not None:
                records.append(row_record(sector="prices", subsector="WPI", indicator_name=commodity,
                    date=_month(int(found.group(2)), MONTH_NUMBERS[found.group(1).upper()]), value=value,
                    unit="percent YoY inflation", frequency="monthly", source=path.name))
    return frame(records)


def clean_prices(data_dir: Path) -> dict[str, pd.DataFrame]:
    folder = data_dir / "Prices"
    cpi = _annual_cpi(next(folder.glob("Consumer Price Index - Annual*.xlsx")))
    cpi = pd.concat([cpi, _core_cpi(next(folder.glob("RBIB Table*.xlsx")))], ignore_index=True)
    return {"cpi_combined": cpi,
            "wpi_monthly": _wpi(next(folder.glob("Wholesale Price*.xlsx"))),
            "house_price_index": _house_prices(next(folder.glob("House Price*.xlsx")))}
