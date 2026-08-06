"""Protocols package for A2A (Agent-to-Agent) and MCP (Model Context Protocol)."""
from __future__ import annotations

from .a2a_protocol import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentExecutor,
    AgentSkill,
    EventQueue,
    RequestContext,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from .mcp_protocol import (
    MCPJsonRpcRequest,
    MCPJsonRpcResponse,
    MCPTool,
    handle_mcp_rpc,
)

__all__ = [
    "A2AArtifact",
    "A2AMessage",
    "A2AMessagePart",
    "AgentCard",
    "AgentExecutor",
    "AgentSkill",
    "EventQueue",
    "RequestContext",
    "TaskRequest",
    "TaskResponse",
    "TaskStatus",
    "TaskStatusUpdateEvent",
    "TaskArtifactUpdateEvent",
    "MCPJsonRpcRequest",
    "MCPJsonRpcResponse",
    "MCPTool",
    "handle_mcp_rpc",
]
