"""Bootstrap: register every sector's Agent Card, executor and A2A handlers.

This is the only place that names sector packages. Routing, delegation and
peer requests afterwards use agent ids and card metadata only.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import logging

from core.data.schema import SectorEnum
from core.protocols.a2a import a2a_server, agent_registry
from core.protocols.a2a.executor_adapter import (
    SECTOR_ANALYSIS,
    ExecutorTaskHandler,
    SectorAnalysisParams,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SectorSpec:
    agent_id: str
    executor_module: str
    executor_class: str
    sector: SectorEnum | None
    keywords: tuple[str, ...]


SECTOR_SPECS: tuple[SectorSpec, ...] = (
    SectorSpec("real_sector", "real_sector.executor", "RealSectorAgentExecutor", SectorEnum.REAL_ECONOMY,
               ("gdp", "gdp growth", "economic growth", "iip", "output", "industry", "industrial production",
                "investment", "gfcf", "manufacturing", "gva", "real economy")),
    SectorSpec("prices_sector", "prices_sector.agents.executor", "PricesSectorAgentExecutor",
               SectorEnum.PRICES_INFLATION,
               ("inflation", "cpi", "wpi", "crude", "oil", "food inflation", "prices", "price index")),
    SectorSpec("monetary_sector", "monetary_sector.executor", "MonetarySectorAgentExecutor",
               SectorEnum.MONETARY_BANKING,
               ("repo", "rate", "interest rate", "rbi", "monetary", "liquidity", "money supply", "mpc", "m3")),
    SectorSpec("finance_sector", "finance_sector.executor", "FinanceSectorAgentExecutor",
               SectorEnum.MONETARY_BANKING,
               ("credit", "banking", "bank", "npa", "deposit", "lending", "mclr", "walr", "loan")),
    SectorSpec("fiscal_sector", "fiscal_sector.executor", "FiscalSectorAgentExecutor", SectorEnum.FISCAL,
               ("fiscal", "deficit", "capex", "debt", "tax", "gst", "budget", "public finance")),
    SectorSpec("external_sector", "external_sector.executor", "ExternalSectorAgentExecutor",
               SectorEnum.EXTERNAL,
               ("forex", "usd", "inr", "currency", "trade", "cad", "export", "import", "rupee",
                "balance of payments", "remittance", "current account")),
    SectorSpec("capital_market_sector", "capital_market_sector.executor", "CapitalMarketsAgentExecutor",
               SectorEnum.CAPITAL_MARKETS,
               ("nifty", "sensex", "vix", "equity", "earnings", "stock market", "fii", "dii", "g-sec")),
    SectorSpec("agriculture_sector", "agriculture_sector.executor", "AgricultureAgentExecutor",
               SectorEnum.AGRICULTURE_RURAL,
               ("agmarket", "agmarknet", "agricultural", "agriculture", "crop", "msp", "foodgrain", "rural",
                "mandi", "rainfall", "monsoon", "onion", "wheat", "rice", "tomato", "potato", "fertilizer",
                "irrigation", "vegetable", "sowing", "kharif", "rabi", "pulses", "gram", "mustard")),
    SectorSpec("labour_sector", "labour_sector.executor", "LabourEmploymentAgentExecutor",
               SectorEnum.LABOUR_EMPLOYMENT,
               ("labour", "employment", "unemployment", "epfo", "wage", "plfs", "jobs", "lfpr")),
    SectorSpec("services_sector", "services_sector.executor", "ServicesSectorAgentExecutor", None,
               ("services sector", "it exports", "ites", "bpo", "pmi", "services gva", "isp")),
)


def _register_sector(spec: SectorSpec) -> bool:
    try:
        cls = getattr(importlib.import_module(spec.executor_module), spec.executor_class)
        card = cls.get_agent_card()
    except (ImportError, AttributeError) as exc:
        logger.warning("Sector '%s' not registered: %s", spec.agent_id, exc)
        return False

    card.agent_id = spec.agent_id
    card.metadata = {
        **card.metadata,
        "sector": spec.sector.value if spec.sector else None,
        "keywords": list(spec.keywords),
    }
    agent_registry.register(card, cls())
    a2a_server.register_handler(
        spec.agent_id, SECTOR_ANALYSIS, ExecutorTaskHandler(agent_registry, spec.agent_id),
        params_model=SectorAnalysisParams, description="Full sector analysis for a natural-language query.",
    )
    try:
        importlib.import_module(f"{spec.agent_id}.a2a_handlers").register()
    except ModuleNotFoundError as exc:
        if exc.name != f"{spec.agent_id}.a2a_handlers":
            raise
    return True


def bootstrap_agent_registry() -> None:
    """Registers all sector Agent Cards, executors and A2A handlers."""
    for spec in SECTOR_SPECS:
        _register_sector(spec)


# Automatically bootstrap upon import
bootstrap_agent_registry()
