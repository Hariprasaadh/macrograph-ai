"""Builders for typed indicator responses exchanged between sector agents."""
from __future__ import annotations

from typing import Optional, Sequence

from .messages import HandlerOutput, IndicatorObservation, IndicatorSignal, SourceProvenance


def signal_output(
    owner_agent: str,
    observations: Sequence[IndicatorObservation],
    sources: Sequence[SourceProvenance],
    *,
    note: Optional[str] = None,
) -> HandlerOutput:
    """Wrap observations and their provenance as a HandlerOutput for IndicatorSignal tasks."""
    signal = IndicatorSignal(owner_agent=owner_agent, observations=list(observations))
    return HandlerOutput(
        result=signal.model_dump(mode="json"),
        sources=list(sources),
        metadata={"note": note} if note else {},
    )
