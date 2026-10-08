"""Strict, typed A2A request/response envelopes and shared payload contracts."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .exceptions import A2AException, ErrorCode

_STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)


_URL_QUERY = re.compile(r"(https?://[^\s?'\"]+)\?[^\s'\"]*")
_MAX_ERROR_CHARS = 300


def scrub_error_text(text: str) -> str:
    """Drop URL query strings (they can carry API keys) and bound the length of client-visible errors."""
    cleaned = _URL_QUERY.sub(lambda m: m.group(1) + "?<redacted>", text)
    return cleaned if len(cleaned) <= _MAX_ERROR_CHARS else cleaned[:_MAX_ERROR_CHARS] + "..."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class SourceProvenance(BaseModel):
    """Origin of a factual statement; survives every A2A hop unchanged."""
    model_config = _STRICT

    source_url: Optional[str] = None
    source_name: str = Field(..., min_length=1)
    dataset: Optional[str] = None
    table: Optional[str] = None
    reporting_period: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=_now)
    page_or_section: Optional[str] = None
    record_reference: Optional[str] = None


class A2AErrorInfo(BaseModel):
    """Structured error: stable code plus human-readable message."""
    model_config = _STRICT

    code: ErrorCode
    message: str
    agent: Optional[str] = None

    @field_validator("message")
    @classmethod
    def _scrub_message(cls, value: str) -> str:
        return scrub_error_text(value)

    @classmethod
    def from_exception(cls, exc: A2AException, agent: Optional[str] = None) -> "A2AErrorInfo":
        return cls(code=exc.code, message=exc.message, agent=agent)


class FollowUp(BaseModel):
    """A question the responder wants the delegating agent to route elsewhere."""
    model_config = _STRICT

    receiver_agent: str
    task: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str


class A2ARequest(BaseModel):
    """One agent-to-agent task request."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    request_id: str = Field(default_factory=lambda: new_id("req"), min_length=1)
    sender_agent: str = Field(..., min_length=1)
    receiver_agent: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    context: Optional[dict[str, Any]] = None
    conversation_id: str = Field(..., min_length=1)
    parent_request_id: Optional[str] = None
    depth: int = Field(default=0, ge=0)
    call_chain: tuple[str, ...] = Field(default_factory=tuple)
    timeout_seconds: Optional[float] = Field(default=None, gt=0)
    timestamp: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _no_self_parent(self) -> "A2ARequest":
        if self.parent_request_id == self.request_id:
            raise ValueError("parent_request_id must differ from request_id")
        return self


class A2AResponse(BaseModel):
    """Result of an A2ARequest; failures are data, never raised across agents."""
    model_config = _STRICT

    request_id: str
    sender_agent: str
    receiver_agent: str
    status: Literal["success", "partial", "failed"]
    result: Optional[dict[str, Any] | list[Any] | str] = None
    sources: list[SourceProvenance] = Field(default_factory=list)
    errors: list[A2AErrorInfo] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now)

    @property
    def ok(self) -> bool:
        return self.status in ("success", "partial")

    @property
    def error_codes(self) -> list[ErrorCode]:
        return [e.code for e in self.errors]


class HandlerOutput(BaseModel):
    """What a capability handler returns; the server wraps it into an A2AResponse."""
    model_config = _STRICT

    result: Optional[dict[str, Any] | list[Any] | str] = None
    sources: list[SourceProvenance] = Field(default_factory=list)
    status: Literal["success", "partial"] = "success"
    errors: list[A2AErrorInfo] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ACallContext(BaseModel):
    """Position of the executing agent in the delegation chain; passed to handlers."""
    model_config = _STRICT

    conversation_id: str
    request_id: str
    agent_id: str
    depth: int = Field(default=0, ge=0)
    call_chain: tuple[str, ...] = Field(default_factory=tuple)


class IndicatorObservation(BaseModel):
    """One cited indicator value exchanged between sector agents."""
    model_config = _STRICT

    indicator_id: str
    label: str
    value: Optional[float] = None
    unit: str = ""
    observation_period: Optional[str] = None
    data_status: str = "unknown"

    @field_validator("value")
    @classmethod
    def _finite(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v != v:
            raise ValueError("value must not be NaN")
        return v


class IndicatorSignal(BaseModel):
    """Typed result for peer indicator queries (repo rate, CPI, credit growth, ...)."""
    model_config = _STRICT

    owner_agent: str
    observations: list[IndicatorObservation] = Field(min_length=1)


class PeerQuery(BaseModel):
    """Typed parameters for peer indicator queries."""
    model_config = _STRICT

    question: Optional[str] = Field(default=None, max_length=500)
