"""Bootstrap and register all Domain A2A Agent Executors with the Agent Registry."""
from __future__ import annotations

import importlib
import logging
from core.protocols.a2a import agent_registry

logger = logging.getLogger(__name__)


def _register_executor(module_candidates: list[str], class_name: str) -> None:
    for mod_name in module_candidates:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, class_name)
            card = cls.get_agent_card() if hasattr(cls, "get_agent_card") else cls().get_agent_card("http://localhost:8000")
            agent_registry.register(card, cls())
            logger.debug("Successfully registered %s from %s", class_name, mod_name)
            return
        except (ImportError, AttributeError) as e:
            continue
    logger.debug("Could not load %s from any candidate in %s", class_name, module_candidates)


def bootstrap_agent_registry() -> None:
    """Registers all active domain A2A AgentCards and Executors."""
    executors = [
        (["real_sector.agents.executor", "backend.real_sector.agents.executor", "real_sector.executor"], "RealSectorAgentExecutor"),
        (["finance_sector.agents.executor", "backend.finance_sector.agents.executor", "finance_sector.executor"], "FinanceSectorAgentExecutor"),
        (["capital_market_sector.agents.executor", "backend.capital_market_sector.agents.executor", "capital_market_sector.executor"], "CapitalMarketsAgentExecutor"),
        (["prices_sector.agents.executor", "backend.prices_sector.agents.executor", "prices_sector.executor"], "PricesSectorAgentExecutor"),
        (["agriculture_sector.executor", "backend.agriculture_sector.executor", "agriculture_sector.agents.executor", "backend.agriculture_sector.agents.executor"], "AgricultureAgentExecutor"),
        (["labour_sector.agents.executor", "backend.labour_sector.agents.executor", "labour_sector.executor"], "LabourEmploymentAgentExecutor"),
        (["external_sector.agents.executor", "backend.external_sector.agents.executor", "external_sector.executor"], "ExternalSectorAgentExecutor"),
        (["fiscal_sector.agents.executor", "backend.fiscal_sector.agents.executor", "fiscal_sector.executor"], "FiscalSectorAgentExecutor"),
    ]

    for candidates, cls_name in executors:
        _register_executor(candidates, cls_name)


# Automatically bootstrap upon import
bootstrap_agent_registry()
