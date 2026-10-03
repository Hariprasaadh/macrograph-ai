"""Parsers for External Sector JSON payloads (DBIE & MoSPI)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from external_sector.models import (
    Citation,
    DataFreshness,
    ExchangeRateRecord,
    ExternalDebtRecord,
    ForexReservesRecord,
    RemittancesRecord,
    TradeBalanceRecord,
)

logger = logging.getLogger(__name__)


def safe_float_val(val: Any) -> float | None:
    if val is None or val == "" or val == "-" or val == ".":
        return None
    try:
        cleaned = str(val).replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_period_sort_key(period_str: str) -> tuple[int, int, int]:
    """Parse period string into a sortable tuple (year, month, day) for accurate chronological sorting."""
    p = str(period_str).strip()
    # Try DD-Mon-YYYY (e.g. 18-Sep-2026)
    try:
        dt = datetime.strptime(p, "%d-%b-%Y")
        return (dt.year, dt.month, dt.day)
    except ValueError:
        pass
    # Try YYYY-MM-DD
    try:
        dt = datetime.strptime(p, "%Y-%m-%d")
        return (dt.year, dt.month, dt.day)
    except ValueError:
        pass
    # Try YYYY-MM
    try:
        dt = datetime.strptime(p, "%Y-%m")
        return (dt.year, dt.month, 1)
    except ValueError:
        pass
    # Try YYYY-Q# (e.g. 2024-Q1)
    m = re.match(r"^(\d{4})-Q([1-4])$", p, re.IGNORECASE)
    if m:
        return (int(m.group(1)), int(m.group(2)) * 3, 1)
    # Try YYYY-YY (e.g. 2024-25)
    m = re.match(r"^(\d{4})-\d{2}$", p)
    if m:
        return (int(m.group(1)), 12, 31)
    # Try YYYY
    try:
        dt = datetime.strptime(p, "%Y")
        return (dt.year, 1, 1)
    except ValueError:
        pass
    return (0, 0, 0)


def parse_forex_reserves(payload: dict[str, Any], lookback_limit: int = 12) -> list[ForexReservesRecord]:
    """Parse RBI DBIE weekly foreign exchange reserves JSON."""
    if lookback_limit < 1:
        return []
    data = payload.get("data", []) if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        data = []

    records: list[ForexReservesRecord] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        period = str(item.get("weekEnded") or item.get("period") or "unknown")
        total_usd = safe_float_val(item.get("totalReservesUSD"))
        total_inr = safe_float_val(item.get("totalReservesINR"))
        import_cover = safe_float_val(item.get("importCoverMonths") or item.get("import_cover_months"))

        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI)",
            document_title="RBI Foreign Exchange Reserves - Weekly Statistical Supplement",
            table_reference="external_sector.r574_foreign_exchange_reserves",
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
                import_cover_months=import_cover,
                citation=citation,
            )
        )

    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    return records[:lookback_limit]


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
    if "-" in fiscal_year_text and month_number <= 3:
        year += 1
    return f"{year:04d}-{month_number:02d}"


def parse_trade_balance(
    payload: Any,
    lookback_limit: int = 12,
) -> list[TradeBalanceRecord]:
    """Parse RBI DBIE monthly merchandise trade table (US$ Millions)."""
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
                exports_usd_bn=round(exports_usd_mn / 1000, 2) if exports_usd_mn is not None else None,
                imports_usd_bn=round(imports_usd_mn / 1000, 2) if imports_usd_mn is not None else None,
                trade_balance_usd_bn=(
                    round(trade_balance_usd_mn / 1000, 2) if trade_balance_usd_mn is not None else None
                ),
                oil_imports_usd_bn=None,
                non_oil_imports_usd_bn=None,
                oil_exports_usd_bn=None,
                non_oil_exports_usd_bn=None,
                services_surplus_usd_bn=None,
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
                reer_40_basket=None,
                neer_40_basket=None,
                citation=citation,
            )
        )
        if len(records) >= lookback_limit:
            break
    return records


def parse_mospi_invisibles(data: list[dict[str, Any]], lookback_limit: int = 10) -> list[RemittancesRecord]:
    """Parse MoSPI indicator 9 (Invisibles & Remittances by category) into structured records."""
    if not isinstance(data, list) or not data or lookback_limit < 1:
        return []

    # Group by fiscal year
    by_year: dict[str, dict[str, float | None]] = {}
    for item in data:
        year = str(item.get("year") or "").strip()
        if not year:
            continue
        if year not in by_year:
            by_year[year] = {
                "private_net": None,
                "private_receipts": None,
                "private_payments": None,
                "services_net": None,
                "services_receipts": None,
            }
        category = str(item.get("category") or "").strip()
        trade_category = item.get("trade_category")
        val = safe_float_val(item.get("value"))

        if "private transfers" in category.lower():
            if trade_category is None:
                by_year[year]["private_net"] = val
            elif "receipt" in str(trade_category).lower():
                by_year[year]["private_receipts"] = val
            elif "payment" in str(trade_category).lower():
                by_year[year]["private_payments"] = val
        elif "non-factor services" in category.lower():
            if trade_category is None:
                by_year[year]["services_net"] = val
            elif "receipt" in str(trade_category).lower():
                by_year[year]["services_receipts"] = val

    records: list[RemittancesRecord] = []
    for year, vals in by_year.items():
        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI) / MoSPI eSankhyiki",
            document_title="Invisibles by Category of Transactions - US Dollars",
            table_reference="mospi.rbi.indicator_9",
            retrieval_url="https://mcp.mospi.gov.in/",
            observation_period=year,
            freshness=DataFreshness.LIVE,
        )
        records.append(
            RemittancesRecord(
                period=year,
                private_transfers_net_usd_mn=vals["private_net"],
                receipts_usd_mn=vals["private_receipts"],
                payments_usd_mn=vals["private_payments"],
                services_receipts_usd_mn=vals["services_receipts"],
                services_net_usd_mn=vals["services_net"],
                citation=citation,
            )
        )

    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    return records[:lookback_limit]


def parse_mospi_external_debt(data: list[dict[str, Any]], lookback_limit: int = 8) -> list[ExternalDebtRecord]:
    """Parse MoSPI indicator 27 (External Debt of India - Quarterly) into structured records."""
    if not isinstance(data, list) or not data or lookback_limit < 1:
        return []

    by_period: dict[str, dict[str, float | None]] = {}
    for item in data:
        year = str(item.get("year") or "").strip()
        month = str(item.get("month") or "").strip()
        if not year:
            continue
        period = f"{year}-{month}" if month else year
        if period not in by_period:
            by_period[period] = {
                "gov_usd_bn": None,
                "total_usd_bn": None,
                "total_inr_cr": None,
                "short_term_usd_bn": None,
                "short_term_to_reserves_pct": None,
                "debt_to_gdp_pct": None,
            }
        sector = str(item.get("external_debt_sector") or "").strip().lower()
        term = str(item.get("external_debt_term") or "").strip().lower()
        unit = str(item.get("unit") or "").strip().lower()
        val = safe_float_val(item.get("value"))

        is_usd = "usd" in unit or "us dollar" in unit or "million" in unit
        if "general government" in sector:
            by_period[period]["gov_usd_bn"] = round(val / 1000.0, 2) if (val is not None and is_usd) else val
        elif "total" in sector:
            if is_usd:
                by_period[period]["total_usd_bn"] = round(val / 1000.0, 2) if val is not None else None
            else:
                by_period[period]["total_inr_cr"] = val
        elif "short" in term or ("short" in sector and "ratio" not in sector and "reserve" not in sector and "gdp" not in sector):
            by_period[period]["short_term_usd_bn"] = round(val / 1000.0, 2) if (val is not None and is_usd) else val
        elif "short_term_to_reserves" in sector or ("short-term debt" in sector and "reserves" in sector):
            by_period[period]["short_term_to_reserves_pct"] = val
        elif "debt_to_gdp" in sector or ("external debt" in sector and "gdp" in sector):
            by_period[period]["debt_to_gdp_pct"] = val

    records: list[ExternalDebtRecord] = []
    for period, vals in by_period.items():
        citation = Citation(
            source_agent="external_sector",
            source_authority="Reserve Bank of India (RBI) / MoSPI eSankhyiki",
            document_title="External Debt of India - Quarterly",
            table_reference="mospi.rbi.indicator_27",
            retrieval_url="https://mcp.mospi.gov.in/",
            observation_period=period,
            freshness=DataFreshness.LIVE,
        )
        records.append(
            ExternalDebtRecord(
                period=period,
                total_debt_usd_bn=safe_float_val(vals.get("total_usd_bn")),
                total_debt_inr_cr=vals.get("total_inr_cr"),
                general_government_usd_bn=safe_float_val(vals.get("gov_usd_bn")),
                short_term_debt_usd_bn=safe_float_val(vals.get("short_term_usd_bn")),
                short_term_to_reserves_pct=vals.get("short_term_to_reserves_pct"),
                debt_to_gdp_pct=vals.get("debt_to_gdp_pct"),
                citation=citation,
            )
        )

    records.sort(key=lambda r: parse_period_sort_key(r.period), reverse=True)
    return records[:lookback_limit]
