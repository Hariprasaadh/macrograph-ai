"""Official Source Adapters Registry for Macroeconomic Data Ingestion."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional
from ..data.schema import CanonicalIndicator, CanonicalObservation, SectorEnum


class SourceAdapterRegistry:
    """Registry managing official extraction pipelines for MoSPI, RBI, SEBI, AMFI, IMF, World Bank."""

    def __init__(self) -> None:
        self._indicators: Dict[str, CanonicalIndicator] = {}
        self._adapters: Dict[str, Callable[[], Optional[CanonicalObservation]]] = {}
        self._seed_canonical_catalog()

    def _seed_canonical_catalog(self) -> None:
        """Seed the canonical indicator definitions across the 8 macro domains."""
        catalog = [
            # Real Economy (Stage 1)
            CanonicalIndicator(
                indicator_id="in.macro.real.gdp_growth",
                name="Quarterly Real GDP Growth Rate",
                sector=SectorEnum.REAL_ECONOMY,
                subsector="National Accounts",
                unit="% YoY",
                frequency="quarterly",
                source_authority="MoSPI",
                source_url="https://www.mospi.gov.in"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.real.iip_growth",
                name="Index of Industrial Production Growth",
                sector=SectorEnum.REAL_ECONOMY,
                subsector="Industry",
                unit="% YoY",
                frequency="monthly",
                source_authority="MoSPI"
            ),
            # Prices & Inflation (Stage 1)
            CanonicalIndicator(
                indicator_id="in.macro.prices.cpi_headline",
                name="All India CPI Combined Headline Inflation",
                sector=SectorEnum.PRICES_INFLATION,
                subsector="Headline",
                unit="% YoY",
                frequency="monthly",
                source_authority="MoSPI"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.prices.wpi_all",
                name="Wholesale Price Index All Commodities",
                sector=SectorEnum.PRICES_INFLATION,
                subsector="WPI",
                unit="% YoY",
                frequency="monthly",
                source_authority="Office of Economic Adviser"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.prices.brent_crude",
                name="Brent Crude Oil Price Benchmark",
                sector=SectorEnum.PRICES_INFLATION,
                subsector="Commodities",
                unit="USD/barrel",
                frequency="daily",
                source_authority="EIA / Markets"
            ),
            # Monetary & Banking (Stage 1)
            CanonicalIndicator(
                indicator_id="in.macro.monetary.repo_rate",
                name="RBI Policy Repo Rate",
                sector=SectorEnum.MONETARY_BANKING,
                subsector="Policy Rates",
                unit="% p.a.",
                frequency="policy_cycle",
                source_authority="RBI",
                source_url="https://www.rbi.org.in"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.monetary.bank_credit_growth",
                name="Scheduled Commercial Banks Credit Growth",
                sector=SectorEnum.MONETARY_BANKING,
                subsector="Credit",
                unit="% YoY",
                frequency="fortnightly",
                source_authority="RBI"
            ),
            # Fiscal (Stage 2)
            CanonicalIndicator(
                indicator_id="in.macro.fiscal.debt_to_gdp",
                name="General Government Debt to GDP Ratio",
                sector=SectorEnum.FISCAL,
                subsector="Sovereign Debt",
                unit="% of GDP",
                frequency="annual",
                source_authority="IMF / MoF"
            ),
            # External (Stage 2)
            CanonicalIndicator(
                indicator_id="in.macro.external.forex_reserves",
                name="Foreign Exchange Reserves of India",
                sector=SectorEnum.EXTERNAL,
                subsector="Reserves",
                unit="Billion USD",
                frequency="weekly",
                source_authority="RBI"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.external.usd_inr",
                name="USD/INR Spot Exchange Rate",
                sector=SectorEnum.EXTERNAL,
                subsector="Currency",
                unit="INR/USD",
                frequency="daily",
                source_authority="RBI / Markets"
            ),
            # Capital Markets (Stage 2)
            CanonicalIndicator(
                indicator_id="in.macro.capmarkets.nifty_50",
                name="NIFTY 50 Benchmark Index",
                sector=SectorEnum.CAPITAL_MARKETS,
                subsector="Equities",
                unit="points",
                frequency="daily",
                source_authority="NSE"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.capmarkets.india_vix",
                name="India VIX Volatility Index",
                sector=SectorEnum.CAPITAL_MARKETS,
                subsector="Volatility",
                unit="points",
                frequency="daily",
                source_authority="NSE"
            ),
            # Agriculture (Stage 3)
            CanonicalIndicator(
                indicator_id="in.macro.agri.foodgrain_production",
                name="Total Foodgrains Production Volume",
                sector=SectorEnum.AGRICULTURE_RURAL,
                subsector="Production",
                unit="Million Tonnes",
                frequency="annual",
                source_authority="Ministry of Agriculture"
            ),
            # Labour (Stage 3)
            CanonicalIndicator(
                indicator_id="in.macro.labour.epfo_additions",
                name="EPFO Monthly Net Payroll Additions",
                sector=SectorEnum.LABOUR_EMPLOYMENT,
                subsector="Formal Employment",
                unit="Count (Thousands)",
                frequency="monthly",
                source_authority="EPFO / MoSPI"
            ),
        ]
        for ind in catalog:
            self._indicators[ind.indicator_id] = ind

    def get_indicator(self, indicator_id: str) -> Optional[CanonicalIndicator]:
        return self._indicators.get(indicator_id)

    def list_indicators(self, sector: Optional[SectorEnum] = None) -> List[CanonicalIndicator]:
        if sector:
            return [ind for ind in self._indicators.values() if ind.sector == sector]
        return list(self._indicators.values())

    def register_adapter(self, indicator_id: str, adapter_fn: Callable[[], Optional[CanonicalObservation]]) -> None:
        self._adapters[indicator_id] = adapter_fn

    def get_adapter(self, indicator_id: str) -> Optional[Callable[[], Optional[CanonicalObservation]]]:
        return self._adapters.get(indicator_id)


source_registry = SourceAdapterRegistry()
