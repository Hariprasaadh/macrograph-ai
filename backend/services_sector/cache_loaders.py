"""Cache loaders for Services Sector DuckDB.

Retrieves persisted records from sector-isolated DuckDB and reconstructs
strictly typed Pydantic models with DataFreshness.CACHED provenance.
"""
from __future__ import annotations

import json
from typing import Any

from services_sector import database as db
from services_sector.models import (
    Citation,
    DataFreshness,
    ISPRecord,
    ServicesGVARecord,
    ServicesPMIRecord,
    ServiceSubSector,
    TransportFreightRecord,
)
from services_sector.parsers import parse_period_sort_key


class ServicesDataUnavailableError(Exception):
    """Raised when neither live fetch nor cache can supply data."""


def prepare_cached_citation(citation_data: Any) -> Citation:
    """Deserialise citation dictionary and mark freshness as CACHED."""
    if isinstance(citation_data, str):
        try:
            citation_data = json.loads(citation_data)
        except json.JSONDecodeError:
            citation_data = {}
    elif not isinstance(citation_data, dict):
        citation_data = {}
    citation_data["freshness"] = DataFreshness.CACHED
    return Citation.model_validate(citation_data)


def load_isp_from_cache(
    sub_sector: ServiceSubSector | None,
    lookback_months: int,
) -> list[ISPRecord]:
    """Load ISP records from DuckDB."""
    rows = db.query_latest_rows("isp_growth", lookback_months * 20)
    if not rows:
        raise ServicesDataUnavailableError(
            "ISP data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        if sub_sector is not None and row.get("sub_sector") != sub_sector.value:
            continue
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            ISPRecord(
                period=row["period"],
                sub_sector=ServiceSubSector(row.get("sub_sector", "GENERAL")),
                isp_index=row.get("isp_index"),
                isp_yoy_pct=row.get("isp_yoy_pct"),
                isp_mom_pct=row.get("isp_mom_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    if sub_sector is not None:
        return records[-lookback_months:] if len(records) > lookback_months else records
    return records


def load_gva_from_cache() -> list[ServicesGVARecord]:
    """Load services GVA records from DuckDB."""
    rows = db.query_latest_rows("services_gva", 30)
    if not rows:
        raise ServicesDataUnavailableError(
            "Services GVA data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            ServicesGVARecord(
                period=row["period"],
                nas_statement=row.get("nas_statement", "unknown"),
                segment=row.get("segment", "Services"),
                gva_current_cr=row.get("gva_current_cr"),
                gva_constant_cr=row.get("gva_constant_cr"),
                gva_yoy_pct=row.get("gva_yoy_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records


def load_pmi_from_cache(lookback_months: int) -> list[ServicesPMIRecord]:
    """Load services PMI records from DuckDB."""
    rows = db.query_latest_rows("services_pmi", lookback_months)
    if not rows:
        raise ServicesDataUnavailableError(
            "Services PMI data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            ServicesPMIRecord(
                period=row["period"],
                headline_pmi=row.get("headline_pmi"),
                new_orders_idx=row.get("new_orders_idx"),
                input_costs_idx=row.get("input_costs_idx"),
                employment_idx=row.get("employment_idx"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records


def load_freight_from_cache(lookback_months: int) -> list[TransportFreightRecord]:
    """Load transport/freight records from DuckDB."""
    rows = db.query_latest_rows("transport_freight", lookback_months * 10)
    if not rows:
        raise ServicesDataUnavailableError(
            "Transport/freight data unavailable: live fetch failed and cache is empty."
        )
    records = []
    for row in rows:
        citation = prepare_cached_citation(row.get("citation", {}))
        records.append(
            TransportFreightRecord(
                period=row["period"],
                indicator=row.get("indicator", "unknown"),
                value=row.get("value"),
                unit=row.get("unit", ""),
                yoy_pct=row.get("yoy_pct"),
                citation=citation,
            )
        )
    records.sort(key=lambda r: parse_period_sort_key(r.period))
    return records
