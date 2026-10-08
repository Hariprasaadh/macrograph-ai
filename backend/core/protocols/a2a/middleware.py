"""Delegation guards and structured logging shared by the A2A server and client."""
from __future__ import annotations

import logging
from typing import Optional

from .exceptions import (
    CircularDelegationError,
    DuplicateRequestError,
    InvalidRequestError,
    MaxDepthExceededError,
    MaxHopsExceededError,
)
from .messages import A2ARequest, A2AResponse

logger = logging.getLogger("macrograph.a2a")


class DelegationGuard:
    """Prevents runaway or cyclic agent delegation."""

    def __init__(self, max_depth: int, max_hops: int) -> None:
        self.max_depth = max_depth
        self.max_hops = max_hops

    def check(self, request: A2ARequest, hops: int, duplicate_of: Optional[str]) -> None:
        chain = request.call_chain or (request.sender_agent,)
        if chain[-1] != request.sender_agent:
            raise InvalidRequestError(
                f"call_chain must end with sender_agent '{request.sender_agent}', got {list(chain)}."
            )
        if request.depth > self.max_depth:
            raise MaxDepthExceededError(
                f"Delegation depth {request.depth} exceeds the maximum of {self.max_depth}."
            )
        if request.receiver_agent in chain:
            raise CircularDelegationError(
                f"'{request.receiver_agent}' is already on the delegation chain {list(chain)}."
            )
        if hops > self.max_hops:
            raise MaxHopsExceededError(
                f"Conversation '{request.conversation_id}' exceeded {self.max_hops} A2A hops."
            )
        if duplicate_of is not None:
            raise DuplicateRequestError(
                f"Equivalent request '{duplicate_of}' was already issued in this conversation."
            )


def log_interaction(request: A2ARequest, response: A2AResponse, duration_ms: float) -> None:
    """One structured line per completed A2A interaction."""
    codes = ",".join(c.value for c in response.error_codes) or "-"
    level = logging.INFO if response.status != "failed" else logging.WARNING
    logger.log(
        level,
        "[A2A] request_id=%s conversation_id=%s parent=%s sender=%s receiver=%s task=%s "
        "depth=%d status=%s errors=%s sources=%d duration_ms=%.1f",
        request.request_id, request.conversation_id, request.parent_request_id or "-",
        request.sender_agent, request.receiver_agent, request.task,
        request.depth, response.status, codes, len(response.sources), duration_ms,
    )
