"""Dashboard overview endpoint."""
from __future__ import annotations

import logging
from typing import Any, Dict
import json
from finance_sector.database import get_connection as get_finance_db

from fastapi import APIRouter

router = APIRouter(tags=["Dashboard"])


@router.get("/api/v1/dashboard/overview", tags=["Dashboard"])
def get_dashboard_overview() -> Dict[str, Any]:
    """Returns aggregated real macroeconomic data for the Finance Sector alongside staged indicators."""
    credit_data = None
    asset_data = None
    rates_data = None
    deposits_data = None

    try:
        with get_finance_db() as conn:
            # 1. Bank Credit Growth
            cr_row = conn.execute(
                "SELECT period, gross_credit_cr, non_food_credit_cr, non_food_credit_yoy_pct, "
                "agriculture_cr, industry_msme_cr, industry_large_cr, services_cr, personal_loans_cr, "
                "personal_housing_cr, personal_vehicle_cr, citation FROM bank_credit_growth ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if cr_row:
                credit_data = {
                    "period": cr_row[0],
                    "gross_credit_cr": cr_row[1],
                    "non_food_credit_cr": cr_row[2],
                    "non_food_credit_yoy_pct": cr_row[3],
                    "sectoral": {
                        "agriculture_cr": cr_row[4],
                        "industry_msme_cr": cr_row[5],
                        "industry_large_cr": cr_row[6],
                        "services_cr": cr_row[7],
                        "personal_loans_cr": cr_row[8],
                        "personal_housing_cr": cr_row[9],
                        "personal_vehicle_cr": cr_row[10],
                    },
                    "citation": json.loads(cr_row[11]) if isinstance(cr_row[11], str) else cr_row[11],
                    "is_real_data": True,
                }

            # 2. Asset Quality
            aq_row = conn.execute(
                "SELECT period, bank_group, gross_npa_pct, net_npa_pct, gross_npa_cr, net_npa_cr, "
                "provision_coverage_ratio_pct, crar_pct, cet1_pct, citation FROM asset_quality ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if aq_row:
                asset_data = {
                    "period": aq_row[0],
                    "bank_group": aq_row[1],
                    "gross_npa_pct": aq_row[2],
                    "net_npa_pct": aq_row[3],
                    "gross_npa_cr": aq_row[4],
                    "net_npa_cr": aq_row[5],
                    "provision_coverage_ratio_pct": aq_row[6],
                    "crar_pct": aq_row[7],
                    "cet1_pct": aq_row[8],
                    "citation": json.loads(aq_row[9]) if isinstance(aq_row[9], str) else aq_row[9],
                    "is_real_data": True,
                }

            # 3. Lending Rates
            lr_row = conn.execute(
                "SELECT period, walr_fresh_pct, walr_outstanding_pct, mclr_1yr_median_pct, "
                "wadtdr_fresh_pct, wadtdr_outstanding_pct, citation FROM lending_rates ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if lr_row:
                rates_data = {
                    "period": lr_row[0],
                    "walr_fresh_pct": lr_row[1],
                    "walr_outstanding_pct": lr_row[2],
                    "mclr_1yr_median_pct": lr_row[3],
                    "wadtdr_fresh_pct": lr_row[4],
                    "wadtdr_outstanding_pct": lr_row[5],
                    "citation": json.loads(lr_row[6]) if isinstance(lr_row[6], str) else lr_row[6],
                    "is_real_data": True,
                }

            # 4. Deposits and CD Ratio
            dp_row = conn.execute(
                "SELECT period, aggregate_deposits_cr, deposits_yoy_pct, demand_deposits_cr, "
                "time_deposits_cr, casa_ratio_pct, bank_credit_cr, cd_ratio_pct, citation "
                "FROM deposits_cd_ratio WHERE period != 'unknown' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if dp_row:
                deposits_data = {
                    "period": dp_row[0],
                    "aggregate_deposits_cr": dp_row[1],
                    "deposits_yoy_pct": dp_row[2],
                    "demand_deposits_cr": dp_row[3],
                    "time_deposits_cr": dp_row[4],
                    "casa_ratio_pct": dp_row[5],
                    "bank_credit_cr": dp_row[6],
                    "cd_ratio_pct": dp_row[7],
                    "citation": json.loads(dp_row[8]) if isinstance(dp_row[8], str) else dp_row[8],
                    "is_real_data": True,
                }
    except Exception:
        logging.getLogger(__name__).exception("Finance dashboard overview query failed; serving empty finance panels")

    # Live and benchmarked indicators for other sectors with MoSPI e-Sankhyiki integration
    other_sectors_preview = [
        {
            "sector": "Real Sector (GDP/GVA)",
            "indicator": "Real GDP Growth Rate",
            "value": None,
            "frequency": "Quarterly (FY25/26)",
            "source": "MoSPI e-Sankhyiki MCP (NAS)",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Prices & Inflation",
            "indicator": "Headline CPI Inflation",
            "value": None,
            "frequency": "Monthly",
            "source": "MoSPI e-Sankhyiki MCP (CPI)",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Monetary & Liquidity",
            "indicator": "Policy Repo Rate",
            "value": None,
            "frequency": "Bi-monthly MPC",
            "source": "RBI Monetary Policy Committee",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "Capital Markets",
            "indicator": "NIFTY 50 Index",
            "value": None,
            "frequency": "Daily",
            "source": "NSE India",
            "status": "unavailable",
            "is_mock": False
        },
        {
            "sector": "External Sector",
            "indicator": "Forex Reserves",
            "value": None,
            "frequency": "Weekly",
            "source": "RBI Weekly Statistical Supplement",
            "status": "unavailable",
            "is_mock": False
        },
    ]

    return {
        "status": "success",
        "finance_sector": {
            "credit_growth": credit_data,
            "asset_quality": asset_data,
            "lending_rates": rates_data,
            "deposits_cd_ratio": deposits_data,
        },
        "other_sectors_preview": other_sectors_preview,
        "platform_summary": {
            "active_live_sectors": ["finance_sector"],
            "staged_sectors": ["real_sector", "capital_market_sector"],
            "development_sectors": [
                "prices_sector", "monetary_sector", "fiscal_sector",
                "external_sector", "agriculture_sector", "labour_sector", "services_sector"
            ],
            "total_sectors": 10,
        }
    }
