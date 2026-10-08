"""Turns A2A trace data into UI events for the streaming chat endpoint."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping

from core.protocols.a2a import agent_registry

_TASK_LABELS = {
    "sector_analysis": "sector analysis",
    "repo_rate": "repo rate",
    "cpi_headline": "headline CPI",
    "bank_credit_growth": "bank credit growth",
}


def _label(agent_id: str) -> str:
    card = agent_registry.get_agent(agent_id)
    return card.name if card else agent_id


def _task_label(task: str) -> str:
    return _TASK_LABELS.get(task, task.replace("_", " "))


def _describe(node: Mapping[str, Any]) -> tuple[str, str]:
    """(title, detail) for one trace node in its current state."""
    sender, receiver, task = node["sender_agent"], node["receiver_agent"], node["task"]
    title = f"A2A {sender} to {receiver}: {_task_label(task)}"
    status = node["status"]
    if status == "pending":
        return title, f"Request {node['request_id']} dispatched to {_label(receiver)}."
    duration = node.get("duration_ms")
    timing = f" in {duration / 1000:.1f}s" if isinstance(duration, (int, float)) else ""
    if status == "success":
        return title, f"{_label(receiver)} responded{timing}."
    if status == "partial":
        return title, f"{_label(receiver)} returned partial data{timing}."
    codes = ", ".join(node.get("error_codes") or []) or status
    return title, f"{_label(receiver)} did not return data{timing}: {codes}."


def trace_step_events(
    trace: Iterable[Mapping[str, Any]],
    emitted: MutableMapping[str, str],
    first_step: int,
) -> list[dict[str, Any]]:
    """Step events for trace nodes that are new or whose status changed since the last call.

    `emitted` maps request_id to the last status sent; it is updated in place.
    """
    events: list[dict[str, Any]] = []
    step = first_step
    for node in trace:
        request_id = node["request_id"]
        if emitted.get(request_id) == node["status"]:
            continue
        emitted[request_id] = node["status"]
        title, detail = _describe(node)
        state = {"pending": "running", "success": "completed", "partial": "partial"}.get(
            node["status"], "failed")
        events.append({
            "type": "step", "step": step, "agent": node["receiver_agent"],
            "request_id": request_id, "status": state, "title": title, "detail": detail,
        })
        step += 1
    return events


def a2a_summary(final_state: Mapping[str, Any]) -> dict[str, Any]:
    """Compact A2A block for the chat `done` payload."""
    return {
        "conversation_id": final_state.get("conversation_id"),
        "routed_agents": final_state.get("routed_agents") or [],
        "routing_method": final_state.get("routing_method"),
        "status": final_state.get("status"),
        "errors": final_state.get("a2a_errors") or [],
        "sources": final_state.get("a2a_sources") or [],
        "trace": final_state.get("a2a_trace") or [],
    }
