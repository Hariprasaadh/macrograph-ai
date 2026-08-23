"""A2A Task Lifecycle and State Management Engine."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from .models import (
    A2AArtifact,
    A2AMessage,
    RequestContext,
    TaskRequest,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)


class EventQueue:
    """Async event queue for pushing task updates to streaming consumers."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._subscribers: List[asyncio.Queue[Any]] = []

    async def emit(self, event: Any) -> None:
        await self._queue.put(event)
        for sub in self._subscribers:
            await sub.put(event)

    async def get(self) -> Any:
        return await self._queue.get()

    def subscribe(self) -> asyncio.Queue[Any]:
        sub_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._subscribers.append(sub_queue)
        return sub_queue

    def unsubscribe(self, sub_queue: asyncio.Queue[Any]) -> None:
        if sub_queue in self._subscribers:
            self._subscribers.remove(sub_queue)

    def empty(self) -> bool:
        return self._queue.empty()


class AgentExecutor:
    """Abstract base class for an A2A Agent Executor."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        raise NotImplementedError("Subclasses must implement execute()")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        raise NotImplementedError("Subclasses must implement cancel()")


class TaskManager:
    """Manages lifecycle, in-memory state, and streaming subscriptions for A2A tasks."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskResponse] = {}
        self._event_queues: Dict[str, EventQueue] = {}
        self._running_tasks: Dict[str, asyncio.Task[Any]] = {}

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        return self._tasks.get(task_id)

    def get_event_queue(self, task_id: str) -> EventQueue:
        if task_id not in self._event_queues:
            self._event_queues[task_id] = EventQueue()
        return self._event_queues[task_id]

    def create_task(self, request: TaskRequest) -> TaskResponse:
        now = datetime.now(timezone.utc).isoformat()
        response = TaskResponse(
            task_id=request.task_id,
            status=TaskState.SUBMITTED,
            created_at=now,
            updated_at=now,
        )
        self._tasks[request.task_id] = response
        return response

    async def run_task(
        self,
        executor: AgentExecutor,
        request: TaskRequest,
        background: bool = False
    ) -> TaskResponse:
        task_id = request.task_id
        if task_id not in self._tasks:
            self.create_task(request)

        event_queue = self.get_event_queue(task_id)
        context = RequestContext(task_id=task_id, request=request)

        async def _execution_wrapper() -> TaskResponse:
            try:
                result = await executor.execute(context, event_queue)
                self._tasks[task_id] = result
                return result
            except asyncio.CancelledError:
                cancelled_resp = TaskResponse(
                    task_id=task_id,
                    status=TaskState.CANCELLED,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    error="Task was cancelled by user."
                )
                self._tasks[task_id] = cancelled_resp
                return cancelled_resp
            except Exception as err:
                failed_resp = TaskResponse(
                    task_id=task_id,
                    status=TaskState.FAILED,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    error=str(err)
                )
                self._tasks[task_id] = failed_resp
                await event_queue.emit(
                    TaskStatusUpdateEvent(
                        task_id=task_id,
                        status=TaskState.FAILED,
                        message=f"Task execution failed: {err}"
                    )
                )
                return failed_resp

        if background:
            async_task = asyncio.create_task(_execution_wrapper())
            self._running_tasks[task_id] = async_task
            return self._tasks[task_id]
        else:
            return await _execution_wrapper()

    async def cancel_task(self, task_id: str, executor: Optional[AgentExecutor] = None) -> bool:
        if task_id not in self._tasks:
            return False

        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()

        if executor:
            event_queue = self.get_event_queue(task_id)
            context = RequestContext(task_id=task_id, request=TaskRequest(task_id=task_id, query=""))
            await executor.cancel(context, event_queue)

        existing = self._tasks[task_id]
        existing.status = TaskState.CANCELLED
        existing.updated_at = datetime.now(timezone.utc).isoformat()
        self._tasks[task_id] = existing
        return True
