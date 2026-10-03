"""A2A Agent Executor for the Monetary & Liquidity Sector."""
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
from monetary_sector import client


class MonetarySectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Monetary Policy & Liquidity Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/monetary-sector") -> AgentCard:
        return AgentCard(
            name="Monetary & Liquidity Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for RBI Monetary Policy: "
                "Policy Repo Rate, SDF, MSF, Bank Rate, CRR, SLR, Money Supply (M1, M2, M3), "
                "System Liquidity, and MPC Stance."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=["macroeconomics", "monetary_sector", "rbi", "repo_rate", "money_supply", "liquidity"],
            skills=[
                AgentSkill(
                    id="policy_rates_analysis",
                    name="RBI Policy Rates & Reserve Requirements",
                    description="Evaluates Policy Repo rate, SDF, MSF, CRR, SLR.",
                    tags=["repo", "rates", "rbi", "crr", "slr"],
                ),
                AgentSkill(
                    id="money_supply_analysis",
                    name="Money Supply Aggregates (M1, M3)",
                    description="Analyzes currency with public, demand deposits, M1 and broad money M3 growth.",
                    tags=["m1", "m3", "money_supply"],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting monetary analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            results = await asyncio.gather(
                client.fetch_policy_rates(lookback_months=6),
                client.fetch_money_supply(lookback_months=6),
                client.fetch_system_liquidity(lookback_months=6),
                client.fetch_monetary_stance_snapshot(),
                return_exceptions=True,
            )

            rates = results[0] if not isinstance(results[0], Exception) else []
            money = results[1] if not isinstance(results[1], Exception) else []
            liq = results[2] if not isinstance(results[2], Exception) else []
            stance = results[3] if not isinstance(results[3], Exception) else []

            latest_repo = rates[-1].repo_rate_pct if rates else "N/A"
            latest_m3_yoy = money[-1].m3_yoy_pct if money else "N/A"

            report_md = (
                "# Monetary Sector Intelligence Report\n\n"
                "## Executive Summary\n"
                f"- **Policy Repo Rate**: {latest_repo}%\n"
                f"- **Broad Money (M3) YoY Growth**: {latest_m3_yoy}%\n"
                f"- **MPC Stance**: {stance[-1].stance_label if stance else 'N/A'}\n\n"
                "| Indicator | Latest Value | Unit | Period | Source |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                f"| Policy Repo Rate | {latest_repo}% | % | {rates[-1].period if rates else 'N/A'} | RBI DBIE |\n"
                f"| M3 Money Supply YoY | {latest_m3_yoy}% | % YoY | {money[-1].period if money else 'N/A'} | RBI DBIE |\n"
            )

            artifact = A2AArtifact(
                artifact_id=f"art_mon_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Monetary Sector Analysis",
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
                parts=[A2AMessagePart(type="text", content="Monetary sector analysis completed successfully.")],
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
