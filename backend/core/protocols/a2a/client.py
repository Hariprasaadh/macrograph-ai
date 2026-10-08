"""A2A client: request creation, discovery, timeout, retry, validation and context propagation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Protocol

from pydantic import ValidationError
from tenacity import AsyncRetrying, retry_if_result, stop_after_attempt, wait_exponential

from core.config import settings

from .exceptions import RETRYABLE_CODES, ErrorCode
from .messages import (
    A2ACallContext,
    A2AErrorInfo,
    A2ARequest,
    A2AResponse,
    new_id,
)
from .models import AgentCard
from .registry import AgentRegistry, registry as default_registry
from .server import A2AServer, a2a_server

logger = logging.getLogger("macrograph.a2a")

# Slack on top of the request timeout so the server's own timeout response wins the race.
_TRANSPORT_GRACE_SECONDS = 2.0


class Transport(Protocol):
    """Delivers a request to the agent runtime. Swap for HTTP without touching callers."""

    async def send(self, request: A2ARequest) -> A2AResponse: ...


class InProcessTransport:
    """Default transport: agents live in the same gateway process."""

    def __init__(self, server: A2AServer) -> None:
        self._server = server

    async def send(self, request: A2ARequest) -> A2AResponse:
        return await self._server.handle(request)


def _failed(request_id: str, sender: str, receiver: str, code: ErrorCode, message: str) -> A2AResponse:
    return A2AResponse(
        request_id=request_id,
        sender_agent=receiver,
        receiver_agent=sender,
        status="failed",
        errors=[A2AErrorInfo(code=code, message=message, agent=receiver)],
    )


class A2AClient:
    """Sends A2A requests on behalf of one agent."""

    def __init__(
        self,
        agent_id: str,
        *,
        transport: Optional[Transport] = None,
        registry: Optional[AgentRegistry] = None,
        max_retries: Optional[int] = None,
        default_timeout: Optional[float] = None,
    ) -> None:
        self.agent_id = agent_id
        self._transport = transport or InProcessTransport(a2a_server)
        self._registry = registry or default_registry
        self._max_retries = settings.A2A_MAX_RETRIES if max_retries is None else max_retries
        self._default_timeout = default_timeout or settings.A2A_REQUEST_TIMEOUT

    def discover(self, capability: str) -> list[AgentCard]:
        """Agents advertising `capability`, excluding the caller."""
        return [c for c in self._registry.find_by_capability(capability) if c.agent_id != self.agent_id]

    def build_request(
        self,
        receiver: str,
        task: str,
        parameters: Optional[dict[str, Any]] = None,
        *,
        parent: Optional[A2ACallContext] = None,
        conversation_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> A2ARequest:
        if parent is not None:
            return A2ARequest(
                sender_agent=self.agent_id, receiver_agent=receiver, task=task,
                parameters=parameters or {}, context=context,
                conversation_id=parent.conversation_id, parent_request_id=parent.request_id,
                depth=parent.depth + 1, call_chain=parent.call_chain,
                timeout_seconds=timeout or self._default_timeout,
            )
        return A2ARequest(
            sender_agent=self.agent_id, receiver_agent=receiver, task=task,
            parameters=parameters or {}, context=context,
            conversation_id=conversation_id or new_id("conv"),
            depth=0, call_chain=(self.agent_id,),
            timeout_seconds=timeout or self._default_timeout,
        )

    async def send_request(
        self,
        receiver: str,
        task: str,
        parameters: Optional[dict[str, Any]] = None,
        *,
        parent: Optional[A2ACallContext] = None,
        conversation_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> A2AResponse:
        """Send one request. Always returns an A2AResponse; failures carry structured errors."""
        try:
            request = self.build_request(
                receiver, task, parameters, parent=parent,
                conversation_id=conversation_id, context=context, timeout=timeout,
            )
        except ValidationError as exc:
            return _failed(new_id("req"), self.agent_id, receiver, ErrorCode.INVALID_REQUEST,
                           f"Invalid A2A request: {exc.errors()[0]['msg']}")
        return await self.send(request, retries=retries)

    async def send(self, request: A2ARequest, *, retries: Optional[int] = None) -> A2AResponse:
        attempts = 1 + (self._max_retries if retries is None else retries)
        retrying = AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            retry=retry_if_result(lambda r: r.status == "failed" and any(c in RETRYABLE_CODES for c in r.error_codes)),
            retry_error_callback=lambda state: state.outcome.result(),
            reraise=False,
        )
        return await retrying(self._attempt, request)

    async def send_many(self, requests: list[A2ARequest], *, retries: Optional[int] = None) -> list[A2AResponse]:
        """Dispatch independent requests concurrently, preserving order."""
        return list(await asyncio.gather(*(self.send(r, retries=retries) for r in requests)))

    async def _attempt(self, request: A2ARequest) -> A2AResponse:
        timeout = (request.timeout_seconds or self._default_timeout) + _TRANSPORT_GRACE_SECONDS
        try:
            response = await asyncio.wait_for(self._transport.send(request), timeout=timeout)
        except asyncio.TimeoutError:
            return _failed(request.request_id, request.sender_agent, request.receiver_agent,
                           ErrorCode.AGENT_TIMEOUT,
                           f"No response from '{request.receiver_agent}' within {timeout:g}s.")
        except Exception as exc:  # transport-level failure, not an agent failure
            logger.warning("[A2A] transport failure request_id=%s receiver=%s: %s",
                           request.request_id, request.receiver_agent, exc)
            return _failed(request.request_id, request.sender_agent, request.receiver_agent,
                           ErrorCode.TRANSPORT_ERROR, f"{type(exc).__name__}: {exc}")
        return self._validate(request, response)

    @staticmethod
    def _validate(request: A2ARequest, response: object) -> A2AResponse:
        if not isinstance(response, A2AResponse):
            try:
                response = A2AResponse.model_validate(response)
            except ValidationError as exc:
                return _failed(request.request_id, request.sender_agent, request.receiver_agent,
                               ErrorCode.INVALID_RESPONSE, f"Malformed A2A response: {exc.errors()[0]['msg']}")
        if response.request_id != request.request_id or response.receiver_agent != request.sender_agent:
            return _failed(request.request_id, request.sender_agent, request.receiver_agent,
                           ErrorCode.INVALID_RESPONSE,
                           "Response correlation mismatch: request_id or receiver does not match the request.")
        return response


def get_client(agent_id: str) -> A2AClient:
    """Client bound to the shared in-process runtime."""
    return A2AClient(agent_id)
