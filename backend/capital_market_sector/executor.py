"""A2A Agent Executor for the Capital Markets Sector."""
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
from capital_market_sector import client


class CapitalMarketsAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Capital Markets Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/capital-markets") -> AgentCard:
        return AgentCard(
            name="Capital Markets Macroeconomic Agent",
            description=(
                "Specialized AI Agent for Indian Capital Markets: "
                "NIFTY 50 equity index levels, India VIX volatility, market breadth, and G-Sec yields."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=["macroeconomics", "capital_market_sector", "nifty_50", "india_vix", "gsec_yields"],
            skills=[
                AgentSkill(
                    id="equity_market_analysis",
                    name="NIFTY 50 & Equity Market Analysis",
                    description="Evaluates NIFTY 50 index levels, volatility, and market breadth.",
                    tags=["nifty", "vix", "equity", "markets"],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting capital markets analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            results = await asyncio.gather(
                client.fetch_nifty_snapshot(),
                client.fetch_india_vix(),
                client.fetch_gsec_yield_snapshot(),
                return_exceptions=True,
            )

            nifty = results[0] if not isinstance(results[0], Exception) else []
            vix = results[1] if not isinstance(results[1], Exception) else []
            gsec = results[2] if not isinstance(results[2], Exception) else []

            nifty_close = nifty[0].close_price if nifty else "N/A"
            vix_val = vix[0].vix_close if vix else "N/A"
            gsec_10y = (
                gsec[0].ten_year_gsec_yield_pct
                if gsec and gsec[0].ten_year_gsec_yield_pct is not None
                else "N/A"
            )
            gsec_10y_value = f"{gsec_10y}%" if gsec_10y != "N/A" else "N/A"

            report_md = (
                "# Capital Markets Intelligence Report\n\n"
                "## Executive Summary\n"
                f"- **NIFTY 50 Index Close**: {nifty_close}\n"
                f"- **India VIX**: {vix_val}\n"
                f"- **10-Year RBI SGL Transaction Yield (monthly)**: {gsec_10y_value}\n\n"
                "| Indicator | Value | Unit | Period | Source |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                f"| NIFTY 50 | {nifty_close} | Index Points | {nifty[0].period if nifty else 'N/A'} | NSE India |\n"
                f"| India VIX | {vix_val} | Index Points | {vix[0].period if vix else 'N/A'} | NSE India |\n"
                f"| 10Y RBI SGL Yield | {gsec_10y_value} | % p.a. | {gsec[0].period if gsec else 'N/A'} | RBI DBIE |\n"
            )

            artifact = A2AArtifact(
                artifact_id=f"art_cap_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Capital Markets Analysis",
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
                parts=[A2AMessagePart(type="text", content="Capital markets analysis completed successfully.")],
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
