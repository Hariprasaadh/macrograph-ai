"""Parsers for Monetary Sector external responses.

Converts raw RBI DBIE JSON payloads into validated Pydantic models with citations.
"""
from __future__ import annotations

import logging
from typing import Any

from monetary_sector.models import (
    Citation,
    DataFreshness,
    MoneySupplyRecord,
    MonetaryStanceRecord,
    PolicyRatesRecord,
    SystemLiquidityRecord,
)

logger = logging.getLogger(__name__)


def safe_float_val(val: Any) -> float | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        cleaned = str(val).replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _citation(
    source: dict[str, Any],
    period: str,
    source_values: dict[str, Any],
    unit: str | None = None,
) -> Citation:
    return Citation(
        source_authority="Reserve Bank of India (RBI)",
        document_title=str(source["document_title"]),
        table_reference=str(source["table_reference"]),
        retrieval_url=str(source["retrieval_url"]),
        observation_period=period,
        freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        source_base_url=source.get("source_base_url"),
        source_note=source.get("source_note"),
        as_of=source.get("as_of"),
        frequency=source.get("frequency"),
        unit=unit or source.get("unit"),
        source_values=source_values,
    )


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def parse_policy_rates(
    payload: dict[str, Any],
    lookback_limit: int = 12,
    source: dict[str, Any] | None = None,
) -> list[PolicyRatesRecord]:
    source = source or {}
    rows = _payload_rows(payload)
    records: list[PolicyRatesRecord] = []

    for row in rows:
        period = str(row.get("month") or row.get("date") or "").strip()
        if not period:
            continue

        values = {
            "repo_rate_pct": safe_float_val(row.get("policy_repo_rate")),
            "reverse_repo_rate_pct": safe_float_val(row.get("reverse_repo_rate")),
            "sdf_rate_pct": safe_float_val(row.get("sdf_rate")),
            "msf_rate_pct": safe_float_val(row.get("msf_rate")),
            "bank_rate_pct": safe_float_val(row.get("bank_rate")),
            "crr_pct": safe_float_val(row.get("crr")),
            "slr_pct": safe_float_val(row.get("slr")),
        }
        if not any(value is not None for value in values.values()):
            continue

        records.append(
            PolicyRatesRecord(
                period=period,
                **values,
                citation=_citation(source, period, row, unit="%"),
            )
        )

    if not records:
        raise ValueError("DBIE Select Economic Indicators contained no usable policy-rate records.")
    return records[:lookback_limit]


def parse_money_supply(
    payload: dict[str, Any],
    lookback_limit: int = 12,
    source: dict[str, Any] | None = None,
) -> list[MoneySupplyRecord]:
    source = source or {}
    records: list[MoneySupplyRecord] = []
    for item in _payload_rows(payload):
        period = str(item.get("date") or item.get("period") or item.get("month") or "").strip()
        values = item.get("values")
        if not period or not isinstance(values, dict):
            continue
        normalized = {
            "currency_with_public_cr": safe_float_val(values.get("currencyWithThePublic")),
            "demand_deposits_cr": safe_float_val(values.get("demandDepositsWithBanks")),
            "other_deposits_rbi_cr": safe_float_val(values.get("otherDepositsWithReserveBank")),
            "m1_cr": safe_float_val(values.get("m1")),
            "post_office_savings_cr": safe_float_val(values.get("postOfficeSavingsDeposits")),
            "m2_cr": safe_float_val(values.get("m2")),
            "time_deposits_cr": safe_float_val(values.get("timeDepositsWithBanks")),
            "m3_cr": safe_float_val(values.get("m3")),
            "m3_yoy_pct": safe_float_val(values.get("m3YoYGrowthPct")),
        }
        if not any(value is not None for value in normalized.values()):
            continue
        records.append(
            MoneySupplyRecord(
                period=period,
                **normalized,
                citation=_citation(
                    source, period, values, unit=payload.get("units") or payload.get("unit"),
                ),
            )
        )

    if not records:
        raise ValueError("DBIE Money Stock Measures contained no usable records.")
    return records[:lookback_limit]


def parse_system_liquidity(
    payload: dict[str, Any],
    lookback_limit: int = 6,
    source: dict[str, Any] | None = None,
) -> list[SystemLiquidityRecord]:
    source = source or {}
    records: list[SystemLiquidityRecord] = []
    for row in _payload_rows(payload):
        period = str(row.get("date") or row.get("period") or "").strip()
        if not period:
            continue
        values = {
            "laf_repo_cr": safe_float_val(row.get("repo")),
            "laf_reverse_repo_cr": safe_float_val(row.get("reverse_repo")),
            "msf_operations_cr": safe_float_val(row.get("msf")),
        }
        if not any(value is not None for value in values.values()):
            continue
        records.append(
            SystemLiquidityRecord(
                period=period,
                **values,
                net_laf_absorption_cr=None,
                liquidity_condition=None,
                citation=_citation(
                    source, period, row, unit=payload.get("unit") or payload.get("units"),
                ),
            )
        )
    if not records:
        raise ValueError("DBIE Liquidity Operations contained no usable operation records.")
    return records[:lookback_limit]
