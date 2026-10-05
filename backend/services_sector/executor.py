"""A2A Agent Executor for the Services Sector.

Provides capability discovery via AgentCard and executes A2A tasks
for India's services production, structural GVA, PMI sentiment,
and high-frequency transport/telecom volumes.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

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
from services_sector import client
from services_sector.market_client import (
    fetch_realtime_services_news,
    fetch_services_market_indicators,
)


class ServicesSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Services Sector Macroeconomic Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/services-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for capability discovery."""
        return AgentCard(
            name="Services Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for India's services economy: "
                "Index of Service Production (ISP monthly, 19 sub-sectors), "
                "Services GVA from National Accounts (NAS 8.9-8.14), "
                "Services PMI sentiment, and transport/freight/telecom volumes. "
                "Strict Anti-Hallucination & Provenance citation policy enforced."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "services_sector",
                "isp_monitoring",
                "services_gva",
                "pmi_sentiment",
                "transport_volumes",
            ],
            skills=[
                AgentSkill(
                    id="isp_production_analysis",
                    name="Index of Service Production (ISP)",
                    description="Evaluates monthly services production and 19 sub-sector indices (IT, telecom, trade, transport, finance).",
                    tags=["isp", "services_production", "sub_sectors"],
                    examples=[
                        "How is India's IT services sector performing?",
                        "What is the latest ISP General index growth?",
                    ],
                ),
                AgentSkill(
                    id="services_gva_analysis",
                    name="Services GVA (NAS 8.9-8.14)",
                    description="Evaluates structural services GVA across trade, transport, communication, finance, real estate.",
                    tags=["gva", "national_accounts", "nas", "structural"],
                    examples=[
                        "What is the services share of GVA?",
                        "Compare financial vs transport services GVA growth.",
                    ],
                ),
                AgentSkill(
                    id="pmi_sentiment_analysis",
                    name="Services PMI Sentiment",
                    description="Analyzes headline PMI, new orders, input costs, and employment sentiment.",
                    tags=["pmi", "sentiment", "business_activity"],
                    examples=[
                        "What is the latest Services PMI reading?",
                        "Are services new orders expanding?",
                    ],
                ),
                AgentSkill(
                    id="transport_freight_volumes",
                    name="Transport, Freight & Telecom Volumes",
                    description="Analyzes aviation traffic, railway freight, port cargo, and telecom subscriptions.",
                    tags=["aviation", "freight", "telecom", "volumes"],
                    examples=[
                        "How is railway freight loading trending?",
                        "What do telecom subscriptions show about services velocity?",
                    ],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        """Executes a services intelligence research task over A2A."""
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            # Fetch data across pillars independently
            market_res, news_res = await asyncio.gather(
                fetch_services_market_indicators(),
                fetch_realtime_services_news(query=f"India services {context.query}"[:200], max_results=3),
                return_exceptions=True,
            )

            results = await asyncio.gather(
                client.fetch_isp_growth(lookback_months=6),
                client.fetch_services_gva(),
                client.fetch_services_pmi(lookback_months=6),
                client.fetch_transport_and_freight(lookback_months=6),
                return_exceptions=True,
            )

            isp_records = results[0] if not isinstance(results[0], Exception) else []
            gva_records = results[1] if not isinstance(results[1], Exception) else []
            pmi_records = results[2] if not isinstance(results[2], Exception) else []
            freight_records = results[3] if not isinstance(results[3], Exception) else []

            general = next(
                (r for r in reversed(isp_records) if r.sub_sector.value == "GENERAL"),
                (isp_records[-1] if isp_records else None),
            )

            summary_lines = [
                "# Services Sector Intelligence Report",
                "",
                "## 1. Executive Summary",
                f"- **ISP General YoY**: {general.isp_yoy_pct if general else 'N/A'}%",
                f"- **Services PMI**: {pmi_records[-1].headline_pmi if pmi_records else 'N/A'}",
                f"- **Services GVA YoY**: {gva_records[-1].gva_yoy_pct if gva_records else 'N/A'}%",
                f"- **Latest Volume**: {(freight_records[-1].indicator + ': ' + str(freight_records[-1].value)) if freight_records else 'N/A'}",
            ]

            if not isinstance(market_res, Exception) and getattr(market_res, "benchmark_index", None):
                b = market_res.benchmark_index
                summary_lines.append(f"- **Nifty IT Benchmark**: {b.current_price:,.2f} ({b.change_pct:+.2f}%)")

            if not isinstance(news_res, Exception) and getattr(news_res, "news_items", None):
                summary_lines.append("\n## Latest Real-Time Developments")
                for n in news_res.news_items[:2]:
                    summary_lines.append(f"- [{n.title}]({n.url})")

            summary_lines.extend([
                "",
                "## 2. Provenance & Attribution Catalog",
                "| Indicator | Latest Value | Unit | Period | Official Authority | Source Table |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ])

            if general:
                summary_lines.append(
                    f"| ISP General YoY | {general.isp_yoy_pct}% | % YoY | {general.period} | {general.citation.source_authority} | {general.citation.table_reference} |"
                )
            if pmi_records:
                pr = pmi_records[-1]
                summary_lines.append(
                    f"| Services PMI | {pr.headline_pmi} | Index (50=no change) | {pr.period} | {pr.citation.source_authority} | {pr.citation.table_reference} |"
                )
            if gva_records:
                gr = gva_records[-1]
                summary_lines.append(
                    f"| Services GVA YoY | {gr.gva_yoy_pct}% | % YoY | {gr.period} | {gr.citation.source_authority} | {gr.citation.table_reference} |"
                )
            if freight_records:
                fr = freight_records[-1]
                summary_lines.append(
                    f"| {fr.indicator} | {fr.value} | {fr.unit} | {fr.period} | {fr.citation.source_authority} | {fr.citation.table_reference} |"
                )

            report_md = "\n".join(summary_lines)

            artifact = A2AArtifact(
                artifact_id=f"art_svc_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Services Sector Analysis",
                type="markdown",
                content=report_md,
                created_at=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    artifact=artifact,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            msg = A2AMessage(
                message_id=f"msg_{uuid.uuid4().hex[:8]}",
                role="agent",
                parts=[A2AMessagePart(type="text", content="Services sector analysis completed successfully.")],
                timestamp=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.COMPLETED,
                    message="Services sector task completed.",
                    timestamp=datetime.now(timezone.utc),
                )
            )

            return TaskResponse(
                task_id=task_id,
                status=TaskState.COMPLETED,
                messages=[msg],
                artifacts=[artifact],
            )

        except Exception as exc:
            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.FAILED,
                    message=f"Task execution failed: {exc}",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            err_msg = A2AMessage(
                message_id=f"msg_err_{uuid.uuid4().hex[:8]}",
                role="agent",
                parts=[A2AMessagePart(type="text", content=f"Task execution failed: {exc}")],
                timestamp=datetime.now(timezone.utc),
            )
            return TaskResponse(
                task_id=task_id,
                status=TaskState.FAILED,
                messages=[err_msg],
                artifacts=[],
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        """Handles task cancellation."""
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskState.CANCELLED,
                message="Task cancelled by request.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        return True
