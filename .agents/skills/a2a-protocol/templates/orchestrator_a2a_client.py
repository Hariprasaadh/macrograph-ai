"""
Template: A2A Client for Macrograph-AI Orchestrator.

Copy this to backend/core/orchestrator/a2a_client.py and adapt as needed.
This client is used by the Orchestrator LangGraph node to delegate tasks
to sector agents via the A2A protocol.

Architecture:
  OrchestratorNode → a2a_client.send_task() → Sector A2A Server → Artifact
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    SendMessageRequest,
    TextPart,
)

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sector agent URL registry
# ---------------------------------------------------------------------------

SECTOR_AGENT_URLS: dict[str, str] = {
    "prices": settings.PRICES_SECTOR_URL.replace("/prices-sector", "").replace(":8000", ":8001"),
    "monetary": settings.MONETARY_SECTOR_URL.replace("/monetary-sector", "").replace(":8000", ":8002"),
    "fiscal": settings.FISCAL_SECTOR_URL.replace("/fiscal-sector", "").replace(":8000", ":8003"),
    "external": settings.EXTERNAL_SECTOR_URL.replace("/external-sector", "").replace(":8000", ":8004"),
    "agriculture": settings.AGRICULTURE_SECTOR_URL.replace("/agriculture-sector", "").replace(":8000", ":8005"),
    "real": settings.REAL_SECTOR_URL.replace("/real-sector", "").replace(":8000", ":8006"),
    "labour": settings.LABOUR_SECTOR_URL.replace("/labour-sector", "").replace(":8000", ":8007"),
    "capital_market": settings.CAPITAL_MARKETS_URL.replace("/capital-markets", "").replace(":8000", ":8008"),
}


# ---------------------------------------------------------------------------
# Card resolver — with caching
# ---------------------------------------------------------------------------

_card_cache: dict[str, AgentCard] = {}


async def get_agent_card(sector: str, http_client: httpx.AsyncClient) -> AgentCard:
    """
    Fetch and cache the AgentCard for a sector agent.

    Raises:
        ValueError: If the sector is not registered.
        httpx.HTTPError: If the AgentCard endpoint is unreachable.
    """
    if sector in _card_cache:
        return _card_cache[sector]

    url = SECTOR_AGENT_URLS.get(sector)
    if not url:
        raise ValueError(f"Unknown sector: '{sector}'. Registered sectors: {list(SECTOR_AGENT_URLS)}")

    resolver = A2ACardResolver(httpx_client=http_client, base_url=url)
    card = await resolver.get_agent_card()
    _card_cache[sector] = card
    logger.info("Discovered AgentCard for sector '%s': %s v%s", sector, card.name, card.version)
    return card


# ---------------------------------------------------------------------------
# Task sender — synchronous (non-streaming)
# ---------------------------------------------------------------------------


async def send_task(
    sector: str,
    query: str,
    context_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    """
    Send a task to a sector agent via A2A message/send.

    Returns a dict with:
      - "text": str — the primary text finding
      - "data": dict | None — any structured data artifact
      - "sector": str — the responding sector
      - "agent_name": str — the responding agent's name

    Raises:
        ValueError: If sector is unknown or response has no artifacts.
        httpx.HTTPError: If the agent is unreachable.
    """
    import uuid
    msg_id = message_id or f"msg-{uuid.uuid4().hex[:8]}"
    ctx_id = context_id or f"ctx-{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        card = await get_agent_card(sector=sector, http_client=http_client)
        client = A2AClient(httpx_client=http_client, agent_card=card)

        request = SendMessageRequest(
            id=f"req-{uuid.uuid4().hex[:8]}",
            params=MessageSendParams(
                message=Message(
                    role="user",
                    messageId=msg_id,
                    contextId=ctx_id,
                    parts=[Part(root=TextPart(text=query))],
                )
            ),
        )

        logger.info("Sending A2A task to '%s': %s", card.name, query[:100])
        response = await client.send_message(request)

        task = response.root.result.root.task
        if not task.artifacts:
            raise ValueError(f"Agent '{card.name}' returned no artifacts for query: {query!r}")

        text_result = ""
        data_result: dict | None = None

        for artifact in task.artifacts:
            for part in artifact.parts or []:
                if hasattr(part.root, "text") and not text_result:
                    text_result = part.root.text
                elif hasattr(part.root, "data") and data_result is None:
                    data_result = part.root.data

        return {
            "text": text_result,
            "data": data_result,
            "sector": sector,
            "agent_name": card.name,
        }


# ---------------------------------------------------------------------------
# Streaming task sender
# ---------------------------------------------------------------------------


async def stream_task(
    sector: str,
    query: str,
    context_id: str | None = None,
) -> str:
    """
    Send a task to a sector agent via A2A message/stream and collect all text.

    Returns the accumulated text from all artifact streaming events.
    Verifies capability before sending.
    """
    import uuid
    ctx_id = context_id or f"ctx-{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        card = await get_agent_card(sector=sector, http_client=http_client)

        if not (card.capabilities and card.capabilities.streaming):
            raise ValueError(f"Agent '{card.name}' does not support streaming.")

        client = A2AClient(httpx_client=http_client, agent_card=card)
        request = SendMessageRequest(
            id=f"req-{uuid.uuid4().hex[:8]}",
            params=MessageSendParams(
                message=Message(
                    role="user",
                    messageId=f"msg-{uuid.uuid4().hex[:8]}",
                    contextId=ctx_id,
                    parts=[Part(root=TextPart(text=query))],
                )
            ),
        )

        accumulated_text = ""
        async with client.send_message_streaming(request) as stream:
            async for event in stream:
                result = event.root.result
                if hasattr(result.root, "artifact"):
                    for part in result.root.artifact.parts or []:
                        if hasattr(part.root, "text"):
                            accumulated_text += part.root.text
                elif hasattr(result.root, "status") and result.root.final:
                    break

        return accumulated_text
