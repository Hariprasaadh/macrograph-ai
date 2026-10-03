"""A2A Agent Executor for the External Sector."""
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
from external_sector import client


class ExternalSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for External Sector Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/external-sector") -> AgentCard:
        return AgentCard(
            name="External Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for External Sector: "
                "Forex Reserves, Trade Balance, Balance of Payments, USD/INR, REER/NEER, and FDI/FPI Flows."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=["macroeconomics", "external_sector", "forex", "trade_balance", "bop", "usd_inr"],
            skills=[
                AgentSkill(
                    id="forex_reserves_analysis",
                    name="Forex Reserves Analysis",
                    description="Evaluates total forex reserves, FCA, Gold, SDRs, and RTP.",
                    tags=["forex", "reserves", "rbi"],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting external sector analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            results = await asyncio.gather(
                client.fetch_forex_reserves(lookback_weeks=4),
                client.fetch_trade_balance(lookback_months=6),
                client.fetch_exchange_rate_snapshot(lookback_months=6),
                return_exceptions=True,
            )

            forex = results[0] if not isinstance(results[0], Exception) else []
            trade = results[1] if not isinstance(results[1], Exception) else []
            fx = results[2] if not isinstance(results[2], Exception) else []

            total_forex = forex[0].total_reserves_usd_mn if forex else "N/A"
            usd_inr = fx[0].usd_inr_rate if fx else "N/A"

            report_md = (
                "# External Sector Intelligence Report\n\n"
                "## Executive Summary\n"
                f"- **Total Forex Reserves**: ${total_forex} Million USD\n"
                f"- **USD/INR Rate**: ₹{usd_inr}\n"
                f"- **Trade Balance**: ${trade[0].trade_balance_usd_bn if trade else 'N/A'} Billion USD\n\n"
                "| Indicator | Value | Unit | Period | Source |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                f"| Forex Reserves | ${total_forex}M | USD | {forex[0].period if forex else 'N/A'} | RBI DBIE |\n"
            )

            artifact = A2AArtifact(
                artifact_id=f"art_ext_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="External Sector Analysis",
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
                parts=[A2AMessagePart(type="text", content="External sector analysis completed successfully.")],
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
            return TaskResponse(task_id=task_id, status=TaskState.FAILED, messages=[], artifacts=[])

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        return True
