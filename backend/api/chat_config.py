"""Per-sector configuration for direct sector chat (data keys, report sections, models)."""
from __future__ import annotations

from typing import Any
from agriculture_sector.agent import (
    agriculture_agent_node, _SERVICE_KEYWORDS as _AGRICULTURE_SERVICE_KEYWORDS,
)
from prices_sector.agent import prices_agent_node
from external_sector.agent import (
    _SERVICE_KEYWORDS as _EXTERNAL_SERVICE_KEYWORDS,
    external_agent_node,
)
from external_sector.config import external_settings
from labour_sector.agent import (
    _SERVICE_KEYWORDS as _LABOUR_SERVICE_KEYWORDS,
    labour_agent_node,
)
from labour_sector.config import labour_settings
from capital_market_sector.agent import (
    _SERVICE_KEYWORDS as _CAPITAL_SERVICE_KEYWORDS,
    capital_agent_node,
)
from capital_market_sector.config import capital_settings
from monetary_sector.agent import (
    _SERVICE_KEYWORDS as _MONETARY_SERVICE_KEYWORDS,
    monetary_agent_node,
)
from monetary_sector.config import monetary_settings
from real_sector.agent import (
    _SERVICE_KEYWORDS as _REAL_SERVICE_KEYWORDS,
    real_agent_node,
)
from real_sector.config import real_settings
from services_sector.agent import (
    _SERVICE_KEYWORDS as _SERVICES_SERVICE_KEYWORDS,
    services_agent_node,
)
from services_sector.config import services_settings


_DIRECT_SECTOR_CHAT: dict[str, dict[str, Any]] = {
    "agriculture_sector": {
        "node": agriculture_agent_node,
        "service_keywords": _AGRICULTURE_SERVICE_KEYWORDS,
        "name": "Agriculture",
        "data_key": "agriculture_sector_data",
        "analysis_key": "agriculture_sector_analysis",
        "citations_key": "agriculture_sector_citations",
        "errors_key": "agriculture_sector_errors",
        "freshness_key": "agriculture_sector_freshness",
        "sections": [],
    },
    "prices_sector": {
        "node": prices_agent_node,
        "service_keywords": {},
        "name": "Prices & Inflation",
        "data_key": "prices_sector_data",
        "analysis_key": "prices_sector_analysis",
        "citations_key": "prices_sector_citations",
        "errors_key": "prices_sector_errors",
        "freshness_key": "prices_sector_freshness",
        "sections": [],
    },
    "external_sector": {
        "node": external_agent_node,
        "service_keywords": _EXTERNAL_SERVICE_KEYWORDS,
        "api_key": external_settings.SERV_EXT_KEY,
        "model": external_settings.EXTERNAL_LLM_MODEL,
        "name": "External Sector & Trade",
        "data_key": "external_sector_data",
        "analysis_key": "external_sector_analysis",
        "citations_key": "external_sector_citations",
        "errors_key": "external_sector_errors",
        "freshness_key": "external_sector_freshness",
        "sections": [
            ("forex_reserves", "Foreign exchange reserves", [
                ("Total reserves", "total_reserves_usd_mn", " million USD"),
                ("Foreign currency assets", "foreign_currency_assets_usd_mn", " million USD"),
                ("Gold reserves", "gold_reserves_usd_mn", " million USD"),
            ]),
            ("trade_balance", "Merchandise trade", [
                ("Exports", "exports_usd_bn", " billion USD"),
                ("Imports", "imports_usd_bn", " billion USD"),
                ("Trade balance", "trade_balance_usd_bn", " billion USD"),
            ]),
            ("balance_of_payments", "Balance of payments", [
                ("Current account balance", "current_account_balance_usd_bn", " billion USD"),
                ("Current account / GDP", "current_account_to_gdp_pct", "%"),
                ("Capital account balance", "capital_account_balance_usd_bn", " billion USD"),
                ("Net balance of payments", "net_bop_usd_bn", " billion USD"),
            ]),
            ("exchange_rates", "Exchange rates", [
                ("USD/INR reference rate", "usd_inr_rate", ""),
            ]),
            ("external_flows", "Foreign investment flows", [
                ("Net FDI", "net_fdi_usd_mn", " million USD"),
                ("Net FPI", "net_fpi_usd_mn", " million USD"),
            ]),
        ],
    },
    "labour_sector": {
        "node": labour_agent_node,
        "service_keywords": _LABOUR_SERVICE_KEYWORDS,
        "api_key": labour_settings.LABOUR_LLM_KEY,
        "model": labour_settings.LABOUR_LLM_MODEL,
        "name": "Labour & Employment",
        "data_key": "labour_sector_data",
        "analysis_key": "labour_sector_analysis",
        "citations_key": "labour_sector_citations",
        "errors_key": "labour_sector_errors",
        "freshness_key": "labour_sector_freshness",
        "sections": [
            ("unemployment", "Unemployment", [
                ("Unemployment rate (UR)", "unemployment_rate_pct", "%"),
            ]),
            ("lfpr", "Labour force participation", [
                ("Labour force participation rate (LFPR)", "lfpr_total_pct", "%"),
            ]),
            ("wpr", "Worker population", [
                ("Worker population ratio (WPR)", "wpr_total_pct", "%"),
            ]),
            ("labour_conditions", "Employment conditions", [
                ("EPFO net additions", "epfo_net_additions_thousands", " thousand"),
                ("Self-employed share", "self_employed_share_pct", "%"),
                ("Regular wage/salaried share", "regular_wage_share_pct", "%"),
                ("Casual labour share", "casual_labour_share_pct", "%"),
            ]),
        ],
    },
    "capital_market_sector": {
        "node": capital_agent_node,
        "service_keywords": _CAPITAL_SERVICE_KEYWORDS,
        "api_key": capital_settings.CAPITAL_LLM_KEY,
        "model": capital_settings.CAPITAL_LLM_MODEL,
        "name": "Capital Markets",
        "data_key": "capital_market_sector_data",
        "analysis_key": "capital_market_sector_analysis",
        "citations_key": "capital_market_sector_citations",
        "errors_key": "capital_market_sector_errors",
        "freshness_key": "capital_market_sector_freshness",
        "sections": [
            ("nifty_snapshot", "NIFTY 50", [
                ("Close", "close_price", ""),
                ("Change", "change_pct", "%"),
            ]),
            ("india_vix", "India VIX", [
                ("Close", "vix_close", ""),
                ("Regime", "volatility_regime", ""),
            ]),
            ("market_history", "Historical index data", [
                ("Index", "index_name", ""),
                ("Close", "close_price", ""),
                ("Year-over-year return", "yoy_return_pct", "%"),
                ("P/E", "pe_ratio", ""),
                ("P/B", "pb_ratio", ""),
                ("Dividend yield", "dividend_yield_pct", "%"),
            ]),
            ("market_breadth", "Market breadth", [
                ("Advances", "advances_count", ""),
                ("Declines", "declines_count", ""),
                ("Unchanged", "unchanged_count", ""),
                ("Advance/decline ratio", "advance_decline_ratio", ""),
            ]),
            ("gsec_yields", "Government security yields", [
                ("10-year G-Sec yield", "ten_year_gsec_yield_pct", "%"),
                ("5-year G-Sec yield", "five_year_gsec_yield_pct", "%"),
                ("2-year G-Sec yield", "two_year_gsec_yield_pct", "%"),
                ("2s10s spread", "yield_curve_spread_2s10s_bps", " bps"),
            ]),
            ("mutual_fund_flows", "Mutual Fund Flows", [
                ("SIP Inflows", "sip_inflow_cr", " Cr"),
                ("Equity Inflows", "equity_inflows_cr", " Cr"),
                ("Total Industry AUM", "total_mf_aum_lakh_cr", " Lakh Cr"),
            ]),
            ("fpi_flows", "FPI & DII Flows", [
                ("FPI Net Investment", "fpi_net_investment_cr", " Cr"),
                ("DII Net Investment", "dii_net_investment_cr", " Cr"),
            ]),
            ("corporate_earnings", "Corporate Earnings & Valuation", [
                ("TTM EPS", "ttm_eps", ""),
                ("P/E Ratio", "pe_ratio", ""),
                ("PAT Growth YoY", "pat_growth_yoy_pct", "%"),
            ]),
            ("sectoral_performance", "Sectoral Performance", [
                ("Leading Sector", "leading_sector", ""),
                ("Lagging Sector", "lagging_sector", ""),
                ("NIFTY Bank Change", "nifty_bank_change_pct", "%"),
                ("NIFTY IT Change", "nifty_it_change_pct", "%"),
            ]),
            ("primary_market", "Primary Market (IPOs)", [
                ("IPO Count", "ipo_count", ""),
                ("IPO Proceeds", "ipo_proceeds_cr", " Cr"),
                ("Total Equity Raised", "total_equity_raised_cr", " Cr"),
            ]),
            ("investor_participation", "Investor Participation", [
                ("Demat Accounts", "total_demat_accounts_cr", " Cr"),
                ("Monthly Additions", "monthly_demat_additions_lakh", " Lakh"),
                ("Retail Share", "retail_turnover_share_pct", "%"),
            ]),
            ("market_economy_linkages", "Market-Economy Linkages", [
                ("Equity Risk Premium", "equity_risk_premium_bps", " bps"),
                ("Earnings Yield", "nifty_earnings_yield_pct", "%"),
                ("Market Cap to GDP", "market_cap_to_gdp_pct", "%"),
                ("Valuation Regime", "linkage_regime", ""),
            ]),
        ],
    },
    "monetary_sector": {
        "node": monetary_agent_node,
        "service_keywords": _MONETARY_SERVICE_KEYWORDS,
        "api_key": monetary_settings.MONETARY_LLM_KEY,
        "model": monetary_settings.MONETARY_LLM_MODEL,
        "name": "Monetary & Liquidity",
        "data_key": "monetary_sector_data",
        "analysis_key": "monetary_sector_analysis",
        "citations_key": "monetary_sector_citations",
        "errors_key": "monetary_sector_errors",
        "freshness_key": "monetary_sector_freshness",
        "sections": [
            ("policy_rates", "Policy rates", [
                ("Repo rate", "repo_rate_pct", "%"),
                ("Standing Deposit Facility (SDF)", "sdf_rate_pct", "%"),
                ("Marginal Standing Facility (MSF)", "msf_rate_pct", "%"),
                ("Cash Reserve Ratio (CRR)", "crr_pct", "%"),
                ("Statutory Liquidity Ratio (SLR)", "slr_pct", "%"),
            ]),
            ("money_supply", "Money supply", [
                ("M3", "m3_cr", " crore"),
                ("M3 year-over-year growth", "m3_yoy_pct", "%"),
            ]),
            ("system_liquidity", "System liquidity", [
                ("Net LAF absorption / injection", "net_laf_absorption_cr", " crore"),
                ("Liquidity condition", "liquidity_condition", ""),
            ]),
            ("monetary_stance", "Monetary stance", [
                ("Official stance label", "stance_label", ""),
                ("Real policy rate", "real_policy_rate_pct", "%"),
                ("M3 growth", "m3_growth_pct", "%"),
                ("System liquidity status", "system_liquidity_status", ""),
            ]),
        ],
    },
    "real_sector": {
        "node": real_agent_node,
        "service_keywords": _REAL_SERVICE_KEYWORDS,
        "api_key": real_settings.REAL_LLM_KEY,
        "model": real_settings.REAL_LLM_MODEL,
        "name": "Real Sector & Industrial Output",
        "data_key": "real_sector_data",
        "analysis_key": "real_sector_analysis",
        "citations_key": "real_sector_citations",
        "errors_key": "real_sector_errors",
        "freshness_key": "real_sector_freshness",
        "sections": [
            ("iip_sectoral", "IIP Sectoral Growth", [
                ("General IIP YoY", "general_iip_yoy_pct", "%"),
                ("Manufacturing YoY", "manufacturing_yoy_pct", "%"),
                ("Mining YoY", "mining_yoy_pct", "%"),
                ("Electricity YoY", "electricity_yoy_pct", "%"),
            ]),
            ("iip_use_based", "IIP Use-Based Growth", [
                ("Capital Goods YoY", "capital_goods_yoy_pct", "%"),
                ("Intermediate Goods YoY", "intermediate_goods_yoy_pct", "%"),
                ("Consumer Durables YoY", "consumer_durables_yoy_pct", "%"),
                ("Primary Goods YoY", "primary_goods_yoy_pct", "%"),
            ]),
            ("core_industries", "Eight Core Industries (ICI)", [
                ("Overall ICI YoY", "overall_ici_yoy_pct", "%"),
                ("Steel YoY", "steel_yoy_pct", "%"),
                ("Cement YoY", "cement_yoy_pct", "%"),
                ("Coal YoY", "coal_yoy_pct", "%"),
            ]),
            ("manufacturing_gva", "Manufacturing GVA", [
                ("Real GVA YoY", "manufacturing_gva_real_yoy_pct", "%"),
                ("Nominal GVA (₹ Cr)", "manufacturing_gva_cr", " Cr"),
            ]),
        ],
    },
    "services_sector": {
        "node": services_agent_node,
        "service_keywords": _SERVICES_SERVICE_KEYWORDS,
        "api_key": services_settings.SERV_EXT_KEY,
        "model": services_settings.SERVICES_LLM_MODEL,
        "name": "Services Sector",
        "data_key": "services_sector_data",
        "analysis_key": "services_sector_analysis",
        "citations_key": "services_sector_citations",
        "errors_key": "services_sector_errors",
        "freshness_key": "services_sector_freshness",
        "sections": [
            ("isp_general", "ISP General Index", [
                ("Index (Base 2024-25 = 100)", "isp_index", ""),
                ("Year-over-year growth", "isp_yoy_pct", "%"),
                ("Month-on-month growth", "isp_mom_pct", "%"),
            ]),
            ("isp_it_computer", "IT & Computer Services (ISP)", [
                ("Index (Base 2024-25 = 100)", "isp_index", ""),
                ("Year-over-year growth", "isp_yoy_pct", "%"),
                ("Month-on-month growth", "isp_mom_pct", "%"),
            ]),
            ("services_gva_structural", "Services GVA (NAS Structural)", [
                ("NAS statement", "nas_statement", ""),
                ("Segment", "segment", ""),
                ("Real GVA year-over-year growth", "gva_yoy_pct", "%"),
            ]),
            ("services_pmi", "Services PMI Sentiment", [
                ("Headline PMI (50 = no change)", "headline_pmi", ""),
                ("New orders", "new_orders_idx", ""),
                ("Input costs", "input_costs_idx", ""),
                ("Employment", "employment_idx", ""),
            ]),
            ("transport_freight_telecom", "Transport & Volumes", [
                ("Indicator", "indicator", ""),
                ("Observed value", "value", ""),
                ("Year-over-year change", "yoy_pct", "%"),
            ]),
        ],
    },
}
