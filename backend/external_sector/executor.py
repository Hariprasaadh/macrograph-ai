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
                "Forex Reserves, Trade Balance, Balance of Payments, USD/INR, REER/NEER, "
                "Remittances, and External Debt Vulnerability."
            ),
            url=base_url,
            version="1.1.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics", "external_sector", "forex", "trade_balance",
                "bop", "usd_inr", "remittances", "external_debt"
            ],
            skills=[
                AgentSkill(
                    id="forex_reserves_analysis",
                    name="Forex Reserves & Liquidity Analysis",
                    description="Evaluates total forex reserves, FCA, Gold, SDRs, RTP, and import cover.",
                    tags=["forex", "reserves", "rbi", "import_cover"],
                ),
                AgentSkill(
                    id="international_trade_analysis",
                    name="Merchandise & Services Trade Analysis",
                    description="Evaluates exports, imports, oil vs non-oil composition, and trade deficit.",
                    tags=["trade", "exports", "imports", "deficit"],
                ),
                AgentSkill(
                    id="balance_of_payments_analysis",
                    name="Balance of Payments (BoP) & CAD",
                    description="Evaluates Current Account Deficit (% GDP) and BoP financing sustainability.",
                    tags=["bop", "cad", "current_account"],
                ),
                AgentSkill(
                    id="exchange_rate_competitiveness",
                    name="Exchange Rate & REER/NEER Competitiveness",
                    description="Analyzes USD/INR trends, volatility, and 40-currency REER trade-weighted indices.",
                    tags=["usd_inr", "reer", "neer", "currency"],
                ),
                AgentSkill(
                    id="remittances_and_invisibles",
                    name="Remittances & Cross-Border Invisibles",
                    description="Tracks private transfer inflows, worker remittances, and services surplus.",
                    tags=["remittances", "transfers", "invisibles", "services"],
                ),
                AgentSkill(
                    id="external_debt_vulnerability",
                    name="External Debt Stock & Solvency",
                    description="Assesses external debt composition, short-term debt, and reserve adequacy.",
                    tags=["external_debt", "sovereign", "debt_ratio", "vulnerability"],
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
                client.fetch_exchange_rates(lookback_days=180),
                client.fetch_remittances_and_invisibles(lookback_years=3),
                client.fetch_external_debt(lookback_quarters=4),
                client.fetch_live_market_rates(),
                return_exceptions=True,
            )

            forex = results[0] if not isinstance(results[0], Exception) else []
            trade = results[1] if not isinstance(results[1], Exception) else []
            fx = results[2] if not isinstance(results[2], Exception) else []
            remit = results[3] if not isinstance(results[3], Exception) else []
            debt = results[4] if not isinstance(results[4], Exception) else []
            mkt = results[5] if not isinstance(results[5], Exception) else None

            latest_forex = forex[0] if forex else None
            latest_trade = trade[0] if trade else None
            latest_fx = fx[0] if fx else None
            latest_remit = remit[0] if remit else None
            latest_debt = debt[0] if debt else None

            import_cover_str = (
                f" ({latest_forex.import_cover_months} months import cover)"
                if latest_forex and latest_forex.import_cover_months is not None
                else ""
            )
            debt_ratio_str = (
                f" (Short-term to Reserves: {latest_debt.short_term_to_reserves_pct}%)"
                if latest_debt and latest_debt.short_term_to_reserves_pct is not None
                else ""
            )
            live_spot_rate = mkt.usd_inr if mkt and mkt.usd_inr else None
            fx_rate_val = live_spot_rate if live_spot_rate is not None else (latest_fx.usd_inr_rate if latest_fx else "N/A")
            fx_period = mkt.timestamp[:10] if (live_spot_rate and mkt) else (latest_fx.period if latest_fx else "N/A")
            fx_source = "Yahoo Finance (Live)" if live_spot_rate is not None else "RBI DBIE (Reference)"

            report_md = (
                "# External Sector Intelligence Report\n\n"
                "## Executive Summary\n"
                f"- **Total Forex Reserves**: ${latest_forex.total_reserves_usd_mn if latest_forex else 'N/A'} Million USD{import_cover_str}\n"
                f"- **Spot USD/INR ({fx_source})**: ₹{fx_rate_val}\n"
                f"- **Brent Crude Oil**: ${mkt.brent_crude_usd if mkt and mkt.brent_crude_usd else 'N/A'}/barrel\n"
                f"- **Trade Balance**: ${latest_trade.trade_balance_usd_bn if latest_trade else 'N/A'} Billion USD\n"
                f"- **Annual Private Remittances**: ${latest_remit.private_transfers_net_usd_mn if latest_remit else 'N/A'} Million USD\n"
                f"- **External Debt Stock**: ${latest_debt.total_debt_usd_bn if latest_debt else 'N/A'} Billion USD{debt_ratio_str}\n\n"
                "## Empirical Data Provenance\n"
                "| Indicator | Latest Value | Unit | Period | Source Authority |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                f"| Total Forex Reserves | {latest_forex.total_reserves_usd_mn if latest_forex else 'N/A'} | USD Mn | {latest_forex.period if latest_forex else 'N/A'} | RBI DBIE |\n"
                f"| Merchandise Trade Balance | {latest_trade.trade_balance_usd_bn if latest_trade else 'N/A'} | USD Bn | {latest_trade.period if latest_trade else 'N/A'} | RBI DBIE / MoSPI |\n"
                f"| USD/INR Exchange Rate | {fx_rate_val} | INR/USD | {fx_period} | {fx_source} |\n"
                f"| Private Remittances (Net) | {latest_remit.private_transfers_net_usd_mn if latest_remit else 'N/A'} | USD Mn | {latest_remit.period if latest_remit else 'N/A'} | MoSPI eSankhyiki |\n"
                f"| External Debt Stock | {latest_debt.total_debt_usd_bn if latest_debt else 'N/A'} | USD Bn | {latest_debt.period if latest_debt else 'N/A'} | MoSPI eSankhyiki |\n"
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
                parts=[A2AMessagePart(type="text", content="External sector comprehensive analysis completed successfully.")],
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
