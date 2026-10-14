"""Resource IDs and observed field contracts from the data.gov.in API.

The IDs were checked against the portal resource pages and live API on
2026-10-14. Runtime retrieval still validates the returned schema and rows.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSpec:
    resource_id: str
    title: str
    publisher: str
    period_field: str
    value_fields: tuple[str, ...]
    required_fields: frozenset[str]
    unit: str
    frequency: str

    @property
    def api_url(self) -> str:
        return f"https://api.data.gov.in/resource/{self.resource_id}"


MANDI = ResourceSpec(
    resource_id="9ef84268-d588-465a-a308-a864a43d0070",
    title="Current Daily Price of Various Commodities from Various Markets (Mandi)",
    publisher="Ministry of Agriculture and Farmers Welfare, Department of Agriculture and Farmers Welfare",
    period_field="arrival_date",
    value_fields=("modal_price", "min_price", "max_price"),
    required_fields=frozenset({"state", "district", "market", "commodity", "arrival_date",
                               "modal_price", "min_price", "max_price"}),
    unit="INR/quintal",
    frequency="daily",
)

CROP = ResourceSpec(
    resource_id="35be999b-0208-4354-b557-f6ca9a5355de",
    title="District-wise, season-wise crop production statistics from 1997",
    publisher="Ministry of Agriculture and Farmers Welfare, Department of Agriculture and Farmers Welfare",
    period_field="crop_year",
    value_fields=("production_", "area_"),
    required_fields=frozenset({"state_name", "district_name", "crop_year", "season", "crop",
                               "area_", "production_"}),
    unit="tonnes",
    frequency="annual",
)
