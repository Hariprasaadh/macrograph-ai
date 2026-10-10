"""Strict proposals and auditable outcomes; model prose is never rendered as fact."""
from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ClaimBase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim_id: str = Field(min_length=1, max_length=100)


class ObservationClaim(ClaimBase):
    claim_type: Literal['observation']
    observation_id: str
    proposed_value: float = Field(allow_inf_nan=False)
    output_unit: Literal['% YoY', '% MoM', 'index']


class RateChangeClaim(ClaimBase):
    claim_type: Literal['rate_change']
    operation: Literal['subtract']
    earlier_observation_id: str
    later_observation_id: str
    proposed_value: float = Field(allow_inf_nan=False)
    output_unit: Literal['percentage_points']


class PriceDirectionClaim(ClaimBase):
    claim_type: Literal['price_direction_yoy']
    observation_id: str
    direction: Literal['higher', 'lower', 'unchanged']
    comparison: Literal['same_month_previous_year']


class ReportedExplanationClaim(ClaimBase):
    claim_type: Literal['reported_explanation']
    passage_id: str
    supporting_quote: str = Field(min_length=1, max_length=1800)


class GeneralMechanismClaim(ClaimBase):
    claim_type: Literal['general_mechanism']
    mechanism_id: Literal['cpi_definition', 'wpi_definition', 'yoy_interpretation', 'wholesale_pass_through']


class StatisticalFindingClaim(ClaimBase):
    claim_type: Literal['statistical_finding']
    analysis_id: str


Claim = Annotated[ObservationClaim | RateChangeClaim | PriceDirectionClaim | ReportedExplanationClaim
                  | GeneralMechanismClaim | StatisticalFindingClaim, Field(discriminator='claim_type')]
CLAIM_ADAPTER = TypeAdapter(Claim)


class VerificationResult(BaseModel):
    claim_id: str
    claim_type: str
    status: Literal['verified', 'source_attributed', 'general_mechanism', 'rejected', 'insufficient_evidence']
    verification_method: str
    evidence_ids: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    computed_value: float | None = None
    unit: str | None = None
    rendered_text: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
