"""Server-Sent Events (SSE) Streaming for A2A Tasks."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from sse_starlette.sse import ServerSentEvent

from .lifecycle import EventQueue
from .models import TaskState, TaskStatusUpdateEvent, TaskArtifactUpdateEvent


async def task_event_stream(
    event_queue: EventQueue,
    task_id: str,
    timeout_seconds: float = 60.0
) -> AsyncGenerator[ServerSentEvent, None]:
    """Generates SSE events from an EventQueue until task completes or times out."""
    sub_queue = event_queue.subscribe()
    try:
        # Initial connect event
        yield ServerSentEvent(
            data=json.dumps({"event": "connected", "task_id": task_id}),
            event="connect"
        )

        start_time = asyncio.get_event_loop().time()
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                yield ServerSentEvent(
                    data=json.dumps({"event": "timeout", "task_id": task_id}),
                    event="timeout"
                )
                break

            try:
                event = await asyncio.wait_for(sub_queue.get(), timeout=min(5.0, remaining))
            except asyncio.TimeoutError:
                # Send ping/keep-alive comment
                yield ServerSentEvent(comment="keep-alive")
                continue

            if isinstance(event, TaskStatusUpdateEvent):
                yield ServerSentEvent(
                    data=event.model_dump_json(),
                    event="status_update"
                )
                if event.status in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                    break

            elif isinstance(event, TaskArtifactUpdateEvent):
                yield ServerSentEvent(
                    data=event.model_dump_json(),
                    event="artifact_update"
                )

            else:
                yield ServerSentEvent(
                    data=json.dumps(event, default=str),
                    event="custom_event"
                )

    finally:
        event_queue.unsubscribe(sub_queue)
