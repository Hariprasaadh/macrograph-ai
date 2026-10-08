"""A2A Agent Executor for the Labour Sector."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid

from core.protocols.a2a.models import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentSkill,
    RequestContext,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from core.protocols.a2a.lifecycle import AgentExecutor, EventQueue
from core.sector_reasoning import record_to_dict
from labour_sector import client


class LabourEmploymentAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Labour & Employment Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/labour-sector") -> AgentCard:
        return AgentCard(
            name="Labour & Employment Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for Indian Labour Market: "
                "PLFS Unemployment Rate (UR %), LFPR %, WPR %, and EPFO payroll additions."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=["macroeconomics", "labour_sector", "unemployment", "lfpr", "wpr", "epfo"],
            skills=[
                AgentSkill(
                    id="unemployment_analysis",
                    name="PLFS Unemployment Rate Analysis",
                    description="Evaluates Unemployment Rate UR (%), LFPR %, and WPR %.",
                    tags=["unemployment", "lfpr", "wpr", "plfs"],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting labour sector analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            results = await asyncio.gather(
                client.fetch_unemployment_snapshot(),
                client.fetch_labour_force_participation(),
                client.fetch_worker_population_ratio(),
                return_exceptions=True,
            )

            unemp = results[0] if not isinstance(results[0], Exception) else []
            lfpr = results[1] if not isinstance(results[1], Exception) else []
            wpr = results[2] if not isinstance(results[2], Exception) else []

            unemp_rec = record_to_dict(unemp[0]) if unemp else {}
            lfpr_rec = record_to_dict(lfpr[0]) if lfpr else {}
            wpr_rec = record_to_dict(wpr[0]) if wpr else {}
            ur_val = unemp_rec.get("unemployment_rate_pct", "N/A")
            lfpr_val = lfpr_rec.get("lfpr_total_pct", "N/A")
            wpr_val = wpr_rec.get("wpr_total_pct", "N/A")

            report_md = (
                "# Labour & Employment Sector Intelligence Report\n\n"
                "## Executive Summary\n"
                f"- **PLFS Unemployment Rate (UR)**: {ur_val}%\n"
                f"- **Labour Force Participation Rate (LFPR)**: {lfpr_val}%\n"
                f"- **Worker Population Ratio (WPR)**: {wpr_val}%\n\n"
                "| Indicator | Value | Unit | Period | Source |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                f"| Unemployment Rate | {ur_val}% | % | {unemp_rec.get('period', 'N/A')} | MoSPI PLFS |\n"
                f"| LFPR | {lfpr_val}% | % | {lfpr_rec.get('period', 'N/A')} | MoSPI PLFS |\n"
                f"| WPR | {wpr_val}% | % | {wpr_rec.get('period', 'N/A')} | MoSPI PLFS |\n"
            )

            artifact = A2AArtifact(
                artifact_id=f"art_lab_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Labour Sector Analysis",
                type="markdown",
                content=report_md,
                created_at=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskArtifactUpdateEvent(task_id=task_id, artifact=artifact, timestamp=datetime.now(timezone.utc))
            )

            msg = A2AMessage(
                message_id=f"msg_{uuid.uuid4().hex[:8]}",
                role="agent",
                parts=[A2AMessagePart(type="text", content="Labour sector analysis completed successfully.")],
                timestamp=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskStatusUpdateEvent(task_id=task_id, status=TaskState.COMPLETED, message="Task completed.", timestamp=datetime.now(timezone.utc))
            )

            return TaskResponse(task_id=task_id, status=TaskState.COMPLETED, messages=[msg], artifacts=[artifact])
        except Exception as exc:
            await event_queue.emit(
                TaskStatusUpdateEvent(task_id=task_id, status=TaskState.FAILED, message=str(exc), timestamp=datetime.now(timezone.utc))
            )
            return TaskResponse(task_id=task_id, status=TaskState.FAILED, messages=[], artifacts=[], error=str(exc))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        return True
