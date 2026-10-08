"""Short indicator names mapped to canonical indicator ids (single source of truth)."""
from __future__ import annotations

CANONICAL_ID_MAP = {
    # Real sector
    "gdp_growth": "in.macro.real.gdp_growth",
    "real_gdp_growth": "in.macro.real.gdp_growth",
    "iip_growth": "in.macro.real.iip_growth",
    "iip_manufacturing": "in.macro.real.iip_growth",
    "manufacturing_iip": "in.macro.real.iip_growth",
    "industry": "in.macro.real.iip_growth",
    "national_income": "in.macro.real.gdp_growth",
    "manufacturing_gva": "in.macro.real.gdp_growth",
    "eight_core_industries": "in.macro.real.core_industries",
    "core_industries": "in.macro.real.core_industries",

    # Prices sector
    "cpi_inflation": "in.macro.prices.cpi_headline",
    "cpi_headline": "in.macro.prices.cpi_headline",
    "cpi_headline_combined_yoy": "in.macro.prices.cpi_headline",
    "cpi_general": "in.macro.prices.cpi_headline",
    "prices": "in.macro.prices.cpi_headline",
    "cpi_food": "in.macro.prices.cpi_food",
    "wpi_all": "in.macro.prices.wpi_all",
    "brent_crude": "in.macro.prices.brent_crude",
    "brent_crude_oil": "in.macro.prices.brent_crude",

    # Monetary sector
    "repo_rate": "in.macro.monetary.repo_rate",
    "policy_repo_rate": "in.macro.monetary.repo_rate",
    "monetary": "in.macro.monetary.repo_rate",
    "bank_credit_growth": "in.macro.monetary.bank_credit_growth",
    "m3_growth": "in.macro.monetary.m3_growth",
    "m3_money_supply": "in.macro.monetary.m3_growth",
    "m3_money_supply_yoy": "in.macro.monetary.m3_growth",

    # Fiscal sector
    "debt_to_gdp": "in.macro.fiscal.debt_to_gdp",
    "general_govt_debt_gdp_pct": "in.macro.fiscal.debt_to_gdp",
    "fiscal_deficit": "in.macro.fiscal.fiscal_deficit",
    "fiscal_deficit_cr": "in.macro.fiscal.fiscal_deficit",
    "fiscal_deficit_gdp_pct": "in.macro.fiscal.fiscal_deficit",
    "central_capex": "in.macro.fiscal.central_capex",
    "capital_expenditure_cr": "in.macro.fiscal.central_capex",
    "gross_gst_cr": "in.macro.fiscal.gst_gross_revenue",
    "gst_gross_revenue": "in.macro.fiscal.gst_gross_revenue",
    "mospi_net_taxes_cr": "in.macro.fiscal.mospi_product_taxes",

    # External sector
    "forex_reserves": "in.macro.external.forex_reserves",
    "total_forex_reserves": "in.macro.external.forex_reserves",
    "total_reserves": "in.macro.external.forex_reserves",
    "trade_balance": "in.macro.external.trade_balance",
    "merchandise_trade_balance": "in.macro.external.trade_balance",
    "usd_inr": "in.macro.external.usd_inr",
    "usd_inr_exchange_rate": "in.macro.external.usd_inr",
    "exchange_rate": "in.macro.external.usd_inr",
    "private_remittances": "in.macro.external.remittances",
    "external_debt": "in.macro.external.external_debt",
    "external_debt_stock": "in.macro.external.external_debt",

    # Capital markets & labour
    "nifty_50": "in.macro.capmarkets.nifty_50",
    "equity": "in.macro.capmarkets.nifty_50",
    "india_vix": "in.macro.capmarkets.india_vix",
    "vix": "in.macro.capmarkets.india_vix",
    "foodgrain_production": "in.macro.agri.foodgrain_production",
    "agriculture": "in.macro.agri.foodgrain_production",
    "epfo_additions": "in.macro.labour.epfo_additions",
    "unemployment_rate": "in.macro.labour.unemployment_rate",
}


def resolve_canonical_id(raw_name: str, sector: str | None = None) -> str:
    """Normalize raw indicator names/codes to the canonical schema (in.macro.<sector>.<name>)."""
    raw_str = str(raw_name).strip()
    if raw_str.startswith("in.macro."):
        return raw_str

    normalized = (
        raw_str.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "_")
    )
    if normalized in CANONICAL_ID_MAP:
        return CANONICAL_ID_MAP[normalized]

    for k, v in CANONICAL_ID_MAP.items():
        if k == normalized or (len(k) > 4 and k in normalized):
            return v

    prefix = sector.replace("_sector", "") if sector else "indicator"
    return f"in.macro.{prefix}.{normalized}"

