"""Helper functions for querying sector DuckDB stores and analytical synthesis."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb

logger = logging.getLogger(__name__)


def parse_citation(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {"note": val}
    return {}


def query_finance_telemetry() -> Dict[str, Any]:
    credit_data = None
    asset_data = None
    rates_data = None
    deposits_data = None
    timeseries: Dict[str, List[Dict[str, Any]]] = {
        "credit": [],
        "asset_quality": [],
        "lending_rates": [],
        "deposits": [],
    }

    try:
        from finance_sector.database import get_connection as get_finance_db
        with get_finance_db(read_only=True) as conn:
            cr_rows = conn.execute(
                "SELECT period, gross_credit_cr, non_food_credit_cr, non_food_credit_yoy_pct, "
                "agriculture_cr, industry_msme_cr, industry_large_cr, services_cr, personal_loans_cr, "
                "personal_housing_cr, personal_vehicle_cr, citation FROM bank_credit_growth ORDER BY id ASC"
            ).fetchall()
            for r in cr_rows:
                timeseries["credit"].append({"period": r[0], "gross_credit_cr": r[1], "non_food_credit_cr": r[2], "non_food_credit_yoy_pct": r[3]})
            if cr_rows:
                l = cr_rows[-1]
                credit_data = {
                    "period": l[0], "gross_credit_cr": l[1], "non_food_credit_cr": l[2], "non_food_credit_yoy_pct": l[3],
                    "sectoral": {
                        "agriculture_cr": l[4], "industry_msme_cr": l[5], "industry_large_cr": l[6],
                        "services_cr": l[7], "personal_loans_cr": l[8], "personal_housing_cr": l[9], "personal_vehicle_cr": l[10],
                    },
                    "citation": parse_citation(l[11]), "is_real_data": True,
                }

            aq_rows = conn.execute(
                "SELECT period, bank_group, gross_npa_pct, net_npa_pct, gross_npa_cr, net_npa_cr, "
                "provision_coverage_ratio_pct, crar_pct, cet1_pct, citation FROM asset_quality ORDER BY id ASC"
            ).fetchall()
            for r in aq_rows:
                timeseries["asset_quality"].append({"period": r[0], "gross_npa_pct": r[2], "net_npa_pct": r[3], "crar_pct": r[7], "pcr_pct": r[6]})
            if aq_rows:
                l = aq_rows[-1]
                asset_data = {
                    "period": l[0], "bank_group": l[1], "gross_npa_pct": l[2], "net_npa_pct": l[3],
                    "gross_npa_cr": l[4], "net_npa_cr": l[5], "provision_coverage_ratio_pct": l[6],
                    "crar_pct": l[7], "cet1_pct": l[8], "citation": parse_citation(l[9]), "is_real_data": True,
                }

            lr_rows = conn.execute(
                "SELECT period, walr_fresh_pct, walr_outstanding_pct, mclr_1yr_median_pct, "
                "wadtdr_fresh_pct, wadtdr_outstanding_pct, citation FROM lending_rates ORDER BY id ASC"
            ).fetchall()
            for r in lr_rows:
                timeseries["lending_rates"].append({"period": r[0], "walr_fresh_pct": r[1], "walr_outstanding_pct": r[2], "mclr_1yr_median_pct": r[3], "wadtdr_fresh_pct": r[4]})
            if lr_rows:
                l = lr_rows[-1]
                rates_data = {
                    "period": l[0], "walr_fresh_pct": l[1], "walr_outstanding_pct": l[2], "mclr_1yr_median_pct": l[3],
                    "wadtdr_fresh_pct": l[4], "wadtdr_outstanding_pct": l[5], "citation": parse_citation(l[6]), "is_real_data": True,
                }

            dp_rows = conn.execute(
                "SELECT period, aggregate_deposits_cr, deposits_yoy_pct, demand_deposits_cr, "
                "time_deposits_cr, casa_ratio_pct, bank_credit_cr, cd_ratio_pct, citation "
                "FROM deposits_cd_ratio WHERE period != 'unknown' ORDER BY id ASC"
            ).fetchall()
            for r in dp_rows:
                timeseries["deposits"].append({"period": r[0], "aggregate_deposits_cr": r[1], "deposits_yoy_pct": r[2], "cd_ratio_pct": r[7], "casa_ratio_pct": r[5]})
            if dp_rows:
                l = dp_rows[-1]
                deposits_data = {
                    "period": l[0], "aggregate_deposits_cr": l[1], "deposits_yoy_pct": l[2], "demand_deposits_cr": l[3],
                    "time_deposits_cr": l[4], "casa_ratio_pct": l[5], "bank_credit_cr": l[6], "cd_ratio_pct": l[7],
                    "citation": parse_citation(l[8]), "is_real_data": True,
                }
    except Exception as exc:
        logger.exception("Finance telemetry query error: %s", exc)

    return {
        "credit_growth": credit_data, "asset_quality": asset_data,
        "lending_rates": rates_data, "deposits_cd_ratio": deposits_data,
        "timeseries": timeseries,
    }


def query_fiscal_telemetry() -> Dict[str, Any]:
    gst_list: List[Dict[str, Any]] = []
    deficit_list: List[Dict[str, Any]] = []
    debt_list: List[Dict[str, Any]] = []
    latest_gst = None
    latest_deficit = None
    latest_debt = None

    try:
        from fiscal_sector.database import get_connection as get_fiscal_db
        with get_fiscal_db() as conn:
            gst_rows = conn.execute(
                "SELECT period, gross_gst_cr, cgst_cr, sgst_cr, igst_cr, cess_cr, yoy_growth_pct, citation "
                "FROM gst_collections ORDER BY id ASC"
            ).fetchall()
            for r in gst_rows:
                gst_list.append({"period": r[0], "gross_gst_cr": r[1], "cgst_cr": r[2], "sgst_cr": r[3], "igst_cr": r[4], "cess_cr": r[5], "yoy_growth_pct": r[6], "citation": parse_citation(r[7])})
            if gst_list:
                latest_gst = gst_list[-1]

            def_rows = conn.execute(
                "SELECT period, fiscal_deficit_cr, fiscal_deficit_gdp_pct, citation "
                "FROM union_fiscal_deficit ORDER BY id ASC"
            ).fetchall()
            for r in def_rows:
                deficit_list.append({"period": r[0], "fiscal_deficit_cr": r[1], "fiscal_deficit_gdp_pct": r[2], "citation": parse_citation(r[3])})
            if deficit_list:
                latest_deficit = deficit_list[-1]

            debt_rows = conn.execute(
                "SELECT period, general_govt_gross_debt_gdp_pct, citation FROM general_govt_debt ORDER BY id ASC"
            ).fetchall()
            for r in debt_rows:
                debt_list.append({"period": r[0], "general_govt_gross_debt_gdp_pct": r[1], "citation": parse_citation(r[2])})
            if debt_list:
                latest_debt = debt_list[-1]
    except Exception as exc:
        logger.warning("Fiscal telemetry query skipped: %s", exc)

    return {
        "latest_gst": latest_gst, "latest_deficit": latest_deficit, "latest_debt": latest_debt,
        "gst_history": gst_list, "deficit_history": deficit_list, "debt_history": debt_list,
    }


def query_external_telemetry() -> Dict[str, Any]:
    fx_history: List[Dict[str, Any]] = []
    reserves_history: List[Dict[str, Any]] = []
    trade_history: List[Dict[str, Any]] = []
    latest_fx = None
    latest_reserves = None
    latest_trade = None

    try:
        p = Path(__file__).resolve().parents[1] / "external_sector" / "data" / "external_sector.duckdb"
        if p.exists():
            with duckdb.connect(str(p), read_only=True) as conn:
                fx_rows = conn.execute("SELECT period, usd_inr_rate, citation FROM exchange_rates ORDER BY id ASC").fetchall()
                for r in fx_rows[-30:]:
                    fx_history.append({"period": r[0], "usd_inr_rate": r[1], "citation": parse_citation(r[2])})
                if fx_rows:
                    latest_fx = {"period": fx_rows[-1][0], "usd_inr_rate": fx_rows[-1][1], "citation": parse_citation(fx_rows[-1][2])}

                res_rows = conn.execute("SELECT period, total_reserves_usd_mn, total_reserves_inr_cr, citation FROM forex_reserves ORDER BY id ASC").fetchall()
                for r in res_rows[-24:]:
                    reserves_history.append({"period": r[0], "total_reserves_usd_mn": r[1], "total_reserves_inr_cr": r[2], "citation": parse_citation(r[3])})
                if res_rows:
                    latest_reserves = {"period": res_rows[-1][0], "total_reserves_usd_mn": res_rows[-1][1], "citation": parse_citation(res_rows[-1][3])}

                tr_rows = conn.execute("SELECT period, exports_usd_bn, imports_usd_bn, citation FROM trade_balance ORDER BY id ASC").fetchall()
                for r in tr_rows[-12:]:
                    trade_history.append({"period": r[0], "exports_usd_bn": r[1], "imports_usd_bn": r[2], "trade_deficit_usd_bn": round(r[2] - r[1], 2), "citation": parse_citation(r[3])})
                if tr_rows:
                    latest_trade = {"period": tr_rows[-1][0], "exports_usd_bn": tr_rows[-1][1], "imports_usd_bn": tr_rows[-1][2], "trade_deficit_usd_bn": round(tr_rows[-1][2] - tr_rows[-1][1], 2), "citation": parse_citation(tr_rows[-1][3])}
    except Exception as exc:
        logger.warning("External telemetry error: %s", exc)

    return {
        "latest_fx": latest_fx, "latest_reserves": latest_reserves, "latest_trade": latest_trade,
        "fx_history": fx_history, "reserves_history": reserves_history, "trade_history": trade_history,
    }


def query_capmarkets_telemetry() -> Dict[str, Any]:
    gsec_history: List[Dict[str, Any]] = []
    vix_history: List[Dict[str, Any]] = []
    latest_gsec = None
    latest_vix = None

    try:
        p = Path(__file__).resolve().parents[1] / "capital_market_sector" / "data" / "capital_market_sector.duckdb"
        if p.exists():
            with duckdb.connect(str(p), read_only=True) as conn:
                gsec_rows = conn.execute("SELECT period, ten_year_gsec_yield_pct, five_year_gsec_yield_pct, citation FROM gsec_yields ORDER BY id ASC").fetchall()
                for r in gsec_rows[-16:]:
                    gsec_history.append({"period": r[0], "ten_year_gsec_yield_pct": r[1], "five_year_gsec_yield_pct": r[2], "citation": parse_citation(r[3])})
                if gsec_rows:
                    latest_gsec = {"period": gsec_rows[-1][0], "ten_year_gsec_yield_pct": gsec_rows[-1][1], "citation": parse_citation(gsec_rows[-1][3])}

                vix_rows = conn.execute("SELECT period, vix_close, citation FROM india_vix ORDER BY id ASC").fetchall()
                for r in vix_rows[-16:]:
                    vix_history.append({"period": r[0], "vix_close": r[1], "citation": parse_citation(r[2])})
                if vix_rows:
                    latest_vix = {"period": vix_rows[-1][0], "vix_close": vix_rows[-1][1], "citation": parse_citation(vix_rows[-1][2])}
    except Exception as exc:
        logger.warning("Capital markets telemetry error: %s", exc)

    return {"latest_gsec": latest_gsec, "latest_vix": latest_vix, "gsec_history": gsec_history, "vix_history": vix_history}


def query_labour_telemetry() -> Dict[str, Any]:
    unemp_history: List[Dict[str, Any]] = []
    latest_unemp = None
    latest_lfpr = None

    try:
        p = Path(__file__).resolve().parents[1] / "labour_sector" / "data" / "labour_sector.duckdb"
        if p.exists():
            with duckdb.connect(str(p), read_only=True) as conn:
                u_rows = conn.execute("SELECT period, unemployment_rate_pct, unemployment_rate_urban_pct, citation FROM unemployment ORDER BY id ASC").fetchall()
                for r in u_rows[-12:]:
                    unemp_history.append({"period": r[0], "unemployment_rate_pct": r[1], "citation": parse_citation(r[3])})
                if u_rows:
                    latest_unemp = {"period": u_rows[-1][0], "unemployment_rate_pct": u_rows[-1][1], "citation": parse_citation(u_rows[-1][3])}

                l_rows = conn.execute("SELECT period, lfpr_total_pct, citation FROM lfpr ORDER BY id DESC LIMIT 1").fetchone()
                if l_rows:
                    latest_lfpr = {"period": l_rows[0], "lfpr_total_pct": l_rows[1], "citation": parse_citation(l_rows[2])}
    except Exception as exc:
        logger.warning("Labour telemetry error: %s", exc)

    return {"latest_unemp": latest_unemp, "latest_lfpr": latest_lfpr, "unemp_history": unemp_history}


def query_monetary_telemetry() -> Dict[str, Any]:
    latest_rates = None
    try:
        p = Path(__file__).resolve().parents[1] / "monetary_sector" / "data" / "monetary_sector.duckdb"
        if p.exists():
            with duckdb.connect(str(p), read_only=True) as conn:
                r_row = conn.execute("SELECT period, repo_rate_pct, reverse_repo_rate_pct, citation FROM policy_rates ORDER BY id DESC LIMIT 1").fetchone()
                if r_row:
                    latest_rates = {"period": r_row[0], "repo_rate_pct": r_row[1], "reverse_repo_rate_pct": r_row[2], "citation": parse_citation(r_row[3])}
    except Exception as exc:
        logger.warning("Monetary telemetry error: %s", exc)
    return {"latest_rates": latest_rates}


def query_real_telemetry() -> Dict[str, Any]:
    latest_core = None
    try:
        from real_sector.database import get_connection as get_real_db
        with get_real_db() as conn:
            row = conn.execute("SELECT period, overall_ici_yoy_pct, coal_yoy_pct, crude_oil_yoy_pct, steel_yoy_pct, cement_yoy_pct, electricity_yoy_pct, citation FROM core_industries ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                latest_core = {
                    "period": row[0], "overall_ici_yoy_pct": row[1],
                    "sectoral": {"coal": row[2], "crude_oil": row[3], "steel": row[4], "cement": row[5], "electricity": row[6]},
                    "citation": parse_citation(row[7]),
                }
    except Exception as exc:
        logger.warning("Real telemetry query error: %s", exc)
    return {"latest_core": latest_core}


def query_services_telemetry() -> Dict[str, Any]:
    latest_pmi = None
    try:
        from services_sector.database import get_connection as get_services_db
        with get_services_db() as conn:
            row = conn.execute("SELECT period, headline_pmi, citation FROM services_pmi ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                latest_pmi = {"period": row[0], "headline_pmi": row[1], "citation": parse_citation(row[2])}
    except Exception as exc:
        logger.warning("Services telemetry query error: %s", exc)
    return {"latest_pmi": latest_pmi}
