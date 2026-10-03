"""A2A Agent Executor for the Finance & Banking Sector.

Provides capability discovery via AgentCard and executes A2A tasks
for Scheduled Commercial Banks: credit growth, asset quality, lending rates,
and deposit mobilisation.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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
from finance_sector import client
from finance_sector.models import BankGroup, DataFreshness


class FinanceSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Finance & Banking Sector Macroeconomic Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/finance-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for capability discovery."""
        return AgentCard(
            name="Finance & Banking Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for Indian Scheduled Commercial Banks (SCBs): "
                "Non-food credit growth & sectoral deployment, Asset quality (Gross/Net NPA, CRAR), "
                "Interest rate transmission (WALR, MCLR, WADTDR, spreads), and Deposit mobilisation/CD ratio. "
                "Strict Anti-Hallucination & Provenance citation policy enforced."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "finance_sector",
                "banking",
                "credit_growth",
                "asset_quality",
                "npa_monitoring",
                "lending_rates",
                "cd_ratio",
            ],
            skills=[
                AgentSkill(
                    id="bank_credit_analysis",
                    name="Bank Credit Growth & Sectoral Deployment",
                    description="Evaluates non-food bank credit growth and sectoral deployment across Agriculture, MSME, Services, and Retail.",
                    tags=["credit", "banking", "sectoral_deployment", "loans"],
                    examples=[
                        "What is the latest bank credit growth rate in India?",
                        "Analyze sectoral credit deployment trends.",
                    ],
                ),
                AgentSkill(
                    id="asset_quality_analysis",
                    name="Asset Quality & Capital Adequacy (NPA & CRAR)",
                    description="Evaluates Gross NPA (%), Net NPA (%), and CRAR (%) across Scheduled Commercial Bank groups.",
                    tags=["npa", "gnpa", "crar", "solvency", "asset_quality"],
                    examples=[
                        "What is the current Gross NPA ratio for Indian commercial banks?",
                        "Compare private vs public sector bank asset quality.",
                    ],
                ),
                AgentSkill(
                    id="lending_rates_transmission",
                    name="Lending Rates & Policy Transmission",
                    description="Analyzes WALR fresh and outstanding loans, MCLR, WADTDR, and transmission spread over RBI Policy Repo Rate.",
                    tags=["walr", "mclr", "wadtdr", "interest_rates", "transmission"],
                    examples=[
                        "What is the current WALR on fresh rupee loans?",
                        "Assess monetary transmission spread over the repo rate.",
                    ],
                ),
                AgentSkill(
                    id="deposit_mobilisation_cd_ratio",
                    name="Deposit Mobilisation & CD Ratio",
                    description="Analyzes aggregate bank deposits YoY growth, CASA ratio, and Credit-to-Deposit (CD) ratio.",
                    tags=["deposits", "cd_ratio", "casa", "liquidity"],
                    examples=[
                        "What is the latest Credit-to-Deposit ratio of Indian banks?",
                        "Analyze bank deposit mobilization growth.",
                    ],
                ),
            ],
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        """Executes a financial intelligence research task over A2A."""
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
                client.fetch_banking_market_indicators(),
                client.fetch_realtime_finance_news(query="RBI commercial bank credit growth 2026", max_results=3),
                return_exceptions=True,
            )

            results = await asyncio.gather(
                client.fetch_bank_credit_growth(lookback_months=6),
                client.fetch_asset_quality(BankGroup.ALL_SCB, lookback_quarters=4),
                client.fetch_lending_rates(lookback_months=6),
                client.fetch_deposits_and_cd_ratio(lookback_months=6),
                return_exceptions=True,
            )

            credit_records = results[0] if not isinstance(results[0], Exception) else []
            quality_records = results[1] if not isinstance(results[1], Exception) else []
            rates_records = results[2] if not isinstance(results[2], Exception) else []
            deposits_records = results[3] if not isinstance(results[3], Exception) else []

            summary_lines = [
                "# Finance & Banking Sector Intelligence Report",
                "",
                "## 1. Executive Summary",
                f"- **Non-Food Credit YoY**: {credit_records[-1].non_food_credit_yoy_pct if credit_records else 'N/A'}%",
                f"- **Gross NPA Ratio**: {quality_records[-1].gross_npa_pct if quality_records else 'N/A'}%",
                f"- **CRAR**: {quality_records[-1].crar_pct if quality_records else 'N/A'}%",
                f"- **Fresh Loan WALR**: {rates_records[-1].walr_fresh_pct if rates_records else 'N/A'}%",
                f"- **Credit-Deposit Ratio**: {deposits_records[-1].cd_ratio_pct if deposits_records else 'N/A'}%",
            ]

            if not isinstance(market_res, Exception) and getattr(market_res, "benchmark_index", None):
                b = market_res.benchmark_index
                summary_lines.append(f"- **Nifty Bank Benchmark**: {b.current_price:,.2f} ({b.change_pct:+.2f}%)")

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

            if credit_records:
                cr = credit_records[-1]
                summary_lines.append(
                    f"| Non-Food Credit YoY | {cr.non_food_credit_yoy_pct}% | % YoY | {cr.period} | {cr.citation.source_authority} | {cr.citation.table_reference} |"
                )
            if quality_records:
                qr = quality_records[-1]
                summary_lines.append(
                    f"| Gross NPA Ratio | {qr.gross_npa_pct}% | % | {qr.period} | {qr.citation.source_authority} | {qr.citation.table_reference} |"
                )
            if rates_records:
                rr = rates_records[-1]
                summary_lines.append(
                    f"| WALR (Fresh Loans) | {rr.walr_fresh_pct}% | % p.a. | {rr.period} | {rr.citation.source_authority} | {rr.citation.table_reference} |"
                )
            if deposits_records:
                dr = deposits_records[-1]
                summary_lines.append(
                    f"| CD Ratio | {dr.cd_ratio_pct}% | % | {dr.period} | {dr.citation.source_authority} | {dr.citation.table_reference} |"
                )

            report_md = "\n".join(summary_lines)

            artifact = A2AArtifact(
                artifact_id=f"art_fin_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                name="Finance Sector Analysis",
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
                parts=[A2AMessagePart(type="text", content="Finance sector analysis completed successfully.")],
                timestamp=datetime.now(timezone.utc),
            )

            await event_queue.emit(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskState.COMPLETED,
                    message="Finance sector task completed.",
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
