"""Universal Canonical Economic Data Layer and Analytical Output Schemas.

Cleanly separates empirical observations from causal models, scenario forecasts,
evidence provenance, and agent analytical assessments.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, Field


class SectorEnum(str, Enum):
    """The 8 standard Indian macroeconomic domains."""
    REAL_ECONOMY = "real_economy"
    PRICES_INFLATION = "prices_inflation"
    MONETARY_BANKING = "monetary_banking"
    FISCAL = "fiscal"
    EXTERNAL = "external"
    CAPITAL_MARKETS = "capital_markets"
    AGRICULTURE_RURAL = "agriculture_rural"
    LABOUR_EMPLOYMENT = "labour_employment"


class DataStatusEnum(str, Enum):
    LIVE = "live"
    VERIFIED_HISTORICAL = "verified_historical"
    UNAVAILABLE = "unavailable"


class RevisionStatusEnum(str, Enum):
    FLASH = "flash"
    PROVISIONAL = "provisional"
    REVISED = "revised"
    FINAL = "final"


class CausalRelationType(str, Enum):
    """Rigorous 5-tier causal classification taxonomy."""
    THEORY = "THEORY"                                       # Qualitative economic theory consensus
    STATISTICAL_ASSOCIATION = "STATISTICAL_ASSOCIATION"     # Contemporaneous correlation with p-value
    LAGGED_RELATIONSHIP = "LAGGED_RELATIONSHIP"             # Cross-correlation at lag k
    GRANGER_PREDICTIVE = "GRANGER_PREDICTIVE"               # Granger predictive causality F-test
    STRUCTURAL_CAUSAL_MODEL = "STRUCTURAL_CAUSAL_MODEL"     # Explicit SCM/DAG with identified conditions


# 1. Canonical Indicator Definition (Metadata Schema)
class CanonicalIndicator(BaseModel):
    """Definition and metadata for a recognized economic indicator."""
    indicator_id: str = Field(..., description="Unique hierarchical identifier, e.g. in.macro.prices.cpi_headline")
    name: str = Field(..., description="Full descriptive name, e.g. All India CPI Combined Headline")
    sector: SectorEnum = Field(..., description="One of the 8 canonical macroeconomic domains")
    subsector: Optional[str] = Field(default=None, description="Granular classification, e.g. Core, Food, IIP-Capital")
    unit: str = Field(..., description="Measurement unit, e.g. % YoY, Billion USD, INR Crore, points")
    frequency: str = Field(..., description="Observation frequency: monthly, quarterly, annual, daily")
    source_authority: str = Field(..., description="Official publishing entity: MoSPI, RBI, SEBI, AMFI, etc.")
    source_url: Optional[str] = Field(default=None, description="Official portal or dataset URL")
    description: Optional[str] = Field(default=None, description="Economic description of indicator")


# 2. Canonical Observation (Empirical Data Point)
class CanonicalObservation(BaseModel):
    """An empirical observation value with strict data provenance and statistical features."""
    observation_id: str = Field(
        default_factory=lambda: f"obs-{uuid.uuid4().hex[:10]}",
        description="Unique observation identifier"
    )
    indicator_id: str = Field(..., description="Reference to CanonicalIndicator.indicator_id")
    observation_period: str = Field(..., description="Period string: YYYY-MM-DD, YYYY-QX, or YYYY")
    value: Optional[float] = Field(..., description="Numerical observed value or None if missing")
    unit: str = Field(..., description="Measurement unit matching canonical indicator")
    release_timestamp: Optional[str] = Field(default=None, description="Official publication timestamp (ISO 8601)")
    retrieved_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Data ingestion timestamp"
    )
    revision_status: RevisionStatusEnum = Field(default=RevisionStatusEnum.FINAL)
    data_status: DataStatusEnum = Field(default=DataStatusEnum.LIVE)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Data reliability confidence score")
    z_score: Optional[float] = Field(default=None, description="Rolling historical Z-score")
    percentile_rank: Optional[float] = Field(default=None, description="Historical percentile distribution (0-100)")
    provenance_hash: Optional[str] = Field(default=None, description="SHA-256 hash of observation payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary context")

    def model_post_init(self, __context: Any) -> None:
        if not self.provenance_hash:
            payload = f"{self.indicator_id}:{self.observation_period}:{self.value}:{self.unit}:{self.data_status}"
            self.provenance_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# 3. Causal Relationship (Transmission Edge in Knowledge Graph)
class CausalRelationship(BaseModel):
    """Empirical or theoretical causal transmission link between two indicators."""
    relation_id: str = Field(
        default_factory=lambda: f"rel-{uuid.uuid4().hex[:8]}",
        description="Unique relation ID"
    )
    source_indicator_id: str = Field(..., description="Upstream shock indicator ID")
    target_indicator_id: str = Field(..., description="Downstream response indicator ID")
    relation_type: CausalRelationType = Field(..., description="Causal classification level")
    transmission_lag_months: int = Field(default=0, ge=0, description="Estimated transmission lag in months")
    elasticity_sign: str = Field(default="+", description="Directional sign: '+' (positive), '-' (inverse), or 'ambiguous'")
    empirical_p_value: Optional[float] = Field(default=None, description="Statistical significance p-value if empirical")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in transmission link")
    mechanism_description: str = Field(..., description="Economic mechanism explanation")
    documented_assumptions: List[str] = Field(default_factory=list, description="Causal assumptions / identification bounds")


# 4. Scenario Simulation Result
class ScenarioResult(BaseModel):
    """Forecasted propagation path under simulated macroeconomic shock conditions."""
    scenario_id: str = Field(default_factory=lambda: f"scen-{uuid.uuid4().hex[:8]}")
    scenario_name: str = Field(..., description="E.g., Global Crude Oil Shock (+20%)")
    shock_variable: str = Field(..., description="Shocked indicator ID")
    shock_magnitude: float = Field(..., description="Shock size in indicator units or %")
    horizon_periods: int = Field(default=4, description="Forecast horizon in quarters or months")
    forecasted_impacts: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of indicator_id -> {baseline, shocked, delta, confidence_band}"
    )
    simulated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance_chain: List[str] = Field(default_factory=list, description="Causal relation IDs traversed")


# 5. Evidence & Provenance Citation
class Evidence(BaseModel):
    """Verifiable source citation, official document excerpt, or observation hash."""
    evidence_id: str = Field(default_factory=lambda: f"evi-{uuid.uuid4().hex[:8]}")
    source_authority: str = Field(..., description="MoSPI, RBI, IMF, SEBI, etc.")
    document_title: str = Field(..., description="E.g., Monetary Policy Report Oct 2024")
    publication_date: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    verbatim_excerpt: Optional[str] = Field(default=None, description="Exact quotation or table reference")
    observation_hashes: List[str] = Field(default_factory=list, description="Linked observation SHA-256 hashes")


# 6. Agent Analysis (Domain Synthesized Output)
class AgentAnalysis(BaseModel):
    """Structured analytical assessment produced by a domain agent."""
    agent_id: str = Field(..., description="Agent name/identifier")
    sector: SectorEnum = Field(..., description="Domain sector")
    observations: List[CanonicalObservation] = Field(default_factory=list)
    causal_links: List[CausalRelationship] = Field(default_factory=list)
    evidence_chain: List[Evidence] = Field(default_factory=list)
    assessment_narrative: str = Field(..., description="Explainable synthesis text")
    risk_alerts: List[str] = Field(default_factory=list, description="Macroeconomic risk warnings")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
