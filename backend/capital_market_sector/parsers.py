"""Parsers for Capital Markets Sector external responses."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from capital_market_sector.models import (
    Citation,
    DataFreshness,
    GSecYieldRecord,
    IndiaVixRecord,
    MarketBreadthRecord,
    NiftySnapshotRecord,
)

logger = logging.getLogger(__name__)


def safe_float_val(val: Any) -> float | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        cleaned = str(val).replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_market_breadth(payload: Any, citation: Citation) -> MarketBreadthRecord:
    """Normalize the verified NSE MCP `get_market_breadth` response."""
    if not isinstance(payload, dict):
        raise ValueError("NSE MCP market breadth response must be an object.")

    period = payload.get("date")
    if not isinstance(period, str) or not period.strip():
        raise ValueError("NSE MCP market breadth response has no observation date.")

    total_stocks = safe_float_val(payload.get("total_stocks"))
    advances = safe_float_val(payload.get("advances"))
    declines = safe_float_val(payload.get("declines"))
    unchanged = safe_float_val(payload.get("unchanged"))
    ratio = safe_float_val(payload.get("ad_ratio"))
    volume = safe_float_val(payload.get("total_volume"))
    if all(value is None for value in (total_stocks, advances, declines, unchanged, ratio, volume)):
        raise ValueError("NSE MCP market breadth response contains no usable observations.")

    return MarketBreadthRecord(
        period=period.strip(),
        total_stocks=int(total_stocks) if total_stocks is not None else None,
        advances_count=int(advances) if advances is not None else None,
        declines_count=int(declines) if declines is not None else None,
        unchanged_count=int(unchanged) if unchanged is not None else None,
        advance_decline_ratio=ratio,
        total_volume=int(volume) if volume is not None else None,
        citation=citation,
    )


def parse_gsec_yields(
    payload: Any,
    *,
    lookback_months: int = 12,
    citation_factory: Any,
) -> list[GSecYieldRecord]:
    """Parse RBI's monthly SGL transaction yields using tenor-labelled columns."""
    if lookback_months < 1 or not isinstance(payload, dict):
        return []
    columns = payload.get("columns")
    rows = payload.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []
    if not all(isinstance(column, str) for column in columns):
        return []

    formatted_rows = [
        dict(zip(columns, row))
        for row in rows
        if isinstance(row, (list, tuple)) and len(row) == len(columns)
    ]
    new_format_rows = [
        row for row in formatted_rows
        if row.get("tab") == "New Format"
    ]
    maturity_columns: dict[int, str] = {}
    for row in new_format_rows:
        try:
            row_number = int(row.get("row_no"))
        except (TypeError, ValueError):
            continue
        if row_number != 7:
            continue
        for column in columns:
            match = re.fullmatch(r"(\d+)\s+Years?", str(row.get(column) or "").strip())
            if match:
                maturity_columns[int(match.group(1))] = column
        break

    required_tenors = {2, 5, 10}
    if not required_tenors <= maturity_columns.keys():
        raise ValueError("RBI G-Sec yield table does not label all required tenors.")

    records: list[GSecYieldRecord] = []
    for row in new_format_rows:
        try:
            row_number = int(row.get("row_no"))
        except (TypeError, ValueError):
            continue
        if row_number < 8:
            continue
        period_text = str(row.get("c1") or "").strip()
        try:
            period = datetime.strptime(period_text, "%b-%Y").strftime("%Y-%m")
        except ValueError:
            continue

        two_year = safe_float_val(row.get(maturity_columns[2]))
        five_year = safe_float_val(row.get(maturity_columns[5]))
        ten_year = safe_float_val(row.get(maturity_columns[10]))
        if all(value is None for value in (two_year, five_year, ten_year)):
            continue
        spread = (
            round((ten_year - two_year) * 100, 4)
            if ten_year is not None and two_year is not None
            else None
        )
        records.append(
            GSecYieldRecord(
                period=period,
                ten_year_gsec_yield_pct=ten_year,
                five_year_gsec_yield_pct=five_year,
                two_year_gsec_yield_pct=two_year,
                yield_curve_spread_2s10s_bps=spread,
                citation=citation_factory(period),
            )
        )

    records.sort(key=lambda record: record.period, reverse=True)
    return records[:lookback_months]
