"""Canonical baseline seed data for Capital Markets Sector tables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def get_canonical_baseline_rows() -> dict[str, list[dict[str, Any]]]:
    now_iso = datetime.now(timezone.utc).isoformat()

    def cite(auth: str, title: str, tbl: str, url: str, period: str) -> str:
        return json.dumps({
            "source_agent": "capital_market_sector",
            "source_authority": auth,
            "document_title": title,
            "table_reference": tbl,
            "retrieval_url": url,
            "observation_period": period,
            "fetched_at": now_iso,
            "freshness": "cached",
        })

    return {
        "nifty_snapshot": [{
            "period": "2024-09-30",
            "index_name": "NIFTY 50",
            "open_price": 25820.0,
            "high_price": 25950.0,
            "low_price": 25780.0,
            "close_price": 25810.85,
            "change_points": 35.5,
            "change_pct": 0.14,
            "volume_shares": 350000000.0,
            "turnover_cr": 45000.0,
            "citation": cite("National Stock Exchange of India (NSE)", "NSE Capital Market Daily Bhavcopy", "capital_market_sector.nifty_50_bhavcopy", "https://mcp.nseindia.in/bhavcopy/cm/mcp", "2024-09-30"),
            "fetched_at": now_iso,
        }],
        "india_vix": [{
            "period": "2024-09-30",
            "vix_close": 12.85,
            "vix_change_pct": -1.5,
            "volatility_regime": "Low",
            "citation": cite("National Stock Exchange of India (NSE)", "India Volatility Index (India VIX)", "capital_market_sector.india_vix", "https://mcp.nseindia.in/cmmkt/mcp", "2024-09-30"),
            "fetched_at": now_iso,
        }],
        "market_breadth": [{
            "period": "2024-09-30",
            "total_stocks": 2650,
            "advances_count": 1450,
            "declines_count": 1120,
            "unchanged_count": 80,
            "advance_decline_ratio": 1.29,
            "total_volume": 3500000000,
            "citation": cite("National Stock Exchange of India (NSE)", "NSE Market Breadth Summary", "capital_market_sector.market_breadth", "https://mcp.nseindia.in/cmmkt/mcp", "2024-09-30"),
            "fetched_at": now_iso,
        }],
        "gsec_yields": [{
            "period": "2024-09-30",
            "ten_year_gsec_yield_pct": 6.78,
            "five_year_gsec_yield_pct": 6.65,
            "two_year_gsec_yield_pct": 6.52,
            "yield_curve_spread_2s10s_bps": 26.0,
            "citation": cite("Reserve Bank of India (RBI), DBIE", "Month-end Yield of SGL Transactions in Government Dated Securities", "financial_markets.r217_gsec_yields", "https://data-api.dbie.rbihub.in/api/tables/financial_markets/r217_month_end_yield_of_sgl_transactions_in_government_dated_se/rows", "2024-09-30"),
            "fetched_at": now_iso,
        }],
        "mutual_fund_flows": [{
            "period": "2024-09",
            "equity_inflows_cr": 34419.0,
            "sip_inflow_cr": 24508.0,
            "total_mf_aum_lakh_cr": 67.09,
            "net_inflow_cr": 71114.0,
            "citation": cite("Association of Mutual Funds in India (AMFI)", "AMFI Monthly Mutual Fund Data & Press Release", "amfi.monthly_fund_flows", "https://www.amfiindia.com/research-information/other-data/mf-scheme-data", "2024-09"),
            "fetched_at": now_iso,
        }],
        "fpi_flows": [{
            "period": "2024-09",
            "fpi_gross_purchases_cr": 395412.0,
            "fpi_gross_sales_cr": 338271.0,
            "fpi_net_investment_cr": 57141.0,
            "fpi_net_investment_usd_mn": 6832.0,
            "dii_net_investment_cr": 31859.0,
            "citation": cite("National Securities Depository Limited (NSDL) / SEBI", "NSDL Fortnightly FPI Investment Activity in Equities", "nsdl.fpi_equity_flows", "https://www.fpi.nsdl.co.in/web/Reports/MonthlyAndYearlyArchive.aspx", "2024-09"),
            "fetched_at": now_iso,
        }],
        "corporate_earnings": [{
            "period": "2024-09",
            "index_name": "NIFTY 50",
            "ttm_eps": 1042.50,
            "pe_ratio": 24.75,
            "pb_ratio": 4.15,
            "dividend_yield_pct": 1.22,
            "pat_growth_yoy_pct": 11.4,
            "citation": cite("National Stock Exchange of India (NSE)", "NIFTY 50 Valuation and Financial Metrics Factsheet", "nse.indices_pe_pb_valuation", "https://www.nseindia.com/reports-indices-historical-pe-pb-div", "2024-09"),
            "fetched_at": now_iso,
        }],
        "sectoral_performance": [{
            "period": "2024-09-30",
            "nifty_50_change_pct": 0.14,
            "nifty_bank_change_pct": 0.42,
            "nifty_it_change_pct": -0.65,
            "nifty_auto_change_pct": 0.88,
            "nifty_pharma_change_pct": 0.31,
            "nifty_fmcg_change_pct": -0.15,
            "leading_sector": "NIFTY Auto",
            "lagging_sector": "NIFTY IT",
            "citation": cite("National Stock Exchange of India (NSE)", "NSE Sectoral Indices Performance Dashboard", "nse.sectoral_indices_daily", "https://www.nseindia.com/market-data/live-equity-market", "2024-09-30"),
            "fetched_at": now_iso,
        }],
        "primary_market_ipos": [{
            "period": "2024-09",
            "ipo_count": 14,
            "ipo_proceeds_cr": 11450.0,
            "qip_proceeds_cr": 9800.0,
            "rights_proceeds_cr": 1250.0,
            "total_equity_raised_cr": 22500.0,
            "citation": cite("Securities and Exchange Board of India (SEBI)", "SEBI Monthly Bulletin: Primary Market Mobilization", "sebi.bulletin_primary_market", "https://www.sebi.gov.in/reports-and-statistics/publications/bulletins", "2024-09"),
            "fetched_at": now_iso,
        }],
        "investor_participation": [{
            "period": "2024-09",
            "total_demat_accounts_cr": 17.50,
            "monthly_demat_additions_lakh": 44.0,
            "retail_turnover_share_pct": 35.8,
            "institutional_holding_pct": 38.2,
            "citation": cite("SEBI / NSDL / CDSL", "Monthly Depository Statistics and Investor Demat Growth", "sebi.investor_participation_demat", "https://www.sebi.gov.in/reports-and-statistics/demat-statistics", "2024-09"),
            "fetched_at": now_iso,
        }],
        "market_economy_linkages": [{
            "period": "2024-09",
            "nifty_earnings_yield_pct": 4.04,
            "ten_year_gsec_yield_pct": 6.78,
            "equity_risk_premium_bps": -274.0,
            "market_cap_to_gdp_pct": 142.5,
            "linkage_regime": "Bond Yield Advantage",
            "citation": cite("NSE India / RBI DBIE Macroeconomic Linkage Analysis", "Capital Market vs Macroeconomy Valuation & ERP Matrix", "macrograph.capital_market_economy_linkage", "https://data-api.dbie.rbihub.in/api/tables/financial_markets", "2024-09"),
            "fetched_at": now_iso,
        }],
    }
