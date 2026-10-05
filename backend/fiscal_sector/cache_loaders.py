"""Cache loaders for the Fiscal Sector.

When live external fetches (IMF MCP, MoSPI MCP, CGA) fail or time out,
these loaders read from the sector's dedicated DuckDB and return
records stamped with DataFreshness.CACHED.
"""
from __future__ import annotations

import json
import logging
from fiscal_sector import database as db
from fiscal_sector.models import (
    Citation,
    DataFreshness,
    FiscalDeficitRecord,
    GSTCollectionRecord,
    MoSPITaxAggregateRecord,
    SovereignDebtRecord,
)

logger = logging.getLogger(__name__)


class FiscalDataUnavailableError(Exception):
    """Raised when live fetch fails AND local DuckDB cache is empty."""
    pass


def load_fiscal_deficit_from_cache(lookback: int = 5) -> list[FiscalDeficitRecord]:
    """Load Union fiscal deficit records from DuckDB."""
    rows = db.query_fiscal_deficit(lookback)
    if not rows:
        raise FiscalDataUnavailableError(
            "Union fiscal deficit data is unavailable: live fetch failed and cache is empty."
        )

    records: list[FiscalDeficitRecord] = []
    for r in rows:
        cit_dict = json.loads(r["citation"]) if isinstance(r["citation"], str) else r["citation"]
        cit_dict["freshness"] = DataFreshness.CACHED.value
        records.append(
            FiscalDeficitRecord(
                period=r["period"],
                revenue_receipts_cr=r["revenue_receipts_cr"],
                tax_revenue_net_cr=r["tax_revenue_net_cr"],
                non_tax_revenue_cr=r["non_tax_revenue_cr"],
                non_debt_capital_receipts_cr=r.get("non_debt_capital_receipts_cr", 0.0),
                total_receipts_cr=r["total_receipts_cr"],
                total_expenditure_cr=r["total_expenditure_cr"],
                revenue_expenditure_cr=r["revenue_expenditure_cr"],
                capital_expenditure_cr=r["capital_expenditure_cr"],
                fiscal_deficit_cr=r["fiscal_deficit_cr"],
                fiscal_deficit_gdp_pct=r.get("fiscal_deficit_gdp_pct"),
                revenue_deficit_cr=r.get("revenue_deficit_cr"),
                primary_deficit_cr=r.get("primary_deficit_cr"),
                citation=Citation.model_validate(cit_dict),
            )
        )
    return records


def load_sovereign_debt_from_cache(lookback: int = 10) -> list[SovereignDebtRecord]:
    """Load general government debt records from DuckDB."""
    rows = db.query_general_govt_debt(lookback)
    if not rows:
        raise FiscalDataUnavailableError(
            "General government debt data is unavailable: live IMF fetch failed and cache is empty."
        )

    records: list[SovereignDebtRecord] = []
    for r in rows:
        cit_dict = json.loads(r["citation"]) if isinstance(r["citation"], str) else r["citation"]
        cit_dict["freshness"] = DataFreshness.CACHED.value
        records.append(
            SovereignDebtRecord(
                period=r["period"],
                general_govt_gross_debt_gdp_pct=r["general_govt_gross_debt_gdp_pct"],
                net_lending_borrowing_gdp_pct=r["net_lending_borrowing_gdp_pct"],
                revenue_gdp_pct=r.get("revenue_gdp_pct"),
                expenditure_gdp_pct=r.get("expenditure_gdp_pct"),
                citation=Citation.model_validate(cit_dict),
            )
        )
    return records


def load_gst_collections_from_cache(lookback_months: int = 12) -> list[GSTCollectionRecord]:
    """Load GST collections from DuckDB."""
    rows = db.query_gst_collections(lookback_months)
    if not rows:
        raise FiscalDataUnavailableError(
            "GST collections data is unavailable: live fetch failed and cache is empty."
        )

    records: list[GSTCollectionRecord] = []
    for r in rows:
        cit_dict = json.loads(r["citation"]) if isinstance(r["citation"], str) else r["citation"]
        cit_dict["freshness"] = DataFreshness.CACHED.value
        records.append(
            GSTCollectionRecord(
                period=r["period"],
                gross_gst_cr=r["gross_gst_cr"],
                cgst_cr=r.get("cgst_cr"),
                sgst_cr=r.get("sgst_cr"),
                igst_cr=r.get("igst_cr"),
                cess_cr=r.get("cess_cr"),
                yoy_growth_pct=r.get("yoy_growth_pct"),
                citation=Citation.model_validate(cit_dict),
            )
        )
    return records


def load_mospi_tax_from_cache(lookback: int = 5) -> list[MoSPITaxAggregateRecord]:
    """Load MoSPI National Accounts product tax aggregates from DuckDB."""
    rows = db.query_mospi_tax_aggregates(lookback)
    if not rows:
        raise FiscalDataUnavailableError(
            "MoSPI product tax data is unavailable: live fetch failed and cache is empty."
        )

    records: list[MoSPITaxAggregateRecord] = []
    for r in rows:
        cit_dict = json.loads(r["citation"]) if isinstance(r["citation"], str) else r["citation"]
        cit_dict["freshness"] = DataFreshness.CACHED.value
        records.append(
            MoSPITaxAggregateRecord(
                year=r["year"],
                indicator=r["indicator"],
                current_price_cr=r["current_price_cr"],
                constant_price_cr=r.get("constant_price_cr"),
                frequency=r.get("frequency", "Annual"),
                revision=r.get("revision"),
                citation=Citation.model_validate(cit_dict),
            )
        )
    return records
