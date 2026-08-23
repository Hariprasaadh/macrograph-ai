"""Bootstrap and register all Domain A2A Agent Executors with the Agent Registry."""
from __future__ import annotations

from core.protocols.a2a import agent_registry
from real_sector.agents.executor import RealSectorAgentExecutor
from finance_sector.agents.executor import FinanceSectorAgentExecutor
from capital_market_sector.agents.executor import CapitalMarketsAgentExecutor


def bootstrap_agent_registry() -> None:
    """Registers all active domain A2A AgentCards and Executors."""
    # 1. Real Sector Agent
    real_exec = RealSectorAgentExecutor()
    real_card = RealSectorAgentExecutor.get_agent_card()
    agent_registry.register(real_card, real_exec)

    # 2. Finance Sector Agent (Monetary, Banking, Fiscal, External)
    fin_exec = FinanceSectorAgentExecutor()
    fin_card = FinanceSectorAgentExecutor.get_agent_card()
    agent_registry.register(fin_card, fin_exec)

    # 3. Capital Markets Agent
    cap_exec = CapitalMarketsAgentExecutor()
    cap_card = CapitalMarketsAgentExecutor.get_agent_card()
    agent_registry.register(cap_card, cap_exec)


# Automatically bootstrap upon import
bootstrap_agent_registry()
