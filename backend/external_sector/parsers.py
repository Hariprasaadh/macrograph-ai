"""Parsers for External Sector JSON payloads."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from external_sector.models import (
    Citation,
    DataFreshness,
    ExchangeRateRecord,
    ForexReservesRecord,
    TradeBalanceRecord,
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


def parse_forex_reserves(payload: dict[str, Any], lookback_limit: int = 12) -> list[ForexReservesRecord]:
    data = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        data = []

    records: list[ForexReservesRecord] = []
    for item in data[:lookback_limit]:
        if not isinstance(item, dict):
            continue

        period = str(item.get("weekEnded") or item.get("period") or "unknown")
        total_usd = safe_float_val(item.get("totalReservesUSD"))
        total_inr = safe_float_val(item.get("totalReservesINR"))

        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI)",
            document_title="RBI Foreign Exchange Reserves - Weekly Statistical Supplement",
            table_reference="external_sector.r540_forex_reserves",
            retrieval_url="https://dbie.rbihub.in/data/forex-reserves.json",
            observation_period=period,
            freshness=DataFreshness.LIVE,
        )

        records.append(
            ForexReservesRecord(
                period=period,
                total_reserves_usd_mn=total_usd,
                total_reserves_inr_cr=total_inr,
                foreign_currency_assets_usd_mn=safe_float_val(item.get("foreignCurrencyUSD")),
                gold_reserves_usd_mn=safe_float_val(item.get("goldUSD")),
                sdrs_usd_mn=safe_float_val(item.get("sdrsUSD")),
                reserve_tranche_position_usd_mn=safe_float_val(item.get("rtpUSD")),
                citation=citation,
            )
        )

    return records


def _dbie_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    columns = payload.get("columns")
    rows = payload.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []
    if not all(isinstance(column, str) for column in columns):
        return []
    return [
        dict(zip(columns, row))
        for row in rows
        if isinstance(row, (list, tuple)) and len(row) == len(columns)
    ]


def _trade_period(fiscal_year: Any, month: Any) -> str | None:
    fiscal_year_text = str(fiscal_year or "").strip()
    month_text = str(month or "").strip().casefold()
    year_match = re.search(r"\b(\d{4})\b", fiscal_year_text)
    month_numbers = {
        name.casefold(): number
        for number, name in enumerate(
            ("January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"),
            start=1,
        )
    }
    month_number = month_numbers.get(month_text)
    if year_match is None or month_number is None:
        return None

    year = int(year_match.group(1))
    if month_number <= 3:
        year += 1
    return f"{year:04d}-{month_number:02d}"


def parse_trade_balance(
    payload: Any,
    lookback_limit: int = 12,
) -> list[TradeBalanceRecord]:
    """Parse RBI DBIE's monthly merchandise trade table (US$ Millions)."""
    if lookback_limit < 1:
        return []
    table_reference = "external_sector.r433_india_s_foreign_trade_us_dollars"
    retrieval_url = (
        "https://data-api.dbie.rbihub.in/api/tables/"
        "external_sector/r433_india_s_foreign_trade_us_dollars/rows"
    )
    records: list[TradeBalanceRecord] = []
    for row in _dbie_rows(payload):
        period = _trade_period(row.get("c1"), row.get("c2"))
        if period is None:
            continue

        exports_usd_mn = safe_float_val(row.get("c3"))
        imports_usd_mn = safe_float_val(row.get("c4"))
        trade_balance_usd_mn = safe_float_val(row.get("c5"))
        if all(value is None for value in (exports_usd_mn, imports_usd_mn, trade_balance_usd_mn)):
            continue

        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
            document_title="India's Foreign Trade - US Dollars",
            table_reference=table_reference,
            retrieval_url=retrieval_url,
            observation_period=period,
            freshness=DataFreshness.LIVE,
        )
        records.append(
            TradeBalanceRecord(
                period=period,
                exports_usd_bn=exports_usd_mn / 1000 if exports_usd_mn is not None else None,
                imports_usd_bn=imports_usd_mn / 1000 if imports_usd_mn is not None else None,
                trade_balance_usd_bn=(
                    trade_balance_usd_mn / 1000 if trade_balance_usd_mn is not None else None
                ),
                citation=citation,
            )
        )
        if len(records) >= lookback_limit:
            break

    records.sort(key=lambda record: record.period, reverse=True)
    return records


def parse_exchange_rates(
    payload: Any,
    lookback_limit: int = 276,
) -> list[ExchangeRateRecord]:
    """Parse RBI DBIE daily exchange rates, expressed as rupees per USD."""
    if lookback_limit < 1:
        return []
    table_reference = "external_sector.r575_exchange_rate"
    retrieval_url = (
        "https://data-api.dbie.rbihub.in/api/tables/"
        "external_sector/r575_exchange_rate/rows"
    )
    records: list[ExchangeRateRecord] = []
    for row in _dbie_rows(payload):
        source_date = str(row.get("c1") or "").strip()
        usd_inr_rate = safe_float_val(row.get("c2"))
        if not source_date or usd_inr_rate is None:
            continue
        try:
            date_text = datetime.strptime(source_date, "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
            document_title="Daily Exchange Rate of the Indian Rupee",
            table_reference=table_reference,
            retrieval_url=retrieval_url,
            observation_period=date_text,
            freshness=DataFreshness.LIVE,
        )
        records.append(
            ExchangeRateRecord(
                period=date_text,
                usd_inr_rate=usd_inr_rate,
                citation=citation,
            )
        )
        if len(records) >= lookback_limit:
            break
    return records
