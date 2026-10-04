"""Typed agriculture observations, provenance and MCP result contracts."""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Text = Annotated[str, Field(min_length=1)]
SourceCategory = Literal["agmarknet", "mospi", "weather_mcp", "data_gov", "faostat"]


class AgricultureQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    crop: Text | None = None
    commodity: Text | None = None
    state: Text | None = None
    district: Text | None = None
    market: Text | None = None
    variety: Text | None = None
    city: Text | None = None
    location: Text | None = None
    country: Text | None = None
    history_years: int | None = Field(default=None, ge=2, le=50)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    intent: str | None = None
    period: Text | None = None
    start_date: date | None = None
    end_date: date | None = None
    scheme: Text | None = None
    days: int = Field(default=30, ge=1, le=365)
    limit: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def date_order(self) -> AgricultureQuery:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must precede end_date")
        return self


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_agent: Literal["agriculture_sector"] = "agriculture_sector"
    source: Text
    source_category: SourceCategory
    source_url: Text
    dataset: Text
    mcp_tool: Text
    upstream_tool: Text
    retrieved_at: datetime
    data_vintage: str | None = None
    source_note: str | None = None
    source_filters: dict[str, Any] = Field(default_factory=dict)
    freshness: Literal["retrieved_live", "source_snapshot", "cached", "live", "recent"] = "retrieved_live"

    @model_validator(mode="after")
    def timezone_required(self) -> Provenance:
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must include timezone")
        return self


class AgricultureObservation(Provenance):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    kind: Literal["observation"] = "observation"
    indicator: Text
    value: float
    unit: Text
    period: Text
    frequency: Text
    quality_flag: str | None = None
    state: str | None = None
    district: str | None = None
    crop: str | None = None
    commodity: str | None = None
    market: str | None = None
    variety: str | None = None
    season: str | None = None

    @field_validator("value", mode="before")
    @classmethod
    def reject_boolean(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("A boolean is not a numeric observation")
        return value

    def citation(self) -> dict[str, Any]:
        filters = self.source_filters.get("filters", self.source_filters)
        table = self.dataset
        if isinstance(filters, dict) and filters.get("indicator_code") is not None:
            table += f" / indicator_code {filters['indicator_code']}"
        citation = {
            **self.model_dump(mode="json", exclude_none=True),
            "source_authority": self.source,
            "document_title": f"{self.dataset}: {self.indicator}",
            "table_reference": table, "retrieval_url": self.source_url,
            "observation_period": self.period, "fetched_at": self.retrieved_at.isoformat(),
        }
        canonical = json.dumps(citation, sort_keys=True, default=str).encode("utf-8")
        citation["provenance_hash"] = hashlib.sha256(canonical).hexdigest()[:16]
        return citation


class CropProduction(AgricultureObservation):
    kind: Literal["crop_production"] = "crop_production"
    crop: Text
    value: float = Field(ge=0)


class CropYield(CropProduction):
    kind: Literal["crop_yield"] = "crop_yield"


class CropArea(CropProduction):
    kind: Literal["crop_area"] = "crop_area"


class CropListObservation(Provenance):
    kind: Literal["crop_list"] = "crop_list"
    name: Text
    period: Text


class MandiPrice(AgricultureObservation):
    kind: Literal["mandi_price"] = "mandi_price"
    commodity: Text
    market: Text
    value: float = Field(ge=0)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def price_range(self) -> MandiPrice:
        if self.min_price is not None and self.value < self.min_price:
            raise ValueError("Modal price below minimum")
        if self.max_price is not None and self.value > self.max_price:
            raise ValueError("Modal price above maximum")
        return self


class MarketArrival(AgricultureObservation):
    kind: Literal["market_arrival"] = "market_arrival"
    commodity: Text
    market: Text
    value: float = Field(ge=0)


class MSPObservation(CropProduction):
    kind: Literal["msp"] = "msp"
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def effective_period(self) -> MSPObservation:
        if bool(self.effective_from) != bool(self.effective_to):
            raise ValueError("MSP effective dates require both endpoints")
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("MSP effective dates are reversed")
        return self


class RainfallObservation(AgricultureObservation):
    kind: Literal["rainfall"] = "rainfall"
    value: float = Field(ge=0)
    normal_value: float | None = Field(default=None, ge=0)
    normal_period: str | None = None
    normal_source: str | None = None
    normal_source_url: str | None = None
    city: str | None = None


class WeatherObservation(AgricultureObservation):
    kind: Literal["weather"] = "weather"
    metric: Text
    location: Text
    display_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class MonsoonObservation(Provenance):
    kind: Literal["monsoon"] = "monsoon"
    indicator: Text
    period: Text
    state: Text
    monsoon_status: Text


class FertilizerObservation(AgricultureObservation):
    kind: Literal["fertilizer"] = "fertilizer"
    fertilizer: Text
    value: float = Field(ge=0)


class IrrigationObservation(AgricultureObservation):
    kind: Literal["irrigation"] = "irrigation"
    value: float = Field(ge=0)
    irrigation_source: str | None = None
    measure: str | None = None


class AgricultureScheme(Provenance):
    kind: Literal["scheme"] = "scheme"
    name: Text
    description: Text
    period: Text


Observation = Annotated[
    CropProduction | CropYield | CropArea | CropListObservation | MandiPrice | MarketArrival | MSPObservation
    | RainfallObservation | WeatherObservation | MonsoonObservation | FertilizerObservation
    | IrrigationObservation | AgricultureScheme | AgricultureObservation,
    Field(discriminator="kind"),
]


class SourceError(BaseModel):
    source: str
    code: Literal["not_configured", "unsupported", "timeout", "source_error", "missing_data", "invalid_data"]
    message: str


class AgricultureResult(BaseModel):
    tool: str
    status: Literal["available", "partial", "unavailable", "error"]
    records: list[Observation] = Field(default_factory=list)
    errors: list[SourceError] = Field(default_factory=list)
    derived: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def availability(self) -> AgricultureResult:
        if self.status in {"unavailable", "error"} and (self.records or self.derived):
            raise ValueError("Unavailable results cannot contain observations")
        if self.status in {"available", "partial"} and not self.records:
            raise ValueError("Available results require sourced observations")
        return self


class AgricultureFinding(BaseModel):
    agent: Literal["agriculture_sector"] = "agriculture_sector"
    indicator: str
    finding: str
    evidence: list[Observation] = Field(default_factory=list)
    source: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["available", "partial", "unavailable", "error"]
    confidence: Literal["sourced_observations", "insufficient_evidence"]
    analytics: list[dict[str, Any]] = Field(default_factory=list)
