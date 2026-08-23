"""Standard Agent-to-Agent (A2A) Protocol Data Models.

Conforms to standard A2A specification for Agent Discovery (Agent Cards),
Task Lifecycle Management, Multi-Part Messaging, and Cryptographically Hashed Artifacts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Standard A2A Task execution lifecycle states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Alias for backward compatibility
TaskStatus = TaskState


class AgentSkill(BaseModel):
    """Specific analytical capability advertised in an Agent Card."""
    id: str = Field(..., description="Unique skill identifier, e.g. national_income_analysis")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="Detailed description of capability")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    examples: List[str] = Field(default_factory=list, description="Sample user query triggers")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Expected input JSON Schema")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Expected output JSON Schema")


class AgentCapabilities(BaseModel):
    """Supported agent capabilities and protocol modalities."""
    streaming: bool = Field(default=True, description="Supports SSE real-time streaming")
    push_notifications: bool = Field(default=False, description="Supports webhook push notifications")
    stateful_sessions: bool = Field(default=True, description="Supports multi-turn task memory")


class AgentCard(BaseModel):
    """A2A Agent Card specification document hosted at /.well-known/agent.json."""
    name: str = Field(..., description="Agent Name")
    description: str = Field(..., description="Detailed agent capability description")
    url: str = Field(..., description="Base URL of the Agent endpoint")
    version: str = Field(default="1.0.0", description="Agent version string")
    default_input_mode: str = Field(default="json", description="Default input modality (text/json)")
    default_output_mode: str = Field(default="artifact", description="Default output modality (text/artifact)")
    capabilities: List[str] = Field(default_factory=list, description="List of capability tags")
    skills: List[AgentSkill] = Field(default_factory=list, description="Supported skills")
    protocol_version: str = Field(default="1.0.0", description="A2A Protocol version")
    auth_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "none"},
        description="Authentication specifications"
    )


class A2AMessagePart(BaseModel):
    """Part of a multi-part message supporting text, json, or markdown formats."""
    kind: str = Field(default="text", description="Kind of content: text, json, markdown, image, chart")
    content: Union[str, Dict[str, Any], List[Any]] = Field(..., description="Payload content")


class A2AMessage(BaseModel):
    """Inter-agent message exchanged during task execution."""
    role: str = Field(..., description="Role of sender: user, orchestrator, agent")
    parts: List[A2AMessagePart] = Field(default_factory=list, description="Message content parts")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )


class A2AArtifact(BaseModel):
    """Structured output artifact produced during task execution with data provenance."""
    artifact_id: str = Field(
        default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}",
        description="Unique artifact ID"
    )
    name: str = Field(..., description="Descriptive name of artifact")
    type: str = Field(..., description="Type of artifact: json, markdown, spreadsheet, chart")
    content: Union[Dict[str, Any], str, List[Any]] = Field(..., description="Data content of the artifact")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary metadata")
    provenance_hash: Optional[str] = Field(default=None, description="SHA-256 hash of content for data integrity")

    def model_post_init(self, __context: Any) -> None:
        if self.provenance_hash is None:
            if isinstance(self.content, (dict, list)):
                dump = json.dumps(self.content, sort_keys=True, default=str)
            else:
                dump = str(self.content)
            self.provenance_hash = hashlib.sha256(dump.encode("utf-8")).hexdigest()[:16]


class TaskRequest(BaseModel):
    """Task submission request sent to an A2A agent."""
    task_id: str = Field(
        default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}",
        description="Unique task identifier"
    )
    query: str = Field(..., description="Prompt or query instructions for the agent")
    skills_required: List[str] = Field(default_factory=list, description="Required agent skill IDs")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task execution arguments")


class TaskResponse(BaseModel):
    """Unified task state and result response."""
    task_id: str
    status: TaskState
    messages: List[A2AMessage] = Field(default_factory=list)
    artifacts: List[A2AArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


class TaskStatusUpdateEvent(BaseModel):
    """Event fired when task status transitions or emits progress."""
    task_id: str
    status: TaskState
    message: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskArtifactUpdateEvent(BaseModel):
    """Event fired when a new artifact is attached to a task."""
    task_id: str
    artifact: A2AArtifact
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RequestContext(BaseModel):
    """Execution context passed to an AgentExecutor."""
    task_id: str
    request: TaskRequest
    metadata: Dict[str, Any] = Field(default_factory=dict)
