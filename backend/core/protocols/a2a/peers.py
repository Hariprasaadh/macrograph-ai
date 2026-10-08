"""Helpers for sector agents that need indicators owned by peer sectors, via A2A only."""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence

from pydantic import ValidationError

from core.config import settings

from .client import A2AClient
from .dependencies import dependencies_for
from .executor_adapter import A2A_CONTEXT_KEY
from .messages import A2ACallContext, A2AResponse, IndicatorObservation, IndicatorSignal

logger = logging.getLogger("macrograph.a2a")


def parent_context(parameters: Optional[Mapping[str, Any]]) -> Optional[A2ACallContext]:
    """Recover the delegation context an executor received through TaskRequest.parameters."""
    raw = (parameters or {}).get(A2A_CONTEXT_KEY)
    if not raw:
        return None
    try:
        return A2ACallContext.model_validate(raw)
    except ValidationError:
        logger.warning("Ignoring malformed A2A context in task parameters.")
        return None


async def request_peer_signals(
    sender: str,
    needs: Sequence[tuple[str, str]],
    *,
    parent: Optional[A2ACallContext] = None,
    question: Optional[str] = None,
    client: Optional[A2AClient] = None,
) -> list[A2AResponse]:
    """Ask peers for (receiver_agent, task) pairs concurrently.

    Failures stay in the returned responses; callers decide how to degrade.
    """
    a2a = client or A2AClient(sender)
    parameters = {"question": question[:500]} if question else {}
    requests = [
        a2a.build_request(receiver, task, parameters, parent=parent, timeout=settings.A2A_PEER_TIMEOUT)
        for receiver, task in needs
    ]
    return await a2a.send_many(requests)


def observations(responses: Sequence[A2AResponse]) -> dict[str, tuple[IndicatorObservation, A2AResponse]]:
    """Valid IndicatorObservations keyed by indicator_id, each with its originating response."""
    found: dict[str, tuple[IndicatorObservation, A2AResponse]] = {}
    for response in responses:
        if not response.ok:
            continue
        try:
            signal = IndicatorSignal.model_validate(response.result)
        except ValidationError:
            continue
        for obs in signal.observations:
            found[obs.indicator_id] = (obs, response)
    return found


def peer_context_lines(responses: Sequence[A2AResponse]) -> list[str]:
    """Markdown bullets that keep owner agent, value, period and source attached."""
    lines: list[str] = []
    for obs, response in observations(responses).values():
        src = response.sources[0] if response.sources else None
        source_text = f"{src.source_name}, {src.table or src.dataset or 'n/a'}" if src else "source unavailable"
        value = "unavailable" if obs.value is None else f"{obs.value:g} {obs.unit}".strip()
        lines.append(
            f"- {obs.label} (from {response.sender_agent} via A2A): {value} "
            f"[period {obs.observation_period or 'n/a'}; {source_text}]"
        )
    for response in responses:
        if not response.ok:
            codes = ", ".join(c.value for c in response.error_codes)
            lines.append(f"- Peer data unavailable from {response.sender_agent}: {codes}")
    return lines


def peer_records(responses: Sequence[A2AResponse]) -> list[dict[str, Any]]:
    """Structured peer data for JSON artifacts; keeps provenance and surfaces failures."""
    records: list[dict[str, Any]] = []
    for obs, response in observations(responses).values():
        records.append({
            "owner_agent": response.sender_agent,
            **obs.model_dump(),
            "sources": [s.model_dump(mode="json") for s in response.sources],
            "a2a_request_id": response.request_id,
        })
    for response in responses:
        if not response.ok:
            records.append({
                "owner_agent": response.sender_agent,
                "status": "unavailable",
                "errors": [e.model_dump(mode="json") for e in response.errors],
                "a2a_request_id": response.request_id,
            })
    return records


async def gather_peer_context(
    sender: str, parameters: Optional[Mapping[str, Any]], query: Optional[str]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Request every declared dependency of `sender` and return (markdown lines, structured records)."""
    needs = [(d.provider, d.task) for d in dependencies_for(sender)]
    if not needs:
        return [], []
    responses = await request_peer_signals(
        sender, needs, parent=parent_context(parameters), question=query
    )
    return peer_context_lines(responses), peer_records(responses)
