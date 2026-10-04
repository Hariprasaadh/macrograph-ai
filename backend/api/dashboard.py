"""Aggregated multi-sector dashboard overview endpoint.

Queries canonical DuckDB stores across all active sectors with verified
data provenance, adhering strictly to the anti-hallucination standard.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict
from fastapi import APIRouter

from finance_sector.database import get_connection as get_finance_db

router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger(__name__)


def _query_finance_sector() -> Dict[str, Any]:
    """Retrieve latest verified banking & financial indicators from finance DuckDB."""
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
    except Exception as exc:
        logger.warning("Finance DuckDB query failed: %s", exc)

    return {
        "credit_growth": credit_data,
        "asset_quality": asset_data,
        "lending_rates": rates_data,
        "deposits_cd_ratio": deposits_data,
    }


def _query_other_sectors_preview() -> list[dict[str, Any]]:
    """Retrieve verified indicators from active sector DuckDB stores."""
    previews = []

    # 1. Real Sector (IIP & Manufacturing GVA)
    try:
        from real_sector.database import get_connection as get_real_db
        with get_real_db() as conn:
            gva_row = conn.execute(
                "SELECT period, manufacturing_gva_real_yoy_pct FROM manufacturing_gva ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if gva_row and gva_row[1] is not None:
                previews.append({
                    "sector": "Real Sector (GDP/GVA)",
                    "indicator": "Manufacturing Real GVA Growth",
                    "value": f"{gva_row[1]:.1f}% YoY",
                    "frequency": f"Quarterly ({gva_row[0]})",
                    "source": "RBI DBIE / MoSPI National Accounts",
                    "status": "verified",
                    "is_mock": False,
                })

            iip_row = conn.execute(
                "SELECT period, general_iip_yoy_pct FROM iip_sectoral ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if iip_row and iip_row[1] is not None:
                previews.append({
                    "sector": "Real Sector (Output)",
                    "indicator": "General IIP Growth",
                    "value": f"{iip_row[1]:+.1f}% YoY",
                    "frequency": f"Monthly ({iip_row[0]})",
                    "source": "MoSPI e-Sankhyiki / RBI DBIE (Table r535)",
                    "status": "verified",
                    "is_mock": False,
                })
    except Exception as e:
        logger.debug("Real sector preview query: %s", e)

    # 2. Monetary & Liquidity Sector
    try:
        from monetary_sector.database import get_connection as get_monetary_db
        with get_monetary_db() as conn:
            rate_row = conn.execute(
                "SELECT period, repo_rate_pct FROM policy_rates ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if rate_row and rate_row[1] is not None:
                previews.append({
                    "sector": "Monetary & Liquidity",
                    "indicator": "Policy Repo Rate",
                    "value": f"{rate_row[1]:.2f}%",
                    "frequency": f"Bi-monthly ({rate_row[0]})",
                    "source": "RBI Monetary Policy Committee",
                    "status": "verified",
                    "is_mock": False,
                })
    except Exception as e:
        logger.debug("Monetary sector preview query: %s", e)

    # 3. Capital Markets Sector
    try:
        from capital_market_sector.database import get_connection as get_capital_db
        with get_capital_db() as conn:
            nifty_row = conn.execute(
                "SELECT period, close_price, change_pct FROM nifty_snapshot ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if nifty_row and nifty_row[1] is not None:
                previews.append({
                    "sector": "Capital Markets",
                    "indicator": "NIFTY 50 Index",
                    "value": f"{nifty_row[1]:,.2f} ({nifty_row[2]:+.2f}%)",
                    "frequency": f"Daily ({nifty_row[0]})",
                    "source": "NSE India / Bhavcopy",
                    "status": "verified",
                    "is_mock": False,
                })

            gsec_row = conn.execute(
                "SELECT period, ten_year_gsec_yield_pct FROM gsec_yields ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if gsec_row and gsec_row[1] is not None:
                previews.append({
                    "sector": "Capital Markets (Debt)",
                    "indicator": "10-Year Benchmark G-Sec Yield",
                    "value": f"{gsec_row[1]:.2f}%",
                    "frequency": f"Monthly ({gsec_row[0]})",
                    "source": "RBI DBIE Public Tables API",
                    "status": "verified",
                    "is_mock": False,
                })
    except Exception as e:
        logger.debug("Capital market preview query: %s", e)

    # 4. External Sector
    try:
        from external_sector.database import get_connection as get_ext_db
        with get_ext_db() as conn:
            fx_row = conn.execute(
                "SELECT period, total_reserves_usd_mn FROM forex_reserves ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if fx_row and fx_row[1] is not None:
                previews.append({
                    "sector": "External Sector",
                    "indicator": "Forex Reserves",
                    "value": f"${fx_row[1] / 1000:,.1f} Bn",
                    "frequency": f"Weekly ({fx_row[0]})",
                    "source": "RBI Weekly Statistical Supplement (WSS)",
                    "status": "verified",
                    "is_mock": False,
                })

            fx_rate = conn.execute(
                "SELECT period, usd_inr_rate FROM exchange_rates ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if fx_rate and fx_rate[1] is not None:
                previews.append({
                    "sector": "External Sector",
                    "indicator": "USD/INR Reference Rate",
                    "value": f"₹{fx_rate[1]:.2f}",
                    "frequency": f"Daily ({fx_rate[0]})",
                    "source": "RBI Financial Markets Operations / FBIL",
                    "status": "verified",
                    "is_mock": False,
                })
    except Exception as e:
        logger.debug("External sector preview query: %s", e)

    # 5. Labour & Employment Sector
    try:
        from labour_sector.database import get_connection as get_labour_db
        with get_labour_db() as conn:
            ur_row = conn.execute(
                "SELECT period, unemployment_rate_pct FROM unemployment ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if ur_row and ur_row[1] is not None:
                previews.append({
                    "sector": "Labour & Employment",
                    "indicator": "Unemployment Rate (UR)",
                    "value": f"{ur_row[1]:.1f}%",
                    "frequency": f"Quarterly ({ur_row[0]})",
                    "source": "MoSPI Periodic Labour Force Survey (PLFS)",
                    "status": "verified",
                    "is_mock": False,
                })
    except Exception as e:
        logger.debug("Labour sector preview query: %s", e)

    # Fallback to explicit status indicators for any missing sectors to maintain anti-hallucination compliance
    covered_sectors = {p["sector"] for p in previews}
    if not any("Prices" in s for s in covered_sectors):
        previews.append({
            "sector": "Prices & Inflation",
            "indicator": "Headline CPI Inflation",
            "value": None,
            "frequency": "Monthly",
            "source": "MoSPI e-Sankhyiki MCP (CPI)",
            "status": "unavailable",
            "is_mock": False,
        })
    if not any("Monetary" in s for s in covered_sectors):
        previews.append({
            "sector": "Monetary & Liquidity",
            "indicator": "Policy Repo Rate",
            "value": None,
            "frequency": "Bi-monthly MPC",
            "source": "RBI Monetary Policy Committee",
            "status": "unavailable",
            "is_mock": False,
        })

    return previews


@router.get("/api/v1/dashboard/overview", tags=["Dashboard"])
def get_dashboard_overview() -> Dict[str, Any]:
    """Returns aggregated real macroeconomic telemetry across active sectors."""
    finance_data = _query_finance_sector()
    other_previews = _query_other_sectors_preview()

    return {
        "status": "success",
        "finance_sector": finance_data,
        "other_sectors_preview": other_previews,
        "platform_summary": {
            "active_live_sectors": [
                "finance_sector",
                "real_sector",
                "capital_market_sector",
                "external_sector",
                "labour_sector",
                "monetary_sector",
            ],
            "staged_sectors": [
                "prices_sector",
                "fiscal_sector",
                "agriculture_sector",
                "services_sector",
            ],
            "development_sectors": [],
            "total_sectors": 10,
        },
    }
