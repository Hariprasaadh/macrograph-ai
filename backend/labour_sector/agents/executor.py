from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from core.protocols.a2a import A2AArtifact, A2AMessage, A2AMessagePart, AgentCard, AgentExecutor, AgentSkill, EventQueue, RequestContext, TaskArtifactUpdateEvent, TaskResponse, TaskState, TaskStatusUpdateEvent
from ..clients.labour_data_client import LabourDataClient
from .tools import LabourToolInput, LabourToolRegistry

class LabourEmploymentAgentExecutor(AgentExecutor):
    def __init__(self, client: LabourDataClient | None = None) -> None:
        self.client = client or LabourDataClient(); self.registry = LabourToolRegistry(self.client)
    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/labour-sector") -> AgentCard:
        schema = LabourToolInput.model_json_schema()
        skills = [AgentSkill(id="epfo_payroll_analysis", name="EPFO Payroll Analysis", description="Analyzes formal employment additions and momentum.", tags=["epfo", "employment"], examples=["How is formal employment changing?"], input_schema=schema), AgentSkill(id="unemployment_analysis", name="PLFS Unemployment Analysis", description="Reports the latest verified PLFS unemployment rate.", tags=["plfs", "unemployment"], examples=["What is the unemployment rate?"], input_schema=schema)]
        return AgentCard(name="Labour & Employment Macroeconomic Agent", description="Indian labour, formalization, and unemployment intelligence.", url=base_url, capabilities=["labour", "employment", "epfo", "plfs"], skills=skills)
    def _select(self, query: str, skills: list[str]) -> list[str]:
        if not skills and any(x in query for x in ("unemployment", "plfs")): return ["get_unemployment_snapshot"]
        if skills == ["unemployment_analysis"] or "unemployment_analysis" in skills: return ["get_unemployment_snapshot"]
        if skills == ["epfo_payroll_analysis"] or "epfo_payroll_analysis" in skills: return ["get_epfo_payroll_snapshot"]
        if any(x in query for x in ("epfo", "payroll", "formal")): return ["get_epfo_payroll_snapshot"]
        return ["get_epfo_payroll_snapshot", "get_unemployment_snapshot"]
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskState.WORKING, message="Fetching labour indicators."))
        results = {name: self.registry.invoke(name, context.request.parameters) for name in self._select(context.request.query.lower(), context.request.skills_required)}
        narrative = "# Labour & Employment Report\n\n" + "\n".join(f"- **{v.get('indicator', k)}**: {v.get('latest_value', 'N/A')} ({v.get('data_status', 'error')})" for k, v in results.items())
        artifacts = [A2AArtifact(name="Labour Indicators", type="json", content=results, metadata={"source": "EPFO/MoSPI"}), A2AArtifact(name="Labour Report", type="markdown", content=narrative, metadata={"query": context.request.query})]
        for artifact in artifacts: await event_queue.emit(TaskArtifactUpdateEvent(task_id=context.task_id, artifact=artifact))
        await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskState.COMPLETED, message="Labour analysis completed."))
        return TaskResponse(task_id=context.task_id, status=TaskState.COMPLETED, messages=[A2AMessage(role="agent", parts=[A2AMessagePart(kind="markdown", content=narrative), A2AMessagePart(kind="json", content=results)])], artifacts=artifacts, updated_at=datetime.now(timezone.utc).isoformat())
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskState.CANCELLED, message="Cancelled.")); return True
