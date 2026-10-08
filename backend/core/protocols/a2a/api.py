"""HTTP surface for the A2A runtime: discovery, request submission and trace inspection."""
from __future__ import annotations

import hmac
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from core.config import settings

from .messages import A2ARequest, A2AResponse
from .registry import registry
from .server import a2a_server
from .trace import trace_store

router = APIRouter(prefix="/a2a/v1", tags=["A2A Protocol"])

# Requests arriving over HTTP are external callers: they cannot claim a sector identity.
HTTP_SENDER = "gateway"


def _authorize(api_key: Optional[str]) -> None:
    expected = settings.A2A_API_KEY.get_secret_value()
    if expected and not hmac.compare_digest(api_key or "", expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-A2A-Key.")


@router.get("/agents")
def list_agents(x_a2a_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Lists registered Agent Cards."""
    _authorize(x_a2a_key)
    return {"agents": [c.model_dump() for c in registry.list_agents()]}


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, x_a2a_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Returns one Agent Card by stable agent id."""
    _authorize(x_a2a_key)
    card = registry.get_agent(agent_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' is not registered.")
    return card.model_dump()


@router.get("/capabilities/{capability}")
def find_by_capability(capability: str, x_a2a_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Finds agents advertising a capability, supported task or skill id."""
    _authorize(x_a2a_key)
    return {"capability": capability, "agents": [c.agent_id for c in registry.find_by_capability(capability)]}


@router.post("/requests", response_model=A2AResponse)
async def submit_request(request: A2ARequest, x_a2a_key: Optional[str] = Header(default=None)) -> A2AResponse:
    """Executes an A2ARequest. Protocol failures are returned as status=failed responses."""
    if not settings.A2A_API_KEY.get_secret_value() and not settings.A2A_ALLOW_ANONYMOUS_REQUESTS:
        raise HTTPException(
            status_code=403,
            detail="Request submission is disabled: set A2A_API_KEY (or A2A_ALLOW_ANONYMOUS_REQUESTS=true for local use).",
        )
    _authorize(x_a2a_key)
    if request.sender_agent != HTTP_SENDER:
        raise HTTPException(status_code=403, detail=f"HTTP callers must use sender_agent='{HTTP_SENDER}'.")
    return await a2a_server.handle(request)


@router.get("/traces/{conversation_id}")
def get_trace(conversation_id: str, x_a2a_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Reconstructs the delegation graph of a conversation."""
    _authorize(x_a2a_key)
    nodes = trace_store.get_trace(conversation_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Unknown or evicted conversation_id.")
    return {"conversation_id": conversation_id, "requests": nodes,
            "tree": trace_store.get_tree(conversation_id)}
