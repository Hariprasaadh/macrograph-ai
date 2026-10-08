"""A2A server: validates, authorizes and executes A2ARequests against registered handlers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import time
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, ValidationError

from core.config import settings

from .dependencies import is_allowed
from .exceptions import (
    A2AException,
    A2ATimeoutError,
    AgentNotFoundError,
    AgentUnavailableError,
    DependencyNotAllowedError,
    ErrorCode,
    InvalidRequestError,
    InvalidResponseError,
    UnsupportedCapabilityError,
)
from .messages import (
    A2ACallContext,
    A2AErrorInfo,
    A2ARequest,
    A2AResponse,
    HandlerOutput,
)
from .middleware import DelegationGuard, log_interaction
from .registry import AgentRegistry, registry as default_registry
from .trace import TraceStore, trace_store as default_trace_store

logger = logging.getLogger("macrograph.a2a")

Handler = Callable[[A2ARequest, A2ACallContext], Awaitable[HandlerOutput]]


@dataclass(frozen=True)
class TaskContract:
    """A registered task: handler plus optional typed parameter and result schemas."""
    handler: Handler
    params_model: Optional[type[BaseModel]] = None
    result_model: Optional[type[BaseModel]] = None
    description: str = ""


class A2AServer:
    """Single enforcement point for the A2A protocol rules."""

    def __init__(
        self,
        registry: AgentRegistry,
        trace: TraceStore,
        guard: Optional[DelegationGuard] = None,
        default_timeout: Optional[float] = None,
    ) -> None:
        self.registry = registry
        self.trace = trace
        self.guard = guard or DelegationGuard(settings.A2A_MAX_DEPTH, settings.A2A_MAX_HOPS)
        self.default_timeout = default_timeout or settings.A2A_REQUEST_TIMEOUT
        self._contracts: dict[tuple[str, str], TaskContract] = {}

    def register_handler(
        self,
        agent_id: str,
        task: str,
        handler: Handler,
        *,
        params_model: Optional[type[BaseModel]] = None,
        result_model: Optional[type[BaseModel]] = None,
        description: str = "",
    ) -> None:
        card = self.registry.get_agent(agent_id)
        if card is None:
            raise AgentNotFoundError(f"Cannot register handler: agent '{agent_id}' is not in the registry.")
        self._contracts[(agent_id, task)] = TaskContract(handler, params_model, result_model, description)
        if task not in card.supported_tasks:
            card.supported_tasks.append(task)

    def task_contract(self, agent_id: str, task: str) -> Optional[TaskContract]:
        return self._contracts.get((agent_id, task))

    async def handle(self, request: A2ARequest) -> A2AResponse:
        """Execute a request. Never raises: every failure becomes a structured response."""
        started = time.perf_counter()
        hops, duplicate_of = self.trace.begin(request)
        try:
            response = await self._dispatch(request, hops, duplicate_of)
        except A2AException as exc:
            response = self._failure(request, A2AErrorInfo.from_exception(exc, request.receiver_agent))
        except Exception as exc:  # handler bug or unexpected data-layer failure
            logger.exception("[A2A] unhandled error request_id=%s receiver=%s task=%s",
                             request.request_id, request.receiver_agent, request.task)
            response = self._failure(request, A2AErrorInfo(
                code=ErrorCode.AGENT_ERROR,
                message=f"Agent '{request.receiver_agent}' failed while running '{request.task}' ({type(exc).__name__}).",
                agent=request.receiver_agent,
            ))
        duration_ms = (time.perf_counter() - started) * 1000
        self.trace.finish(request, response, duration_ms)
        log_interaction(request, response, duration_ms)
        return response

    async def _dispatch(self, request: A2ARequest, hops: int, duplicate_of: Optional[str]) -> A2AResponse:
        self.guard.check(request, hops, duplicate_of)
        self.trace.remember(request)
        if not is_allowed(request.sender_agent, request.receiver_agent, request.task):
            raise DependencyNotAllowedError(
                f"'{request.sender_agent}' has no declared A2A dependency on "
                f"'{request.receiver_agent}' for task '{request.task}'."
            )
        card = self.registry.get_agent(request.receiver_agent)
        if card is None:
            raise AgentNotFoundError(f"Agent '{request.receiver_agent}' is not registered.")
        if request.task not in card.supported_tasks:
            raise UnsupportedCapabilityError(
                f"Agent '{request.receiver_agent}' does not support task '{request.task}'. "
                f"Supported: {sorted(card.supported_tasks)}."
            )
        contract = self._contracts.get((request.receiver_agent, request.task))
        if contract is None:
            raise AgentUnavailableError(
                f"Agent '{request.receiver_agent}' advertises '{request.task}' but has no active handler."
            )
        if contract.params_model is not None:
            try:
                contract.params_model.model_validate(request.parameters)
            except ValidationError as exc:
                raise InvalidRequestError(f"Invalid parameters for '{request.task}': {exc.errors()[0]['msg']}") from exc

        ctx = A2ACallContext(
            conversation_id=request.conversation_id,
            request_id=request.request_id,
            agent_id=request.receiver_agent,
            depth=request.depth,
            call_chain=(request.call_chain or (request.sender_agent,)) + (request.receiver_agent,),
        )
        timeout = request.timeout_seconds or self.default_timeout
        try:
            output = await asyncio.wait_for(contract.handler(request, ctx), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise A2ATimeoutError(
                f"Agent '{request.receiver_agent}' did not respond within {timeout:g}s."
            ) from exc
        return self._build_response(request, contract, output)

    def _build_response(self, request: A2ARequest, contract: TaskContract, output: object) -> A2AResponse:
        if not isinstance(output, HandlerOutput):
            raise InvalidResponseError(
                f"Handler for '{request.task}' returned {type(output).__name__}, expected HandlerOutput."
            )
        if contract.result_model is not None:
            try:
                contract.result_model.model_validate(output.result)
            except ValidationError as exc:
                raise InvalidResponseError(
                    f"Result of '{request.task}' violates {contract.result_model.__name__}: {exc.errors()[0]['msg']}"
                ) from exc
        if not output.sources:
            raise InvalidResponseError(
                f"Result of '{request.task}' carries no source provenance (No Source, No Answer)."
            )
        return A2AResponse(
            request_id=request.request_id,
            sender_agent=request.receiver_agent,
            receiver_agent=request.sender_agent,
            status=output.status,
            result=output.result,
            sources=output.sources,
            errors=output.errors,
            follow_ups=output.follow_ups,
            metadata={**output.metadata, "conversation_id": request.conversation_id, "task": request.task},
        )

    @staticmethod
    def _failure(request: A2ARequest, error: A2AErrorInfo) -> A2AResponse:
        return A2AResponse(
            request_id=request.request_id,
            sender_agent=request.receiver_agent,
            receiver_agent=request.sender_agent,
            status="failed",
            errors=[error],
            metadata={"conversation_id": request.conversation_id, "task": request.task},
        )


a2a_server = A2AServer(default_registry, default_trace_store)
