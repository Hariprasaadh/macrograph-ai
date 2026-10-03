"""A2A Agent Executor for the Real Sector & Industrial Output."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from core.protocols.a2a.lifecycle import AgentExecutor, EventQueue
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
from real_sector import client
from real_sector.parsers import evaluate_industrial_trends


class RealSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Real Sector, Industrial Output, and Core Industries."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/real-sector") -> AgentCard:
        return AgentCard(
            name="Real Sector & Industrial Output Specialist Agent",
            description=(
                "Specialized AI Agent for Indian Real Sector Macroeconomics: "
                "MoSPI Index of Industrial Production (IIP Sectoral & Use-Based), "
                "DPIIT Eight Core Industries (Steel, Cement, Electricity, Coal, Refinery), "
                "RBI DBIE Manufacturing GVA & OBICUS Capacity Utilisation, "
                "and Infrastructure/Capital Goods market context. Strict provenance enforced."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "real_sector",
                "iip_analysis",
                "manufacturing",
                "core_industries",
                "capacity_utilisation",
                "gva_growth",
                "industrial_trends",
            ],
            skills=[
                AgentSkill(
                    id="iip_industrial_analysis",
                    name="IIP Sectoral & Use-Based Industrial Production",
                    description="Evaluates Index of Industrial Production across Mining, Manufacturing, Electricity, Capital Goods, and Consumer Durables.",
                    tags=["iip", "manufacturing", "capital_goods", "industry"],
                    examples=["What is the latest IIP growth rate?", "Analyze capital goods and manufacturing production trends."],
                ),
                AgentSkill(
                    id="core_industries_analysis",
                    name="Eight Core Infrastructure Industries (ICI)",
                    description="Evaluates production growth across Coal, Crude Oil, Gas, Refinery, Fertilizers, Steel, Cement, and Electricity.",
                    tags=["core_industries", "steel", "cement", "infrastructure", "ici"],
                    examples=["Assess growth in Eight Core Industries.", "How are steel and cement output performing?"],
                ),
                AgentSkill(
                    id="manufacturing_capacity_analysis",
                    name="Manufacturing GVA & OBICUS Capacity Utilisation",
                    description="Evaluates Manufacturing GVA growth and RBI OBICUS manufacturing capacity utilisation ratio (%).",
                    tags=["gva", "obicus", "capacity_utilisation", "manufacturing"],
                    examples=["What is India's manufacturing capacity utilisation?", "Assess quarterly manufacturing GVA growth."],
                ),
                AgentSkill(
                    id="joined_real_sector_diagnostic",
                    name="Real Sector Comprehensive Diagnostic",
                    description="Executes a cross-indicator DuckDB join and directional trend evaluation (↑/↓/→) across all real sector pillars.",
                    tags=["joined_diagnostic", "trend_analytics", "composite"],
                    examples=["Provide a comprehensive diagnostic of India's real sector momentum."],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting real sector analysis for: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            results = await asyncio.gather(
                client.fetch_iip_sectoral(lookback_months=6),
                client.fetch_iip_use_based(lookback_months=6),
                client.fetch_core_industries(lookback_months=6),
                client.fetch_manufacturing_gva(lookback_quarters=4),
                client.fetch_obicus_capacity(lookback_quarters=4),
                client.fetch_infrastructure_market_context(),
                return_exceptions=True,
            )

            iip_sec = results[0] if not isinstance(results[0], Exception) and results[0] else []
            iip_use = results[1] if not isinstance(results[1], Exception) and results[1] else []
            ici = results[2] if not isinstance(results[2], Exception) and results[2] else []
            gva = results[3] if not isinstance(results[3], Exception) and results[3] else []
            obicus = results[4] if not isinstance(results[4], Exception) and results[4] else []
            market = results[5] if not isinstance(results[5], Exception) and results[5] else []

            latest_mfg_yoy = iip_sec[-1].manufacturing_yoy_pct if iip_sec else None
            latest_cap_yoy = iip_use[-1].capital_goods_yoy_pct if iip_use else None
            latest_steel_yoy = ici[-1].steel_yoy_pct if ici else None
            latest_cement_yoy = ici[-1].cement_yoy_pct if ici else None
            latest_cu = obicus[-1].capacity_utilisation_pct if obicus else None

            trends = evaluate_industrial_trends(
                latest_mfg_yoy, latest_cap_yoy, latest_steel_yoy, latest_cement_yoy, latest_cu
            )

            # Determine executive diagnostic line
            if (latest_mfg_yoy or 0) <= 1.0 and (latest_cap_yoy or 0) <= 1.0 and (latest_steel_yoy or 0) > 0:
                diagnosis = "Industrial weakness appears concentrated rather than universal."
            elif (latest_mfg_yoy or 0) > 2.0 and (latest_cap_yoy or 0) > 2.0:
                diagnosis = "Industrial output exhibits broad-based expansion across manufacturing and capital investment."
            else:
                diagnosis = "Industrial output exhibits mixed sectoral divergence across basic infrastructure and consumer segments."

            lines = [
                f"# Real Sector & Industrial Output Intelligence Report",
                "",
                f"**Executive Diagnostic**: {diagnosis}",
                "",
                "## Evidence (Real Sector Indicators)",
                f"- **Manufacturing IIP**: {trends.get('Manufacturing IIP', 'N/A')} (Period: {iip_sec[-1].period if iip_sec else 'N/A'})",
                f"- **Capital-goods IIP**: {trends.get('Capital Goods IIP', 'N/A')} (Period: {iip_use[-1].period if iip_use else 'N/A'})",
                f"- **Core-sector Steel**: {trends.get('Core Steel', 'N/A')} (Period: {ici[-1].period if ici else 'N/A'})",
                f"- **Core-sector Cement**: {trends.get('Core Cement', 'N/A')} (Period: {ici[-1].period if ici else 'N/A'})",
                f"- **Manufacturing GVA**: {gva[-1].manufacturing_gva_real_yoy_pct if gva else 'N/A'}% YoY (Period: {gva[-1].period if gva else 'N/A'})",
                f"- **Capacity Utilisation (OBICUS)**: {trends.get('Capacity Utilisation', 'N/A')} (Period: {obicus[-1].period if obicus else 'N/A'})",
                "",
                "## Market Context (Infrastructure & Capital Goods)",
            ]

            if market and market[0].bellwether_companies:
                for b in market[0].bellwether_companies[:5]:
                    lines.append(f"- **{b.company_name} ({b.symbol})**: ₹{b.current_price or 'N/A'} | 1M: {b.change_pct_1m or 0:+.1f}% | 1Y: {b.change_pct_1y or 0:+.1f}% (Sector: {b.sector_category})")

            lines.extend([
                "",
                "## Data Provenance & Attribution",
                "| Indicator | Source Authority | Table Reference | Period | Freshness |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            if iip_sec:
                lines.append(f"| IIP Sectoral | {iip_sec[-1].citation.source_authority} | {iip_sec[-1].citation.table_reference} | {iip_sec[-1].period} | {iip_sec[-1].citation.freshness.value} |")
            if ici:
                lines.append(f"| Eight Core Industries | {ici[-1].citation.source_authority} | {ici[-1].citation.table_reference} | {ici[-1].period} | {ici[-1].citation.freshness.value} |")
            if gva:
                lines.append(f"| Manufacturing GVA | {gva[-1].citation.source_authority} | {gva[-1].citation.table_reference} | {gva[-1].period} | {gva[-1].citation.freshness.value} |")
            if obicus:
                lines.append(f"| OBICUS Capacity | {obicus[-1].citation.source_authority} | {obicus[-1].citation.table_reference} | {obicus[-1].period} | {obicus[-1].citation.freshness.value} |")

            report_md = "\n".join(lines)

            artifact = A2AArtifact(
                artifact_id=f"art_real_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Real Sector & Industrial Report",
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
                parts=[A2AMessagePart(type="text", content=report_md)],
                timestamp=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.COMPLETED,
                    message="Real sector analysis completed.",
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
                    message=f"Real sector task failed: {exc}",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            return TaskResponse(
                task_id=task_id,
                status=TaskState.FAILED,
                messages=[A2AMessage(message_id=f"err_{uuid.uuid4().hex[:8]}", role="agent", parts=[A2AMessagePart(type="text", content=str(exc))])],
                artifacts=[],
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskState.CANCELLED,
                message="Task cancelled.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        return True
