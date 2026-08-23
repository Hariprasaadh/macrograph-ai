"""Indian Macroeconomic Knowledge Graph Ontology and Transmission Network."""
from __future__ import annotations

from typing import Dict, List, Optional
from ..data.schema import (
    CanonicalIndicator,
    CausalRelationship,
    CausalRelationType,
    SectorEnum,
)


class MacroeconomicOntology:
    """Defines macroeconomic entities, sector groupings, and 5-tier causal transmission edges."""

    def __init__(self) -> None:
        self.indicators: Dict[str, CanonicalIndicator] = {}
        self.relationships: List[CausalRelationship] = []
        self._build_ontology()

    def _build_ontology(self) -> None:
        # 1. Register Canonical Indicator Entities across 8 Domains
        indicators_list = [
            # Real Economy (Stage 1)
            CanonicalIndicator(
                indicator_id="in.macro.real.gdp_growth",
                name="Quarterly Real GDP Growth Rate",
                sector=SectorEnum.REAL_ECONOMY,
                subsector="National Accounts",
                unit="% YoY",
                frequency="quarterly",
                source_authority="MoSPI"
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
            CanonicalIndicator(
                indicator_id="in.macro.real.gfcf_investment",
                name="Gross Fixed Capital Formation",
                sector=SectorEnum.REAL_ECONOMY,
                subsector="Investment",
                unit="% of GDP",
                frequency="quarterly",
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
                indicator_id="in.macro.prices.cpi_food",
                name="Consumer Food Price Index Inflation",
                sector=SectorEnum.PRICES_INFLATION,
                subsector="Food CPI",
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
                name="Brent Crude Oil Benchmark Price",
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
                source_authority="RBI"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.monetary.bank_credit_growth",
                name="Bank Credit Growth",
                sector=SectorEnum.MONETARY_BANKING,
                subsector="Credit",
                unit="% YoY",
                frequency="fortnightly",
                source_authority="RBI"
            ),

            # Fiscal Sector (Stage 2)
            CanonicalIndicator(
                indicator_id="in.macro.fiscal.debt_to_gdp",
                name="General Government Debt to GDP Ratio",
                sector=SectorEnum.FISCAL,
                subsector="Debt",
                unit="% of GDP",
                frequency="annual",
                source_authority="IMF"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.fiscal.central_capex",
                name="Central Government Capital Expenditure",
                sector=SectorEnum.FISCAL,
                subsector="Capex",
                unit="INR Crore",
                frequency="monthly",
                source_authority="CGA / MoF"
            ),

            # External Sector (Stage 2)
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
                name="USD/INR Exchange Rate",
                sector=SectorEnum.EXTERNAL,
                subsector="Currency",
                unit="INR/USD",
                frequency="daily",
                source_authority="RBI / Markets"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.external.trade_balance",
                name="Merchandise Trade Balance",
                sector=SectorEnum.EXTERNAL,
                subsector="Trade",
                unit="Billion USD",
                frequency="monthly",
                source_authority="Ministry of Commerce"
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
                indicator_id="in.macro.capmarkets.bank_nifty",
                name="NIFTY Bank Index",
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

            # Agriculture & Rural (Stage 3)
            CanonicalIndicator(
                indicator_id="in.macro.agri.monsoon_departure",
                name="Southwest Monsoon LPA Rainfall Departure",
                sector=SectorEnum.AGRICULTURE_RURAL,
                subsector="Climate",
                unit="% departure",
                frequency="seasonal",
                source_authority="IMD"
            ),
            CanonicalIndicator(
                indicator_id="in.macro.agri.foodgrain_production",
                name="Foodgrain Production Volume",
                sector=SectorEnum.AGRICULTURE_RURAL,
                subsector="Output",
                unit="Million Tonnes",
                frequency="annual",
                source_authority="Ministry of Agriculture"
            ),

            # Labour & Employment (Stage 3)
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
        for ind in indicators_list:
            self.indicators[ind.indicator_id] = ind

        # 2. Register Causal Transmission Edges with 5-Tier Classification
        self.relationships = [
            # Stage 1: Energy -> WPI -> CPI -> Repo Rate -> Credit -> GDP
            CausalRelationship(
                source_indicator_id="in.macro.prices.brent_crude",
                target_indicator_id="in.macro.prices.wpi_all",
                relation_type=CausalRelationType.LAGGED_RELATIONSHIP,
                transmission_lag_months=1,
                elasticity_sign="+",
                empirical_p_value=0.001,
                confidence_score=0.95,
                mechanism_description="Crude oil price surge passes directly into Wholesale fuel & manufacturing input costs.",
                documented_assumptions=["Domestic fuel excise taxes remain constant", "Import tariff structures unchanged"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.prices.wpi_all",
                target_indicator_id="in.macro.prices.cpi_headline",
                relation_type=CausalRelationType.GRANGER_PREDICTIVE,
                transmission_lag_months=2,
                elasticity_sign="+",
                empirical_p_value=0.008,
                confidence_score=0.90,
                mechanism_description="Producer price increases in WPI filter downstream into consumer retail CPI baskets.",
                documented_assumptions=["Retail pricing power enables margin pass-through"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.prices.cpi_headline",
                target_indicator_id="in.macro.monetary.repo_rate",
                relation_type=CausalRelationType.STRUCTURAL_CAUSAL_MODEL,
                transmission_lag_months=1,
                elasticity_sign="+",
                empirical_p_value=0.002,
                confidence_score=0.95,
                mechanism_description="RBI Monetary Policy Committee increases Repo Rate when CPI inflation breaches 4% midpoint target.",
                documented_assumptions=["RBI operates under flexible inflation targeting statutory mandate (4% +/- 2%)"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.monetary.repo_rate",
                target_indicator_id="in.macro.monetary.bank_credit_growth",
                relation_type=CausalRelationType.GRANGER_PREDICTIVE,
                transmission_lag_months=3,
                elasticity_sign="-",
                empirical_p_value=0.015,
                confidence_score=0.88,
                mechanism_description="Higher policy repo rate raises lending rates (MCLR/EBLR), dampening corporate and retail loan demand.",
                documented_assumptions=["Transmission through commercial banking system is non-zero"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.monetary.bank_credit_growth",
                target_indicator_id="in.macro.real.iip_growth",
                relation_type=CausalRelationType.STATISTICAL_ASSOCIATION,
                transmission_lag_months=2,
                elasticity_sign="+",
                empirical_p_value=0.025,
                confidence_score=0.82,
                mechanism_description="Commercial credit availability finances industrial inventory, raw materials, and working capital.",
                documented_assumptions=["Credit demand is predominantly productive/manufacturing oriented"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.real.iip_growth",
                target_indicator_id="in.macro.real.gdp_growth",
                relation_type=CausalRelationType.STRUCTURAL_CAUSAL_MODEL,
                transmission_lag_months=1,
                elasticity_sign="+",
                empirical_p_value=0.001,
                confidence_score=0.98,
                mechanism_description="Index of Industrial Production is a direct supply-side input to GVA/GDP manufacturing component.",
                documented_assumptions=["National Accounts accounting identity holds"]
            ),

            # Stage 2: External, Fiscal, & Capital Markets
            CausalRelationship(
                source_indicator_id="in.macro.prices.brent_crude",
                target_indicator_id="in.macro.external.trade_balance",
                relation_type=CausalRelationType.THEORY,
                transmission_lag_months=1,
                elasticity_sign="-",
                empirical_p_value=0.004,
                confidence_score=0.92,
                mechanism_description="India imports ~85% of its crude oil; higher global prices widen the merchandise trade deficit.",
                documented_assumptions=["Domestic oil consumption volume is relatively price-inelastic"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.external.trade_balance",
                target_indicator_id="in.macro.external.usd_inr",
                relation_type=CausalRelationType.STATISTICAL_ASSOCIATION,
                transmission_lag_months=1,
                elasticity_sign="+",
                empirical_p_value=0.010,
                confidence_score=0.86,
                mechanism_description="Widened trade deficit increases US dollar demand by importers, depreciating INR against USD.",
                documented_assumptions=["Capital account inflows do not fully sterilize the trade deficit"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.monetary.repo_rate",
                target_indicator_id="in.macro.capmarkets.bank_nifty",
                relation_type=CausalRelationType.LAGGED_RELATIONSHIP,
                transmission_lag_months=1,
                elasticity_sign="-",
                empirical_p_value=0.020,
                confidence_score=0.85,
                mechanism_description="Monetary tightening compresses banking net interest margins and increases bond treasury yields.",
                documented_assumptions=["Discount rate in equity DCF models rises with sovereign risk-free rate"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.fiscal.central_capex",
                target_indicator_id="in.macro.real.gfcf_investment",
                relation_type=CausalRelationType.THEORY,
                transmission_lag_months=2,
                elasticity_sign="+",
                empirical_p_value=0.005,
                confidence_score=0.90,
                mechanism_description="Public capital expenditure in infrastructure crowds in private gross fixed capital formation.",
                documented_assumptions=["Public infrastructure spending multipliers are positive (> 2.0x)"]
            ),

            # Stage 3: Agriculture & Labour
            CausalRelationship(
                source_indicator_id="in.macro.agri.monsoon_departure",
                target_indicator_id="in.macro.agri.foodgrain_production",
                relation_type=CausalRelationType.THEORY,
                transmission_lag_months=3,
                elasticity_sign="+",
                empirical_p_value=0.003,
                confidence_score=0.92,
                mechanism_description="Adequate monsoon rainfall increases sown area and crop yields for Kharif foodgrains.",
                documented_assumptions=["Irrigation buffer does not fully decouple rainfed agricultural output"]
            ),
            CausalRelationship(
                source_indicator_id="in.macro.agri.foodgrain_production",
                target_indicator_id="in.macro.prices.cpi_food",
                relation_type=CausalRelationType.STATISTICAL_ASSOCIATION,
                transmission_lag_months=2,
                elasticity_sign="-",
                empirical_p_value=0.012,
                confidence_score=0.89,
                mechanism_description="Higher foodgrain output builds buffer stocks, stabilizing open-market cereal and food prices.",
                documented_assumptions=["Supply chain hoarding and distribution bottlenecks are minimal"]
            ),
        ]


# Global ontology singleton
ontology = MacroeconomicOntology()
