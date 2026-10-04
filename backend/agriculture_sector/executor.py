"""Agriculture A2A findings executor; retrieval stays behind Agriculture MCP."""
from __future__ import annotations

from core.protocols.a2a import (
    A2AArtifact, A2AMessage, A2AMessagePart, AgentExecutor, EventQueue,
    RequestContext, TaskArtifactUpdateEvent, TaskResponse, TaskState, TaskStatusUpdateEvent,
)
from .agent import agriculture_agent_node
from .agent_card import get_agent_card


class AgricultureAgentExecutor(AgentExecutor):
    get_agent_card = staticmethod(get_agent_card)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        await event_queue.emit(TaskStatusUpdateEvent(
            task_id=context.task_id, status=TaskState.WORKING,
            message="Analyzing agriculture evidence through Agriculture MCP.",
        ))
        try:
            result = await agriculture_agent_node({
                "query": context.query or "",
                "parameters": context.request.parameters if context.request else {},
            })
            content = {
                "agent": "agriculture_sector", "status": result["agriculture_sector_status"],
                "findings": result["agriculture_sector_findings"],
                "citations": result["agriculture_sector_citations"],
                "errors": result["agriculture_sector_errors"],
                "analysis": result["agriculture_sector_analysis"],
            }
            artifact = A2AArtifact(name="Agriculture findings", type="json", content=content)
            await event_queue.emit(TaskArtifactUpdateEvent(task_id=context.task_id, artifact=artifact))
            await event_queue.emit(TaskStatusUpdateEvent(
                task_id=context.task_id, status=TaskState.COMPLETED,
                message=f"Agriculture analysis finished: {content['status']}",
            ))
            return TaskResponse(
                task_id=context.task_id, status=TaskState.COMPLETED, artifacts=[artifact],
                messages=[A2AMessage(role="agent", parts=[
                    A2AMessagePart(kind="markdown", content=content["analysis"])])],
            )
        except Exception:
            await event_queue.emit(TaskStatusUpdateEvent(
                task_id=context.task_id, status=TaskState.FAILED, message="Agriculture analysis failed"))
            return TaskResponse(task_id=context.task_id, status=TaskState.FAILED,
                                error="Agriculture analysis failed; no unsupported findings returned")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(TaskStatusUpdateEvent(
            task_id=context.task_id, status=TaskState.CANCELLED, message="Agriculture task cancelled"))
        return True


AgricultureRuralAgentExecutor = AgricultureAgentExecutor
