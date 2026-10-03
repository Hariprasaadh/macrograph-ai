"""
Parsers for MoSPI PLFS responses.

The parsers convert raw PLFS API/MCP observations into the exact
schema expected by labour_sector.database.

Database contracts:

unemployment:
    period
    unemployment_rate_pct
    unemployment_rate_urban_pct
    unemployment_rate_rural_pct
    unemployment_rate_youth_pct
    citation

lfpr:
    period
    lfpr_total_pct
    lfpr_male_pct
    lfpr_female_pct
    lfpr_urban_pct
    lfpr_rural_pct
    citation

wpr:
    period
    wpr_total_pct
    wpr_male_pct
    wpr_female_pct
    wpr_urban_pct
    wpr_rural_pct
    citation

labour_conditions:
    period
    epfo_net_additions_thousands
    self_employed_share_pct
    regular_wage_share_pct
    casual_labour_share_pct
    citation
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any


_MOSPI_CITATION = "https://mcp.mospi.gov.in/"


# ---------------------------------------------------------------------------
# Generic response extraction
# ---------------------------------------------------------------------------

def _decode_json(value: Any) -> Any:
    """Decode JSON stored inside a string."""

    if not isinstance(value, str):
        return value

    text = value.strip()

    if not text:
        return value

    if not (
        text.startswith("{")
        or text.startswith("[")
    ):
        return value

    try:
        import json

        return json.loads(text)

    except (TypeError, ValueError):
        return value


def _find_records(payload: Any) -> list[dict[str, Any]]:
    """
    Locate tabular records in a MoSPI response.

    Supports common response shapes without assuming that every
    MoSPI release uses the same outer envelope.
    """

    payload = _decode_json(payload)

    if payload is None:
        return []

    if isinstance(payload, list):

        records = [
            item
            for item in payload
            if isinstance(item, dict)
        ]

        if records:
            return records

        for item in payload:

            records = _find_records(item)

            if records:
                return records

        return []

    if not isinstance(payload, dict):
        return []

    # Direct tabular containers.
    for key in (
        "data",
        "records",
        "results",
        "rows",
        "items",
        "observations",
    ):

        if key not in payload:
            continue

        value = _decode_json(
            payload[key]
        )

        if isinstance(value, list):

            records = [
                item
                for item in value
                if isinstance(item, dict)
            ]

            if records:
                return records

        if isinstance(value, dict):

            records = _find_records(value)

            if records:
                return records

    # A dictionary may itself be a record.
    if _looks_like_record(payload):
        return [payload]

    # Recursive fallback.
    for value in payload.values():

        if isinstance(value, (dict, list)):

            records = _find_records(value)

            if records:
                return records

    return []


def _looks_like_record(
    value: dict[str, Any],
) -> bool:

    keys = {
        str(key).lower()
        for key in value.keys()
    }

    known_fields = {
        "year",
        "period",
        "year_code",
        "state_code",
        "gender_code",
        "age_code",
        "sector_code",
        "quarter_code",
        "value",
        "indicator_value",
        "indicatorvalue",
        "rate",
        "percentage",
        "percent",
        "estimate",
        "value_percent",
        "value_pct",
    }

    return bool(
        keys.intersection(known_fields)
    )


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

def _first(
    record: dict[str, Any],
    *names: str,
) -> Any:

    lowered = {
        str(key).lower(): value
        for key, value in record.items()
    }

    for name in names:

        value = lowered.get(
            name.lower()
        )

        if value is not None:
            return value

    return None


def _number(value: Any) -> float | None:

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return None

        text = (
            text
            .replace(",", "")
            .replace("%", "")
        )

        try:
            return float(text)

        except ValueError:
            return None

    return None


def _text(value: Any) -> str | None:

    if value is None:
        return None

    text = str(value).strip()

    return text if text else None


def _period(
    record: dict[str, Any],
) -> str | None:

    period = _first(
        record,
        "period",
    )
    year = _first(
        record,
        "year",
        "year_code",
        "financial_year",
        "survey_year",
        "year_name",
    )
    month = _first(record, "month", "month_code", "month_name")

    def dimension_label(value: Any) -> str | None:
        if isinstance(value, dict):
            value = next(
                (value[key] for key in ("name", "label", "value", "code") if value.get(key) is not None),
                None,
            )
        return _text(value)

    period_text = dimension_label(period)
    year_text = dimension_label(year)
    month_text = dimension_label(month)

    if year_text and month_text and re.fullmatch(r"\d{4}", year_text):
        month_number: int | None = None
        if month_text.isdigit():
            month_number = int(month_text)
        else:
            for month_format in ("%B", "%b"):
                try:
                    month_number = datetime.strptime(month_text, month_format).month
                    break
                except ValueError:
                    continue
        if month_number is not None and 1 <= month_number <= 12:
            return f"{year_text}-{month_number:02d}"

    if period_text and re.fullmatch(r"\d{4}[-/]\d{1,2}", period_text):
        year_part, month_part = re.split(r"[-/]", period_text)
        if 1 <= int(month_part) <= 12:
            return f"{year_part}-{int(month_part):02d}"

    if period_text:
        return period_text

    if year_text:
        return year_text

    return dimension_label(_first(record, "quarter", "quarter_name"))


def _value(
    record: dict[str, Any],
) -> float | None:

    return _number(
        _first(
            record,
            "value",
            "indicator_value",
            "indicatorvalue",
            "rate",
            "percentage",
            "percent",
            "estimate",
            "value_percent",
            "value_pct",
            "observation",
            "obs_value",
        )
    )


def _indicator_name(
    record: dict[str, Any],
) -> str:

    value = _first(
        record,
        "indicator",
        "indicator_name",
        "indicatorname",
        "name",
    )

    return (
        str(value).strip().lower()
        if value is not None
        else ""
    )


def _dimension_text(
    record: dict[str, Any],
    *names: str,
) -> str:

    value = _first(
        record,
        *names,
    )

    if value is None:
        return ""

    return str(value).strip().lower()


# ---------------------------------------------------------------------------
# Dimension classification
# ---------------------------------------------------------------------------

def _is_male(
    record: dict[str, Any],
) -> bool:

    text = _dimension_text(
        record,
        "gender",
        "gender_name",
        "sex",
        "sex_name",
    )

    code = _first(
        record,
        "gender_code",
        "gendercode",
    )

    return (
        text in {"male", "men", "m"}
        or str(code) == "1"
    )


def _is_female(
    record: dict[str, Any],
) -> bool:

    text = _dimension_text(
        record,
        "gender",
        "gender_name",
        "sex",
        "sex_name",
    )

    code = _first(
        record,
        "gender_code",
        "gendercode",
    )

    return (
        text in {"female", "women", "f"}
        or str(code) == "2"
    )


def _is_urban(
    record: dict[str, Any],
) -> bool:

    text = _dimension_text(
        record,
        "sector",
        "sector_name",
        "area",
        "area_name",
    )

    code = _first(
        record,
        "sector_code",
        "sectorcode",
    )

    return (
        text == "urban"
        or str(code) == "2"
    )


def _is_rural(
    record: dict[str, Any],
) -> bool:

    text = _dimension_text(
        record,
        "sector",
        "sector_name",
        "area",
        "area_name",
    )

    code = _first(
        record,
        "sector_code",
        "sectorcode",
    )

    return (
        text == "rural"
        or str(code) == "1"
    )


def _is_youth(
    record: dict[str, Any],
) -> bool:

    text = _dimension_text(
        record,
        "age",
        "age_group",
        "agegroup",
        "age_name",
    )

    code = _first(
        record,
        "age_code",
        "agecode",
    )

    youth_terms = {
        "15-29",
        "15 to 29",
        "youth",
        "15–29",
    }

    return (
        text in youth_terms
        or str(code) in {
            "2",
            "3",
        }
    )


def _is_total(
    record: dict[str, Any],
) -> bool:

    gender = _first(
        record,
        "gender_code",
        "gendercode",
    )

    sector = _first(
        record,
        "sector_code",
        "sectorcode",
    )

    age = _first(
        record,
        "age_code",
        "agecode",
    )

    gender_text = _dimension_text(
        record,
        "gender",
        "gender_name",
        "sex",
        "sex_name",
    )

    sector_text = _dimension_text(
        record,
        "sector",
        "sector_name",
        "area",
        "area_name",
    )

    return (
        str(gender) in {"3", "0", "99"}
        or gender_text in {
            "total",
            "all",
            "person",
            "persons",
        }
    ) and (
        str(sector) in {"3", "0", "99"}
        or sector_text in {
            "total",
            "all",
            "all india",
            "rural + urban",
            "rural and urban",
            "rural & urban",
        }
    ) and (
        str(age) in {"1", "4", "0", "99"}
        or age is None
        or _dimension_text(record, "age", "age_group", "agegroup", "age_name")
        in {"15 years and above", "15 years+", "15+", "age 15 and above"}
    )


# ---------------------------------------------------------------------------
# Unemployment
# ---------------------------------------------------------------------------

def parse_unemployment_records(
    payload: Any,
) -> list[dict[str, Any]]:

    records = _find_records(
        payload
    )

    if not records:
        return []

    grouped: dict[str, dict[str, Any]] = {}

    for record in records:

        period = _period(record)
        value = _value(record)

        if period is None or value is None:
            continue

        if period not in grouped:

            grouped[period] = {
                "period": period,
                "unemployment_rate_pct": None,
                "unemployment_rate_urban_pct": None,
                "unemployment_rate_rural_pct": None,
                "unemployment_rate_youth_pct": None,
                "citation": _MOSPI_CITATION,
            }

        row = grouped[period]

        if _is_youth(record):
            row[
                "unemployment_rate_youth_pct"
            ] = value

        elif _is_urban(record):
            row[
                "unemployment_rate_urban_pct"
            ] = value

        elif _is_rural(record):
            row[
                "unemployment_rate_rural_pct"
            ] = value

        elif _is_total(record):
            row[
                "unemployment_rate_pct"
            ] = value

        else:
            # If dimensions are absent, treat the observation as
            # the aggregate value rather than inventing a dimension.
            if (
                row["unemployment_rate_pct"]
                is None
            ):
                row[
                    "unemployment_rate_pct"
                ] = value

    return list(
        grouped.values()
    )


# ---------------------------------------------------------------------------
# LFPR
# ---------------------------------------------------------------------------

def parse_lfpr_records(
    payload: Any,
) -> list[dict[str, Any]]:

    records = _find_records(
        payload
    )

    if not records:
        return []

    grouped: dict[str, dict[str, Any]] = {}

    for record in records:

        period = _period(record)
        value = _value(record)

        if period is None or value is None:
            continue

        if period not in grouped:

            grouped[period] = {
                "period": period,
                "lfpr_total_pct": None,
                "lfpr_male_pct": None,
                "lfpr_female_pct": None,
                "lfpr_urban_pct": None,
                "lfpr_rural_pct": None,
                "citation": _MOSPI_CITATION,
            }

        row = grouped[period]

        if _is_male(record):
            row["lfpr_male_pct"] = value

        elif _is_female(record):
            row["lfpr_female_pct"] = value

        elif _is_urban(record):
            row["lfpr_urban_pct"] = value

        elif _is_rural(record):
            row["lfpr_rural_pct"] = value

        elif _is_total(record):
            row["lfpr_total_pct"] = value

        else:
            if row["lfpr_total_pct"] is None:
                row["lfpr_total_pct"] = value

    return list(
        grouped.values()
    )


# ---------------------------------------------------------------------------
# WPR
# ---------------------------------------------------------------------------

def parse_wpr_records(
    payload: Any,
) -> list[dict[str, Any]]:

    records = _find_records(
        payload
    )

    if not records:
        return []

    grouped: dict[str, dict[str, Any]] = {}

    for record in records:

        period = _period(record)
        value = _value(record)

        if period is None or value is None:
            continue

        if period not in grouped:

            grouped[period] = {
                "period": period,
                "wpr_total_pct": None,
                "wpr_male_pct": None,
                "wpr_female_pct": None,
                "wpr_urban_pct": None,
                "wpr_rural_pct": None,
                "citation": _MOSPI_CITATION,
            }

        row = grouped[period]

        if _is_male(record):
            row["wpr_male_pct"] = value

        elif _is_female(record):
            row["wpr_female_pct"] = value

        elif _is_urban(record):
            row["wpr_urban_pct"] = value

        elif _is_rural(record):
            row["wpr_rural_pct"] = value

        elif _is_total(record):
            row["wpr_total_pct"] = value

        else:
            if row["wpr_total_pct"] is None:
                row["wpr_total_pct"] = value

    return list(
        grouped.values()
    )


# ---------------------------------------------------------------------------
# Employment conditions
# ---------------------------------------------------------------------------

def parse_labour_records(
    payload: Any,
) -> list[dict[str, Any]]:

    records = _find_records(
        payload
    )

    if not records:
        return []

    grouped: dict[str, dict[str, Any]] = {}

    for record in records:

        period = _period(record)
        value = _value(record)

        if period is None or value is None:
            continue

        if period not in grouped:

            grouped[period] = {
                "period": period,
                "epfo_net_additions_thousands": None,
                "self_employed_share_pct": None,
                "regular_wage_share_pct": None,
                "casual_labour_share_pct": None,
                "citation": _MOSPI_CITATION,
            }

        row = grouped[period]

        indicator = _indicator_name(
            record
        )

        if (
            "self" in indicator
            and "employ" in indicator
        ):
            row[
                "self_employed_share_pct"
            ] = value

        elif (
            "regular" in indicator
            and (
                "wage" in indicator
                or "salary" in indicator
            )
        ):
            row[
                "regular_wage_share_pct"
            ] = value

        elif (
            "casual" in indicator
            or "casual labour" in indicator
        ):
            row[
                "casual_labour_share_pct"
            ] = value

        elif (
            "epfo" in indicator
            or "net addition" in indicator
        ):
            row[
                "epfo_net_additions_thousands"
            ] = value

    return list(
        grouped.values()
    )