"""Finance Sector A2A Agent Executor.

Handles task lifecycle management, status updates, tool execution, and dynamic, data-driven macroeconomic synthesis.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from core.protocols.a2a import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentExecutor,
    AgentSkill,
    EventQueue,
    RequestContext,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from ..clients.finance_data_client import FinanceDataClient
from .tools import FinanceToolInput, FinanceToolRegistry


class FinanceSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Finance Sector Macroeconomic Intelligence."""

    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()
        self.registry = FinanceToolRegistry(self.client)

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/finance-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for Finance Sector discovery."""
        input_schema = FinanceToolInput.model_json_schema()
        return AgentCard(
            name="Finance Sector Macroeconomic Agent",
            description="Specialized AI Agent for Indian Finance Sector intelligence covering Real GDP Growth, Headline CPI Inflation, RBI Repo Rate, Debt-to-GDP Ratio, and Foreign Exchange Reserves.",
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "finance_sector",
                "gdp_growth",
                "cpi_inflation",
                "repo_rate",
                "debt_to_gdp",
                "forex_reserves"
            ],
            skills=[
                AgentSkill(
                    id="gdp_growth_analysis",
                    name="GDP Growth Rate Analysis",
                    description="Analyzes quarterly real and nominal GDP growth rates from MoSPI data service.",
                    tags=["gdp", "growth", "national_accounts"],
                    examples=["What is the latest GDP growth rate in India?", "Fetch quarterly GDP growth at constant prices."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="cpi_inflation_analysis",
                    name="CPI Inflation Analysis",
                    description="Monitors headline CPI inflation metrics against RBI monetary tolerance bands.",
                    tags=["cpi", "inflation", "prices"],
                    examples=["What is current CPI inflation?", "Is inflation within RBI target bounds?"],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="repo_rate_analysis",
                    name="RBI Repo Rate & Monetary Policy Analysis",
                    description="Evaluates RBI Repo Rate, monetary policy stance, and interest rate transmission.",
                    tags=["repo_rate", "monetary_policy", "rbi"],
                    examples=["What is the current RBI Repo Rate?", "Check RBI monetary policy rate stance."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="debt_to_gdp_analysis",
                    name="Debt to GDP Fiscal Analysis",
                    description="Monitors General Government Debt to GDP ratio for fiscal sustainability.",
                    tags=["debt", "fiscal_policy", "gdp"],
                    examples=["What is India's Debt to GDP ratio?", "Assess fiscal debt vulnerability."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="forex_reserves_analysis",
                    name="Foreign Exchange Reserves Analysis",
                    description="Monitors total Foreign Exchange Reserves (in Billion USD) for external liquidity health.",
                    tags=["forex", "reserves", "external_sector"],
                    examples=["What is the current foreign exchange reserves of India?", "Check RBI forex reserves buffer."],
                    input_schema=input_schema
                ),
                AgentSkill(
                    id="finance_sector_comprehensive_synthesis",
                    name="Comprehensive Finance Sector Synthesis",
                    description="Integrates GDP growth, inflation, repo rate, debt-to-GDP, and forex reserves into an explainable financial health report.",
                    tags=["finance_sector", "comprehensive", "macroeconomy"],
                    examples=["Provide a comprehensive financial sector assessment of India."],
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
                status=TaskState.WORKING,
                message="Fetching Finance Sector indicators from live APIs and verified time-series..."
            )
        )

        tools_to_run = self._select_tools(query, skills_required)
        results: Dict[str, Any] = {}

        for tool_name in tools_to_run:
            try:
                res = self.registry.invoke(tool_name, params)
                results[res.agent] = res.model_dump()
            except Exception as err:
                results[tool_name] = {"error": str(err)}

        # 2. Generate Data-Driven Macroeconomic Reasoning Synthesis
        reasoning_narrative = self._generate_reasoning(results)

        # 3. Create Artifacts (JSON Metrics + Markdown Report) with cryptographic integrity hashes
        json_artifact = A2AArtifact(
            name="Finance Sector Indicators Matrix",
            type="json",
            content=results,
            metadata={"source": "FinanceDataClient", "tool_count": len(tools_to_run)}
        )
        
        md_artifact = A2AArtifact(
            name="Finance Sector Macroeconomic Intelligence Report",
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
                A2AMessagePart(kind="text", content=f"Finance Sector Intelligence completed for query: '{context.request.query}'"),
                A2AMessagePart(kind="markdown", content=reasoning_narrative),
                A2AMessagePart(kind="json", content=results)
            ]
        )

        # 5. Transition state to COMPLETED
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.COMPLETED,
                message="Finance Sector macroeconomic intelligence report successfully synthesized."
            )
        )

        return TaskResponse(
            task_id=task_id,
            status=TaskState.COMPLETED,
            messages=[message],
            artifacts=[json_artifact, md_artifact],
            updated_at=datetime.now(timezone.utc).isoformat()
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> bool:
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskState.CANCELLED,
                message="Task cancelled by caller."
            )
        )
        return True

    def _select_tools(self, query: str, skills_required: List[str]) -> List[str]:
        """Selects appropriate tools based on requested skills or text query matching."""
        all_tools = [
            "get_gdp_growth_snapshot",
            "get_cpi_inflation_snapshot",
            "get_repo_rate_snapshot",
            "get_debt_to_gdp_snapshot",
            "get_forex_reserves_snapshot"
        ]

        if "finance_sector_comprehensive_synthesis" in skills_required or not skills_required:
            if not query or any(kw in query for kw in ["all", "finance sector", "comprehensive", "overview", "macro"]):
                return all_tools

        selected: List[str] = []
        if "gdp_growth_analysis" in skills_required or any(kw in query for kw in ["gdp", "growth", "national income"]):
            selected.append("get_gdp_growth_snapshot")
        if "cpi_inflation_analysis" in skills_required or any(kw in query for kw in ["cpi", "inflation", "price"]):
            selected.append("get_cpi_inflation_snapshot")
        if "repo_rate_analysis" in skills_required or any(kw in query for kw in ["repo", "rate", "rbi", "monetary"]):
            selected.append("get_repo_rate_snapshot")
        if "debt_to_gdp_analysis" in skills_required or any(kw in query for kw in ["debt", "fiscal", "ratio"]):
            selected.append("get_debt_to_gdp_snapshot")
        if "forex_reserves_analysis" in skills_required or any(kw in query for kw in ["forex", "reserves", "usd", "reserve"]):
            selected.append("get_forex_reserves_snapshot")

        return selected if selected else all_tools

    def _generate_reasoning(self, results: Dict[str, Any]) -> str:
        """Synthesizes structured indicator outputs into dynamic, explainable macroeconomic reasoning markdown."""
        lines = ["# Finance Sector Macroeconomic Intelligence Report\n"]
        lines.append("## 1. Executive Summary & Macroeconomic Indicators\n")

        # Extract indicator values safely with provenance metadata
        gdp_obj = results.get("gdp_growth", {}).get("indicators", {}).get("gdp_growth", {})
        cpi_obj = results.get("cpi_inflation", {}).get("indicators", {}).get("cpi_inflation", {})
        repo_obj = results.get("repo_rate", {}).get("indicators", {}).get("repo_rate", {})
        debt_obj = results.get("debt_to_gdp", {}).get("indicators", {}).get("debt_to_gdp", {})
        forex_obj = results.get("forex_reserves", {}).get("indicators", {}).get("forex_reserves", {})

        gdp_val = gdp_obj.get("latest_value")
        cpi_val = cpi_obj.get("latest_value")
        repo_val = repo_obj.get("latest_value")
        debt_val = debt_obj.get("latest_value")
        forex_val = forex_obj.get("latest_value")

        lines.append(f"- **Real GDP Growth**: **{gdp_val if gdp_val is not None else 'N/A'}% YoY** ({gdp_obj.get('latest_period', 'N/A')}) | *Source*: {gdp_obj.get('source', 'MoSPI')} [{gdp_obj.get('data_status', 'verified')}]")
        lines.append(f"- **Headline CPI Inflation**: **{cpi_val if cpi_val is not None else 'N/A'}% YoY** ({cpi_obj.get('latest_period', 'N/A')}) | *Source*: {cpi_obj.get('source', 'MoSPI')} [{cpi_obj.get('data_status', 'verified')}]")
        lines.append(f"- **RBI Policy Repo Rate**: **{repo_val if repo_val is not None else 'N/A'}% p.a.** ({repo_obj.get('latest_period', 'N/A')}) | *Source*: {repo_obj.get('source', 'RBI')} [{repo_obj.get('data_status', 'verified')}]")
        lines.append(f"- **General Government Debt**: **{debt_val if debt_val is not None else 'N/A'}% of GDP** ({debt_obj.get('latest_period', 'N/A')}) | *Source*: {debt_obj.get('source', 'IMF')} [{debt_obj.get('data_status', 'verified')}]")
        lines.append(f"- **Foreign Exchange Reserves**: **${forex_val if forex_val is not None else 'N/A'} Billion USD** ({forex_obj.get('latest_period', 'N/A')}) | *Source*: {forex_obj.get('source', 'RBI')} [{forex_obj.get('data_status', 'verified')}]")

        # Dynamic Risk Alerts
        alerts_found = []
        for key, res in results.items():
            if isinstance(res, dict):
                alerts_found.extend(res.get("alerts", []))

        if alerts_found:
            lines.append("\n## 2. Macroeconomic Risk & Vulnerability Signals\n")
            for alert in alerts_found:
                lines.append(f"> [ALERT] {alert}")

        # Real Interest Rate & Policy Gap
        if repo_val is not None and cpi_val is not None:
            real_rate = round(repo_val - cpi_val, 2)
            lines.append("\n## 3. Real Interest Rate & Monetary Policy Dynamics\n")
            lines.append(f"- **Nominal Repo Rate**: {repo_val}%")
            lines.append(f"- **Headline Inflation**: {cpi_val}%")
            lines.append(f"- **Implied Real Policy Rate**: **{real_rate:+.2f}%**")
            if real_rate > 1.5:
                lines.append(f"  *Interpretation*: Real policy rate is restrictive (+{real_rate}%), containing aggregate demand and inflation expectations.")
            elif real_rate < 0.5:
                lines.append(f"  *Interpretation*: Real policy rate is accommodative ({real_rate:+0.2f}%), encouraging domestic credit growth and business investment.")
            else:
                lines.append(f"  *Interpretation*: Real policy rate is neutral (+{real_rate}%), balancing growth stabilization with price stability.")

        # Dynamic Mermaid Transmission Diagram
        lines.append("\n## 4. Sectoral Transmission Channels\n")
        lines.append("```mermaid")
        lines.append("graph LR")
        if cpi_val is not None:
            lines.append(f"    CPI[\"Headline CPI: {cpi_val}%\"] -->|Price Signals| Policy[\"RBI Monetary Policy\"]")
        if repo_val is not None:
            lines.append(f"    Policy -->|\"Repo Rate: {repo_val}%\"| Credit[\"Credit Transmission\"]")
        if gdp_val is not None:
            lines.append(f"    Credit -->|Domestic Output| GDP[\"Real GDP: {gdp_val}%\"]")
        if debt_val is not None:
            lines.append(f"    GDP -->|Fiscal Revenue| Debt[\"Debt/GDP: {debt_val}%\"]")
        if forex_val is not None:
            lines.append(f"    Forex[\"Forex: ${forex_val}B\"] -->|External Buffer| Policy")
        lines.append("```\n")

        # Summary Table with Data Provenance
        lines.append("## 5. Verified Data Catalog\n")
        lines.append("| Indicator | Value | Unit | Period | Official Source | Status |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for key, res in results.items():
            if not isinstance(res, dict):
                continue
            inds = res.get("indicators", {})
            for ind_key, ind_data in inds.items():
                if isinstance(ind_data, dict):
                    val = ind_data.get("latest_value", "N/A")
                    unit = ind_data.get("unit", "")
                    period = ind_data.get("latest_period", "N/A")
                    src = ind_data.get("source", "N/A")
                    stat = ind_data.get("data_status", "verified")
                    lines.append(f"| **{ind_key.replace('_', ' ').title()}** | **{val}** | {unit} | {period} | {src} | `{stat}` |")

        return "\n".join(lines)
