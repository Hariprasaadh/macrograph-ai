"""Bootstrap and register all Domain A2A Agent Executors with the Agent Registry."""
from __future__ import annotations

import logging
from core.protocols.a2a import agent_registry

logger = logging.getLogger(__name__)


def bootstrap_agent_registry() -> None:
    """Registers all active domain A2A AgentCards and Executors."""
    # 1. Real Sector Agent
    try:
        from real_sector.agents.executor import RealSectorAgentExecutor
        agent_registry.register(RealSectorAgentExecutor.get_agent_card(), RealSectorAgentExecutor())
    except ImportError as e:
        logger.debug("Real sector agent executor not loaded: %s", e)

    # 2. Finance Sector Agent
    try:
        from finance_sector.agents.executor import FinanceSectorAgentExecutor
        agent_registry.register(FinanceSectorAgentExecutor.get_agent_card(), FinanceSectorAgentExecutor())
    except ImportError as e:
        logger.debug("Finance sector agent executor not loaded: %s", e)

    # 3. Capital Markets Agent
    try:
        from capital_market_sector.agents.executor import CapitalMarketsAgentExecutor
        agent_registry.register(CapitalMarketsAgentExecutor.get_agent_card(), CapitalMarketsAgentExecutor())
    except ImportError as e:
        logger.debug("Capital markets agent executor not loaded: %s", e)

    # 4. Prices & Inflation Sector Agent (MoSPI e-Sankhyiki FastMCP)
    try:
        from prices_sector.agents.executor import PricesSectorAgentExecutor
        agent_registry.register(PricesSectorAgentExecutor.get_agent_card(), PricesSectorAgentExecutor())
    except ImportError as e:
        logger.debug("Prices sector agent executor not loaded: %s", e)

    # Other sector agents (loaded when implemented)
    optional_executors = [
        ("labour_sector.agents.executor", "LabourEmploymentAgentExecutor"),
        ("agriculture_sector.agents.executor", "AgricultureRuralAgentExecutor"),
        ("external_sector.agents.executor", "ExternalSectorAgentExecutor"),
    ]
    for mod_name, cls_name in optional_executors:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            agent_registry.register(cls.get_agent_card(), cls())
        except (ImportError, AttributeError) as e:
            logger.debug("%s not loaded: %s", cls_name, e)


# Automatically bootstrap upon import
bootstrap_agent_registry()

