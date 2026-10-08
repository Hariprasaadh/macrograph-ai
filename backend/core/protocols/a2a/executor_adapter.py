"""Exposes every registered AgentExecutor as the A2A `sector_analysis` task."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .exceptions import A2AException, AgentUnavailableError
from .messages import A2ACallContext, A2ARequest, HandlerOutput
from .models import TaskRequest, TaskState
from .provenance import provenance_from_artifact
from .registry import AgentRegistry

SECTOR_ANALYSIS = "sector_analysis"
A2A_CONTEXT_KEY = "_a2a"


class SectorAnalysisParams(BaseModel):
    """Parameters for a full sector analysis; extra keys pass through to the executor."""
    model_config = ConfigDict(extra="allow")

    query: str = Field(min_length=1, max_length=2000)


class ExecutorTaskHandler:
    """Runs a sector's AgentExecutor through the registry and re-packages its artifacts."""

    def __init__(self, registry: AgentRegistry, agent_id: str) -> None:
        self._registry = registry
        self._agent_id = agent_id

    async def __call__(self, request: A2ARequest, ctx: A2ACallContext) -> HandlerOutput:
        card = self._registry.get_agent(self._agent_id)
        if card is None:
            raise AgentUnavailableError(f"Agent '{self._agent_id}' is not registered.")
        params: dict[str, Any] = dict(request.parameters)
        query = str(params.pop("query"))
        task = TaskRequest(
            task_id=request.request_id,
            query=query,
            skills_required=list(params.pop("skills_required", [])),
            parameters={**params, A2A_CONTEXT_KEY: ctx.model_dump(mode="json")},
        )
        response = await self._registry.execute_task_async(card.name, task)
        if response.status != TaskState.COMPLETED:
            raise A2AException(response.error or f"Executor finished in state '{response.status.value}'.")

        artifacts = [a.model_dump(mode="json") for a in response.artifacts]
        sources = [
            src
            for art in response.artifacts
            for src in provenance_from_artifact(art.content, card.name, art.name, art.provenance_hash)
        ]
        messages = [
            {"role": m.role, "text": part.content if isinstance(part.content, str) else None}
            for m in response.messages for part in m.parts
        ]
        return HandlerOutput(
            result={"artifacts": artifacts, "messages": messages},
            sources=sources,
            metadata={"agent_card": card.name},
        )
