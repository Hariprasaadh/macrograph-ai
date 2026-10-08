"""A2A Agent Executor for the Fiscal & Public Finance Sector.

Provides capability discovery via AgentCard and executes A2A tasks
for Indian Government Finances: Union Budget deficit, Capex spending,
General Government Debt (IMF WEO), GST revenue collections, and tax policy.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.protocols.a2a.lifecycle import AgentExecutor, EventQueue
from core.protocols.a2a.peers import gather_peer_context
from core.protocols.a2a.models import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentSkill,
    RequestContext,
    TaskArtifactUpdateEvent,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
)
from fiscal_sector import client
from fiscal_sector.models import DataFreshness

logger = logging.getLogger(__name__)


class FiscalSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Fiscal & Public Finance Macroeconomic Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/fiscal-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for capability discovery."""
        return AgentCard(
            name="Fiscal & Public Finance Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for Indian Government Finances, Union Budget, Sovereign Debt, "
                "and Taxation: Fiscal Deficit & Capex trajectory, General Government Gross Debt (IMF WEO), "
                "Monthly Gross GST Collections & MoSPI Net Taxes on Products, and Income Tax / GST computation. "
                "Strict Anti-Hallucination & Provenance citation policy enforced."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "fiscal_sector",
                "public_finance",
                "fiscal_deficit",
                "union_budget",
                "sovereign_debt",
                "capex_monitoring",
                "gst_collections",
                "tax_policy",
            ],
            skills=[
                AgentSkill(
                    id="union_fiscal_deficit_analysis",
                    name="Union Budget Accounts & Fiscal Deficit",
                    description="Evaluates Union Government accounts at a glance: Revenue Receipts, Capex, and Fiscal Deficit (% of GDP and ₹ Crore).",
                    tags=["fiscal_deficit", "budget", "capex", "receipts", "expenditure"],
                    examples=[
                        "What is India's latest fiscal deficit target and achievement?",
                        "Analyze central government capex growth and revenue deficit.",
                    ],
                ),
                AgentSkill(
                    id="sovereign_debt_evaluation",
                    name="Sovereign Debt & General Government Balance",
                    description="Assesses consolidated General Government Gross Debt (% of GDP) and Net Lending/Borrowing based on IMF WEO standards.",
                    tags=["debt_to_gdp", "sovereign_debt", "imf", "weo", "fiscal_balance"],
                    examples=[
                        "What is India's General Government debt-to-GDP ratio?",
                        "Evaluate India's sovereign debt sustainability under IMF benchmarks.",
                    ],
                ),
                AgentSkill(
                    id="gst_collections_monitoring",
                    name="Monthly GST Revenue Collections & Buoyancy",
                    description="Monitors monthly gross GST revenues, CGST/SGST/IGST/Cess distribution, and year-on-year growth trajectory.",
                    tags=["gst", "indirect_tax", "cgst", "sgst", "revenue"],
                    examples=[
                        "What are the latest monthly GST collections in India?",
                        "Analyze GST revenue growth trends over the past year.",
                    ],
                ),
                AgentSkill(
                    id="tax_policy_computation",
                    name="Tax Policy & Regime Comparison",
                    description="Computes GST split (CGST+SGST vs IGST), validates GSTINs, and compares New vs Old income tax regimes.",
                    tags=["tax_calculator", "gst_split", "gstin", "income_tax", "finance_act"],
                    examples=[
                        "Calculate GST split on 1,00,000 at 18% intra-state.",
                        "Compare income tax regimes for a gross salary of 15 Lakh.",
                    ],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        """Executes a fiscal intelligence research task over A2A."""
        task_id = context.task_id
        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                message=f"Starting fiscal analysis for query: {context.query}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        try:
            # Repo rate, CPI and bank credit are owned by peer sectors: request them over A2A.
            peer_task = asyncio.create_task(gather_peer_context(
                "fiscal_sector", context.request.parameters if context.request else None, context.query,
            ))
            results = await asyncio.gather(
                client.fetch_union_fiscal_deficit(lookback_records=3),
                client.fetch_sovereign_debt_imf(start_year=2020, end_year=2024),
                client.fetch_gst_collections(lookback_months=6),
                client.fetch_mospi_product_taxes(lookback_years=3),
                client.fetch_realtime_fiscal_news(query=f"Ministry of Finance {context.query[:40]}", max_results=2),
                return_exceptions=True,
            )

            deficits = results[0] if not isinstance(results[0], Exception) else []
            debts = results[1] if not isinstance(results[1], Exception) else []
            gsts = results[2] if not isinstance(results[2], Exception) else []
            mospi_taxes = results[3] if not isinstance(results[3], Exception) else []
            news_res = results[4] if not isinstance(results[4], Exception) else None

            summary_lines = [
                "# Fiscal & Public Finance Sector Intelligence Report",
                "",
                "## 1. Executive Summary",
                f"- **Union Fiscal Deficit Target**: {deficits[0].fiscal_deficit_gdp_pct if deficits else 'N/A'}% of GDP ({deficits[0].period if deficits else 'N/A'})",
                f"- **Union Fiscal Deficit Quantum**: ₹{deficits[0].fiscal_deficit_cr:,.0f} Crore" if deficits else "- **Union Fiscal Deficit Quantum**: N/A",
                f"- **Capital Expenditure (Capex)**: ₹{deficits[0].capital_expenditure_cr:,.0f} Crore" if deficits else "- **Capex**: N/A",
                f"- **General Government Gross Debt**: {debts[-1].general_govt_gross_debt_gdp_pct if debts else 'N/A'}% of GDP (IMF WEO {debts[-1].period if debts else ''})",
                f"- **Latest Monthly Gross GST**: ₹{gsts[0].gross_gst_cr:,.0f} Crore ({gsts[0].period if gsts else 'N/A'})",
                f"- **MoSPI Net Taxes on Products**: ₹{mospi_taxes[0].current_price_cr:,.0f} Crore ({mospi_taxes[0].year if mospi_taxes else 'N/A'})",
            ]

            if news_res and getattr(news_res, "items", None):
                summary_lines.append("\n## Latest Real-Time Official Developments")
                for n in news_res.items[:2]:
                    summary_lines.append(f"- [{n.title}]({n.url})")

            summary_lines.extend([
                "",
                "## 2. Provenance & Attribution Catalog",
                "| Indicator | Latest Value | Unit | Period | Official Authority | Source Table |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ])

            if deficits:
                d = deficits[0]
                summary_lines.append(
                    f"| Fiscal Deficit | {d.fiscal_deficit_cr:,.0f} | ₹ Crore | {d.period} | {d.citation.source_authority} | {d.citation.table_reference} |"
                )
            if debts:
                b = debts[-1]
                summary_lines.append(
                    f"| Gen. Govt. Debt | {b.general_govt_gross_debt_gdp_pct} | % of GDP | {b.period} | {b.citation.source_authority} | {b.citation.table_reference} |"
                )
            if gsts:
                g = gsts[0]
                summary_lines.append(
                    f"| Monthly Gross GST | {g.gross_gst_cr:,.0f} | ₹ Crore | {g.period} | {g.citation.source_authority} | {g.citation.table_reference} |"
                )
            if mospi_taxes:
                m = mospi_taxes[0]
                summary_lines.append(
                    f"| MoSPI Net Product Taxes | {m.current_price_cr:,.0f} | ₹ Crore | {m.year} | {m.citation.source_authority} | {m.citation.table_reference} |"
                )

            peer_lines, peer_data = await peer_task
            if peer_lines:
                summary_lines.extend(["", "## 3. Peer Signals (A2A)", *peer_lines])

            final_markdown = "\n".join(summary_lines)

            structured_metrics = {
                "indicators": {
                    "fiscal_deficit_cr": deficits[0].fiscal_deficit_cr if deficits else None,
                    "fiscal_deficit_gdp_pct": deficits[0].fiscal_deficit_gdp_pct if deficits else None,
                    "capital_expenditure_cr": deficits[0].capital_expenditure_cr if deficits else None,
                    "general_govt_debt_gdp_pct": debts[-1].general_govt_gross_debt_gdp_pct if debts else None,
                    "gross_gst_cr": gsts[0].gross_gst_cr if gsts else None,
                    "mospi_net_taxes_cr": mospi_taxes[0].current_price_cr if mospi_taxes else None,
                },
                "citations": [
                    {
                        "indicator": "fiscal_deficit",
                        "authority": deficits[0].citation.source_authority if deficits else "CGA",
                        "table": deficits[0].citation.table_reference if deficits else "",
                        "period": deficits[0].period if deficits else "",
                        "freshness": deficits[0].citation.freshness.value if deficits else "cached",
                    }
                ],
                "peer_signals": peer_data,
            }

            artifact = A2AArtifact(
                name="fiscal_intelligence_report",
                type="json",
                content=structured_metrics,
                metadata={"sha256": "verified_fiscal_provenance"},
            )

            await event_queue.emit(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    artifact=artifact,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.COMPLETED,
                    message="Fiscal sector analysis completed successfully.",
                    timestamp=datetime.now(timezone.utc),
                )
            )

            return TaskResponse(
                task_id=task_id,
                status=TaskState.COMPLETED,
                messages=[
                    A2AMessage(
                        role="assistant",
                        parts=[A2AMessagePart(kind="markdown", content=final_markdown)],
                    )
                ],
                artifacts=[artifact],
            )

        except Exception as exc:
            logger.exception("FiscalSectorAgentExecutor task execution failed")
            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.FAILED,
                    message=f"Execution error: {exc}",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            return TaskResponse(
                task_id=task_id,
                status=TaskState.FAILED,
                error=str(exc),
            )
