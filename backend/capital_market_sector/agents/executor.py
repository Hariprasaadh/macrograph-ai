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
from .tools import SectorToolInput, SectorToolRegistry
from ..clients.market_data_client import CapitalMarketsDataClient


class CapitalMarketsAgentExecutor(AgentExecutor):
    def __init__(self, client: CapitalMarketsDataClient | None = None) -> None:
        self.client = client or CapitalMarketsDataClient()
        self.registry = SectorToolRegistry(self.client)

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/capital-markets") -> AgentCard:
        input_schema = SectorToolInput.model_json_schema()
        return AgentCard(
            name="Capital Markets Macroeconomic Agent",
            description="Specialized Indian Capital Markets Sector agent for equities, volatility, earnings, primary market, and mutual fund flows.",
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "capital_markets",
                "equities",
                "volatility",
                "earnings",
                "primary_market",
                "mf_flows",
            ],
            skills=[
                AgentSkill(
                    id="equity_market_analysis",
                    name="Equity Market Indices Analysis",
                    description="Analyzes NIFTY 50 and SENSEX index movements and momentum.",
                    tags=["equity", "indexes", "nifty", "sensex"],
                    examples=["Summarize the latest NIFTY 50 and SENSEX readings."],
                    input_schema=input_schema,
                    output_schema={},
                ),
                AgentSkill(
                    id="volatility_analysis",
                    name="Market Volatility Analysis",
                    description="Analyzes India VIX levels and volatility regime signals.",
                    tags=["vix", "volatility", "risk"],
                    examples=["Tell me if India VIX is in a high volatility regime."],
                    input_schema=input_schema,
                    output_schema={},
                ),
                AgentSkill(
                    id="earnings_analysis",
                    name="Corporate Earnings & EPS Analysis",
                    description="Reviews corporate EPS and PAT signals for earnings strength.",
                    tags=["earnings", "eps", "pat", "corporate"],
                    examples=["What do earnings trends say about market direction?"],
                    input_schema=input_schema,
                    output_schema={},
                ),
                AgentSkill(
                    id="primary_market_analysis",
                    name="Primary Market Activity Analysis",
                    description="Analyzes IPO and debt issuance activity in the capital markets.",
                    tags=["ipo", "primary_market", "debt"],
                    examples=["Summarize the current IPO market activity."],
                    input_schema=input_schema,
                    output_schema={},
                ),
                AgentSkill(
                    id="mf_flows_analysis",
                    name="Mutual Fund and DII Flows Analysis",
                    description="Evaluates mutual fund equity flows and domestic institutional purchase signals.",
                    tags=["mf", "dii", "flows", "liquidity"],
                    examples=["Is DII buying or selling equities?"],
                    input_schema=input_schema,
                    output_schema={},
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        task_id = context.task_id
        query = context.request.query.lower()
        skills_required = context.request.skills_required or []
        params = context.request.parameters or {}

        await event_queue.emit(TaskStatusUpdateEvent(task_id=task_id, status=TaskStatus.WORKING, message="Running capital markets tools"))

        tools_to_run = self._select_tools(query, skills_required)
        results: Dict[str, Any] = {}

        for tool_name in tools_to_run:
            try:
                res = self.registry.invoke(tool_name, params)
                results[res.agent] = res.model_dump()
            except Exception as err:
                results[tool_name] = {"error": str(err)}

        narrative = self._generate_narrative(results)

        json_artifact = A2AArtifact(name="Capital Markets Tool Outputs", type="json", content=results, metadata={"tool_count": len(tools_to_run)})
        md_artifact = A2AArtifact(name="Capital Markets Summary", type="markdown", content=narrative, metadata={"query": context.request.query})

        await event_queue.emit(TaskArtifactUpdateEvent(task_id=task_id, artifact=json_artifact))
        await event_queue.emit(TaskArtifactUpdateEvent(task_id=task_id, artifact=md_artifact))

        message = A2AMessage(role="agent", parts=[
            A2AMessagePart(kind="text", content=f"Completed capital markets analysis for query: {context.request.query}"),
            A2AMessagePart(kind="markdown", content=narrative),
            A2AMessagePart(kind="json", content=results),
        ])

        await event_queue.emit(TaskStatusUpdateEvent(task_id=task_id, status=TaskStatus.COMPLETED, message="Capital markets analysis completed."))

        response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            messages=[message],
            artifacts=[json_artifact, md_artifact],
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        return response

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskStatus.CANCELLED, message="Cancelled capital markets task."))
        return True

    def _select_tools(self, query: str, skills_required: List[str]) -> List[str]:
        all_tools = [
            "get_equity_snapshot",
            "get_vix_snapshot",
            "get_earnings_snapshot",
            "get_primary_market_snapshot",
            "get_mf_flows_snapshot",
        ]

        if "capital_markets_comprehensive_synthesis" in skills_required or not skills_required:
            if not query or any(kw in query for kw in ["all", "capital", "market", "comprehensive", "overview"]):
                return all_tools

        selected: List[str] = []
        if "equity_market_analysis" in skills_required or any(kw in query for kw in ["nifty", "sensex", "equity", "index"]):
            selected.append("get_equity_snapshot")
        if "volatility_analysis" in skills_required or any(kw in query for kw in ["vix", "volatility", "risk"]):
            selected.append("get_vix_snapshot")
        if "earnings_analysis" in skills_required or any(kw in query for kw in ["earnings", "eps", "pat"]):
            selected.append("get_earnings_snapshot")
        if "primary_market_analysis" in skills_required or any(kw in query for kw in ["ipo", "debt", "primary market"]):
            selected.append("get_primary_market_snapshot")
        if "mf_flows_analysis" in skills_required or any(kw in query for kw in ["mf", "dii", "flows", "liquidity"]):
            selected.append("get_mf_flows_snapshot")

        return selected if selected else all_tools

    def _generate_narrative(self, results: Dict[str, Any]) -> str:
        lines = ["# Capital Markets Sector Summary\n"]
        for agent_name, result in results.items():
            if isinstance(result, dict) and "assessment" in result:
                lines.append(f"## {agent_name.replace('_', ' ').title()}\n")
                lines.append(result["assessment"] + "\n")
                if result.get("alerts"):
                    lines.append("### Alerts\n")
                    for alert in result["alerts"]:
                        lines.append(f"- {alert}")
                lines.append("\n")
        return "\n".join(lines)
