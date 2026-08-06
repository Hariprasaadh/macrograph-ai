"""Real Sector A2A Agent Executor.

Bridges incoming A2A Task requests with Real Sector MCP tools and analytics.
Handles task lifecycle management, status updates, and artifact generation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ..protocols.a2a_protocol import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentExecutor,
    AgentSkill,
    EventQueue,
    RequestContext,
    TaskResponse,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from ..services.pipeline import RealSectorPipeline
from .tools import SectorToolInput, SectorToolRegistry


class RealSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Real Sector Macroeconomic Intelligence."""

    def __init__(self, pipeline: Optional[RealSectorPipeline] = None) -> None:
        self.pipeline = pipeline or RealSectorPipeline()
        self.registry = SectorToolRegistry(self.pipeline)

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/real-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for capability discovery."""
        input_schema = SectorToolInput.model_json_schema()
        return AgentCard(
            name="Real Sector Macroeconomic Agent",
            description="Specialized AI Agent for Indian Real Sector analysis including National Income (GDP/GVA), Industrial Output (IIP), Prices & Inflation (CPI/WPI), and Agriculture.",
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "real_sector",
                "gdp_analysis",
                "industrial_production",
                "inflation_analysis",
                "agricultural_monitoring"
            ],
            skills=[
                AgentSkill(
                    id="national_income_analysis",
                    name="National Income & GDP Analysis",
                    description="Analyzes quarterly real GDP, nominal GDP, and Gross Fixed Capital Formation (GFCF).",
                    tags=["gdp", "national_income", "growth"],
                    examples=["What is the latest real GDP growth rate in India?", "Analyze fixed capital formation trends."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="industrial_production_analysis",
                    name="Industrial Production (IIP) Analysis",
                    description="Evaluates Index of Industrial Production (IIP) use-based indicators and manufacturing output.",
                    tags=["iip", "industry", "manufacturing"],
                    examples=["Assess industrial output and manufacturing sector health.", "Is Indian IIP contracting or expanding?"],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="price_inflation_analysis",
                    name="Prices & Inflation Analysis",
                    description="Monitors headline CPI, food CPI, core CPI, Wholesale Price Index (WPI), and House Price Index.",
                    tags=["cpi", "wpi", "inflation", "prices"],
                    examples=["What is the current CPI inflation rate?", "Is food inflation exceeding headline CPI?"],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="agricultural_snapshot",
                    name="Agricultural & Foodgrain Analysis",
                    description="Monitors foodgrain production volume, crop yield, and Minimum Support Prices (MSP).",
                    tags=["agriculture", "foodgrain", "msp"],
                    examples=["Check agricultural production and MSP risk indicators."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="real_sector_comprehensive_synthesis",
                    name="Comprehensive Real Sector Synthesis",
                    description="Integrates all real sector domain indicators to produce a unified macroeconomic status report.",
                    tags=["real_sector", "comprehensive", "macroeconomy"],
                    examples=["Provide a comprehensive economic assessment of India's real sector."],
                    input_schema=input_schema
                ),
            ]
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        query = context.request.query.lower()
        skills_required = context.request.skills_required or []
        params = context.request.parameters or {}

        # 1. Transition state to WORKING
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskStatus.WORKING,
                message="Initializing Real Sector analytical tools..."
            )
        )

        tools_to_run = self._select_tools(query, skills_required)
        results: Dict[str, Any] = {}
        tool_outputs: List[str] = []

        for tool_name in tools_to_run:
            try:
                res = self.registry.invoke(tool_name, params)
                results[res.agent] = res.model_dump()
                tool_outputs.append(f"**{res.agent.title()} Sector**: {res.assessment}")
            except Exception as err:
                results[tool_name] = {"error": str(err)}

        # 2. Generate Economic Reasoning Synthesis
        reasoning_narrative = self._generate_reasoning(results)

        # 3. Create Artifacts (JSON Metrics + Markdown Report)
        json_artifact = A2AArtifact(
            name="Real Sector Indicators Matrix",
            type="json",
            content=results,
            metadata={"source": "RealSectorPipeline", "tool_count": len(tools_to_run)}
        )
        
        md_artifact = A2AArtifact(
            name="Real Sector Macroeconomic Analysis Report",
            type="markdown",
            content=reasoning_narrative,
            metadata={"query": context.request.query}
        )

        await event_queue.emit(TaskArtifactUpdateEvent(task_id=task_id, artifact=json_artifact))
        await event_queue.emit(TaskArtifactUpdateEvent(task_id=task_id, artifact=md_artifact))

        # 4. Construct Final Message
        message = A2AMessage(
            role="agent",
            parts=[
                A2AMessagePart(kind="text", content=f"Real Sector Analysis completed for query: '{context.request.query}'"),
                A2AMessagePart(kind="markdown", content=reasoning_narrative),
                A2AMessagePart(kind="json", content=results)
            ]
        )

        # 5. Transition state to COMPLETED
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                message="Real Sector analysis successfully computed and synthesized."
            )
        )

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            messages=[message],
            artifacts=[json_artifact, md_artifact],
            updated_at=datetime.now(timezone.utc).isoformat()
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskStatus.CANCELLED,
                message="Task cancelled by caller."
            )
        )
        return True

    def _select_tools(self, query: str, skills_required: List[str]) -> List[str]:
        """Selects appropriate tools based on requested skills or text query matching."""
        all_tools = [
            "get_national_income_snapshot",
            "get_industry_snapshot",
            "get_prices_snapshot",
            "get_agriculture_snapshot"
        ]

        if "real_sector_comprehensive_synthesis" in skills_required or not skills_required:
            if not query or any(kw in query for kw in ["all", "real sector", "comprehensive", "overview", "macro"]):
                return all_tools

        selected: List[str] = []
        if "national_income_analysis" in skills_required or any(kw in query for kw in ["gdp", "national income", "capital formation", "growth"]):
            selected.append("get_national_income_snapshot")
        if "industrial_production_analysis" in skills_required or any(kw in query for kw in ["iip", "industry", "industrial", "manufacturing"]):
            selected.append("get_industry_snapshot")
        if "price_inflation_analysis" in skills_required or any(kw in query for kw in ["cpi", "wpi", "price", "inflation", "cost"]):
            selected.append("get_prices_snapshot")
        if "agricultural_snapshot" in skills_required or any(kw in query for kw in ["agriculture", "foodgrain", "crop", "msp", "yield"]):
            selected.append("get_agriculture_snapshot")

        return selected if selected else all_tools

    def _generate_reasoning(self, results: Dict[str, Any]) -> str:
        """Synthesizes structured indicator outputs into explainable economic reasoning markdown."""
        lines = ["# Real Sector Economic Intelligence Report\n"]
        lines.append("## Executive Summary\n")

        alerts_found = []
        for key, res in results.items():
            if isinstance(res, dict) and "assessment" in res:
                lines.append(f"- **{key.replace('_', ' ').title()}**: {res['assessment']}")
                alerts_found.extend(res.get("alerts", []))

        if alerts_found:
            lines.append("\n## Macroeconomic Alerts & Risk Signals\n")
            for alert in alerts_found:
                lines.append(f"> [ALERT] {alert}")


        lines.append("\n## Detailed Sector Indicators\n")
        for key, res in results.items():
            if not isinstance(res, dict):
                continue
            lines.append(f"### {key.replace('_', ' ').title()}")
            indicators = res.get("indicators", {})
            for ind_name, ind_val in indicators.items():
                if isinstance(ind_val, dict):
                    unit = ind_val.get("unit", "")
                    latest = ind_val.get("latest_value")
                    change_pct = ind_val.get("period_change_pct") or ind_val.get("latest_growth_pct") or ind_val.get("year_change_pct")
                    chg_str = f" ({change_pct:+.2f}%)" if change_pct is not None else ""
                    lines.append(f"- **{ind_name.replace('_', ' ').title()}**: {latest} {unit}{chg_str}")
            lines.append("")

        return "\n".join(lines)
