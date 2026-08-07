from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    default_input_mode: str = "json"
    default_output_mode: str = "artifact"
    capabilities: List[str] = Field(default_factory=list)
    skills: List[AgentSkill] = Field(default_factory=list)
    auth_requirements: Dict[str, Any] = Field(default_factory=lambda: {"type": "none"})


class A2AMessagePart(BaseModel):
    kind: str = Field(default="text")
    content: Union[str, Dict[str, Any], List[Any]]


class A2AMessage(BaseModel):
    role: str
    parts: List[A2AMessagePart] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class A2AArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}")
    name: str
    type: str
    content: Union[Dict[str, Any], str, List[Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    query: str
    skills_required: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    messages: List[A2AMessage] = Field(default_factory=list)
    artifacts: List[A2AArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


class TaskStatusUpdateEvent(BaseModel):
    task_id: str
    status: TaskStatus
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskArtifactUpdateEvent(BaseModel):
    task_id: str
    artifact: A2AArtifact
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RequestContext(BaseModel):
    task_id: str
    request: TaskRequest
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()

    async def emit(self, event: Any) -> None:
        await self._queue.put(event)

    async def get(self) -> Any:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()


class AgentExecutor:
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        raise NotImplementedError

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        raise NotImplementedError
