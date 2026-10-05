"""Payload parsers for the Fiscal & Public Finance Sector.

Transforms raw responses from IMF MCP / SDMX, MoSPI eSankhyiki MCP,
and official publications into typed Pydantic models.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fiscal_sector.models import (
    Citation,
    DataFreshness,
    FiscalDeficitRecord,
    GSTCollectionRecord,
    MoSPITaxAggregateRecord,
    SovereignDebtRecord,
)

logger = logging.getLogger(__name__)


def parse_imf_weo_observations(
    debt_text: str,
    deficit_text: str,
    freshness: DataFreshness = DataFreshness.LIVE,
) -> list[SovereignDebtRecord]:
    """Parse Markdown table or JSON from IMF MCP WEO responses."""
    # Pattern to match table rows: | Series Key | Time Period | Value | Status |
    row_pattern = re.compile(
        r"\|\s*([A-Za-z0-9_\.]+)\s*\|\s*(\d{4}(?:-[A-Za-z0-9]+)?)\s*\|\s*([-\d\.]+)\s*\|"
    )

    debt_map: dict[str, float] = {}
    for match in row_pattern.finditer(debt_text):
        series_key, period, val_str = match.groups()
        try:
            debt_map[period] = round(float(val_str), 2)
        except ValueError:
            pass

    deficit_map: dict[str, float] = {}
    for match in row_pattern.finditer(deficit_text):
        series_key, period, val_str = match.groups()
        try:
            deficit_map[period] = round(float(val_str), 2)
        except ValueError:
            pass

    # Merge periods
    all_periods = sorted(set(debt_map.keys()) | set(deficit_map.keys()))
    records: list[SovereignDebtRecord] = []
    now_ts = datetime.now(timezone.utc).isoformat()

    for period in all_periods:
        g_debt = debt_map.get(period)
        n_lend = deficit_map.get(period)
        if g_debt is None or n_lend is None:
            continue

        citation = Citation(
            source_agent="fiscal_sector",
            source_authority="International Monetary Fund (IMF)",
            document_title="World Economic Outlook (WEO) SDMX 3.0",
            table_reference="IND.GGXWDG_NGDP.A / IND.GGXCNL_NGDP.A",
            indicator_id="in.macro.fiscal.general_govt_debt_gdp",
            observation_period=period,
            value=g_debt,
            unit="% of GDP",
            url="https://data.imf.org/",
            freshness=freshness,
            retrieved_at=now_ts,
        )

        records.append(
            SovereignDebtRecord(
                period=period,
                general_govt_gross_debt_gdp_pct=g_debt,
                net_lending_borrowing_gdp_pct=n_lend,
                citation=citation,
            )
        )

    return records


def parse_mospi_nas_tax_records(
    payload: dict[str, Any],
    freshness: DataFreshness = DataFreshness.LIVE,
) -> list[MoSPITaxAggregateRecord]:
    """Parse raw JSON data from MoSPI MCP NAS get_data tool."""
    items = payload.get("data", [])
    records: list[MoSPITaxAggregateRecord] = []
    now_ts = datetime.now(timezone.utc).isoformat()

    # Deduplicate by (year, indicator)
    seen: set[tuple[str, str]] = set()

    for item in items:
        year = str(item.get("year", ""))
        indicator = str(item.get("indicator", "Net Taxes on Products"))
        if not year or (year, indicator) in seen:
            continue

        try:
            cur_price = float(item.get("current_price", 0.0))
            con_price = float(item.get("constant_price", 0.0)) if item.get("constant_price") else None
        except (ValueError, TypeError):
            continue

        citation = Citation(
            source_agent="fiscal_sector",
            source_authority="Ministry of Statistics and Programme Implementation (MoSPI)",
            document_title="National Accounts Statistics (NAS) eSankhyiki",
            table_reference=f"NAS Indicator: {indicator}",
            indicator_id="in.macro.fiscal.mospi_product_taxes",
            observation_period=year,
            value=cur_price,
            unit=item.get("unit", "₹ Crore"),
            url="https://esankhyiki.mospi.gov.in/",
            freshness=freshness,
            retrieved_at=now_ts,
        )

        records.append(
            MoSPITaxAggregateRecord(
                year=year,
                indicator=indicator,
                current_price_cr=cur_price,
                constant_price_cr=con_price,
                frequency=item.get("frequency", "Annual"),
                revision=item.get("revision"),
                citation=citation,
            )
        )
        seen.add((year, indicator))

    return records
