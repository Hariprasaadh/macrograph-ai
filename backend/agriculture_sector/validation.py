"""Agriculture-only unit, period, freshness and trend validation.

This module implements the retrieval/normalization checks before records
reach the LLM. It is imported only by ``agriculture_sector`` code; no other
sector (Capital Market or otherwise) depends on it.
"""
from __future__ import annotations

import re
from typing import Any

# Rule 5: explicit conversion factors to tonnes. No silent relabelling:
# a value reported in lakh tonnes must never be presented as million tonnes.
# Canonical base for production quantities is tonnes.
TONNES_PER_UNIT: dict[str, float] = {
    "tonne": 1.0,
    "tonnes": 1.0,
    "metric tonne": 1.0,
    "metric tonnes": 1.0,
    "ton": 1.0,
    "tons": 1.0,
    "mt": 1_000_000.0,
    "mmt": 1_000_000.0,
    "million tonne": 1_000_000.0,
    "million tonnes": 1_000_000.0,
    "million metric tonne": 1_000_000.0,
    "million metric tonnes": 1_000_000.0,
    "lakh tonne": 100_000.0,
    "lakh tonnes": 100_000.0,
    "lakh metric tonne": 100_000.0,
    "lakh metric tonnes": 100_000.0,
    "lmt": 100_000.0,
    "thousand tonne": 1_000.0,
    "thousand tonnes": 1_000.0,
    "crore tonne": 10_000_000.0,
    "crore tonnes": 10_000_000.0,
}

# Bales are a different physical scale (cotton). Keep them separate and never
# convert bales to tonnes without an explicit, sourced bale-weight factor.
BALE_UNITS = {
    "bale", "bales", "lakh bales", "million bales", "thousand bales",
    "000 bales",
}

_ESTIMATE_PATTERN = re.compile(
    r"\b(first|second|third|fourth|final|provisional|revised)\s+(advance\s+)?estimates?\b",
    re.IGNORECASE,
)

_PERIOD_TOKEN = re.compile(r"\b((?:19|20)\d{2}(?:[-/](?:\d{2}|20\d{2}))?)\b")

# Broad plausibility envelopes (tonnes) for national-level production.
# Deliberately wide: they only catch order-of-magnitude unit/scale errors
# (e.g. lakh labelled as million), never agronomic judgement.
NATIONAL_TONNES_RANGE: dict[str, tuple[float, float]] = {
    "rice": (10_000_000.0, 250_000_000.0),
    "wheat": (10_000_000.0, 200_000_000.0),
    # India groundnut output is single-digit MMT (e.g. ~10 MMT in 2021-22,
    # ~13 MMT in 2025-26 3rd advance estimate). A "102.97 million tonnes"
    # claim is ~10x too large (102.97 lakh tonnes = 10.297 MMT) and must fail.
    "groundnut": (1_000_000.0, 25_000_000.0),
    "default": (100_000.0, 500_000_000.0),
}


def display_with_equivalent(value_text: str, unit: str) -> str:
    """Render 'X lakh tonnes (= Y million tonnes)' so scale is unambiguous.

    The source unit is always preserved verbatim; the parenthetical
    equivalent uses the explicit lakh<->million factor (1 lakh tonne =
    0.1 million tonnes) and can never silently relabel the figure.
    """
    try:
        number = float(str(value_text).replace(",", ""))
    except (TypeError, ValueError):
        return f"{value_text} {unit}".strip()
    cleaned = re.sub(r"\s+", " ", (unit or "").strip().casefold())
    lakh_units = {"lakh tonne", "lakh tonnes", "lakh metric tonne",
                  "lakh metric tonnes", "lmt"}
    million_units = {"million tonne", "million tonnes",
                     "million metric tonne", "million metric tonnes",
                     "mmt", "mt"}
    if cleaned in lakh_units:
        return f"{value_text} {unit} (= {number / 10:g} million tonnes)"
    if cleaned in million_units:
        return f"{value_text} {unit} (= {number * 10:g} lakh tonnes)"
    return f"{value_text} {unit}".strip()


def normalize_unit(unit_text: str) -> tuple[str, float | None]:
    """Return (canonical_scale_label, factor_to_tonnes). Factor None for bales/other."""
    cleaned = re.sub(r"\s+", " ", (unit_text or "").strip().casefold())
    if not cleaned:
        return "", None
    if cleaned in BALE_UNITS or "bale" in cleaned:
        return cleaned, None
    factor = TONNES_PER_UNIT.get(cleaned)
    if factor is not None:
        return cleaned, factor
    # Accept common variants such as "million tonnes (mt)".
    for key, value in TONNES_PER_UNIT.items():
        if key in cleaned or cleaned in key:
            return cleaned, value
    return cleaned, None


def to_tonnes(value: float, unit_text: str) -> float | None:
    """Explicit conversion to tonnes; None when the unit is not mass-based."""
    _, factor = normalize_unit(unit_text)
    if factor is None:
        return None
    try:
        return float(value) * factor
    except (TypeError, ValueError):
        return None


def extract_estimate_type(text: str) -> str:
    """Return e.g. 'Third Advance Estimate' or '' when not stated."""
    match = _ESTIMATE_PATTERN.search(text or "")
    if not match:
        return ""
    return " ".join(word.capitalize() for word in match.group(0).split())


def normalize_reporting_period(text: str) -> str:
    """Preserve the full source period token (e.g. '2024-25', not '2024').

    Rule 2: calendar years, fiscal years and agricultural seasons are never
    treated as equivalent. The exact source token is returned.
    """
    tokens = [m.group(1) for m in _PERIOD_TOKEN.finditer(text or "")]
    return tokens[0] if tokens else ""


def period_start_year(period: str) -> int | None:
    """Leading year of a reporting-period token, or None."""
    match = re.match(r"((?:19|20)\d{2})", (period or "").strip())
    return int(match.group(1)) if match else None


def is_latest_query(query: str) -> bool:
    """True when the user asked for the newest observation without a fixed period."""
    q = (query or "").casefold()
    if not re.search(r"\blatest\b|\bcurrent\b|\bmost recent\b", q):
        return False
    if re.search(r"\b((?:19|20)\d{2}(?:[-/]\d{2,4})?)\b", q):
        return False
    if re.search(r"\bfrom\b.+\b(through|to|and)\b", q):
        return False
    if re.search(r"\b(trend|historical|history)\b", q):
        return False
    return True


def resolve_estimate_conflicts(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Rule 3: keep advance and final estimates for the same crop/year distinct.

    Never merges or overwrites rounds. Returns (rows, conflict_notes) where
    notes describe same (crop, period) groups with differing figures/estimates.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        crop = str(row.get("crop") or row.get("indicator") or "").casefold()
        period = str(row.get("year") or row.get("period") or "")
        groups.setdefault((crop, period), []).append(row)
    notes: list[str] = []
    for (crop, period), members in groups.items():
        figures = {(str(m.get("value")), str(m.get("unit")),
                    str(m.get("estimate_type") or "")) for m in members}
        if len(figures) > 1 and period:
            detail = "; ".join(
                f"{v} {u}" + (f" [{e}]" if e else "")
                for v, u, e in sorted(figures))
            notes.append(
                f"Separate source-reported estimates for {period}: {detail}. "
                "They are not merged or treated as interchangeable.")
    return rows, notes


def select_latest(
    candidates: list[dict[str, Any]],
    period_key: str = "period",
) -> dict[str, Any] | None:
    """Rule 4: prefer the newest valid reporting period across sources.

    Not merely the first API's newest record. Ties prefer advance estimates
    explicitly labelled as estimates (they are the newest observation round).
    """
    valid = [c for c in candidates if period_start_year(str(c.get(period_key) or ""))]
    if not valid:
        return None
    return max(valid, key=lambda c: (
        int(str(c.get(period_key))[:4]),
        bool(extract_estimate_type(
            str(c.get("estimate_type") or "") + " " + str(c.get("label") or ""))),
        str(c.get("published_date") or ""),
    ))


def validate_quantity(
    value: float | None, unit: str, crop: str, geography: str = "",
) -> tuple[bool, str]:
    """Rule 5: check value/unit/crop consistency via explicit conversion.

    Returns (ok, note). National-level orders of magnitude outside the
    authoritative envelope are flagged so the caller does not present the
    observation as verified. Sub-national or bale figures are not rejected
    here; they pass with their preserved source unit.
    """
    if value is None:
        return False, "numeric value missing"
    if not (unit or "").strip():
        return False, "unit missing"
    geo = (geography or "").casefold()
    national = ("india-wide" in geo or "national" in geo
                or "broader" in geo or geo.strip() == "")
    tonnes = to_tonnes(value, unit)
    if tonnes is None:
        # Non-mass units (bales): preserve as-is, no verified conversion.
        return True, "non-mass unit preserved without conversion"
    key = (crop or "").casefold()
    low, high = NATIONAL_TONNES_RANGE.get(key, NATIONAL_TONNES_RANGE["default"])
    if national and not (low <= tonnes <= high):
        return False, (
            f"{value:g} {unit} converts to {tonnes:,.0f} tonnes, outside the "
            f"expected national envelope for {crop or 'crop'}; not verified")
    return True, "quantity consistent after explicit conversion"


def trends_comparable(records: list[Any]) -> tuple[bool, str]:
    """Rule 6: trends need consistent units, periods and estimate types."""
    if len(records) < 2:
        return False, "fewer than two observations"
    canonical_units = set()
    for record in records:
        unit = getattr(record, "unit", "") or ""
        _, factor = normalize_unit(str(unit))
        canonical_units.add(("bale" if factor is None and "bale" in unit.casefold()
                             else f"{factor}"))
    if len(canonical_units) > 1:
        return False, "units differ across observations"
    periods = [str(getattr(record, "period", "") or "") for record in records]
    if any(not period_start_year(p) for p in periods):
        return False, "reporting periods are not explicitly assigned"
    if len(set(periods)) < 2:
        return False, "only one reporting period"
    estimates = {str(getattr(record, "estimate_type", None) or "") for record in records}
    if len(estimates) > 1:
        return False, "estimate rounds differ across observations"
    keys = {(getattr(r, "crop", None), getattr(r, "commodity", None),
             getattr(r, "state", None), getattr(r, "district", None),
             getattr(r, "season", None), getattr(r, "source", None),
             getattr(r, "dataset", None)) for r in records}
    coverage = {p: {k for rec, k in zip(records, keys)
                    if str(getattr(rec, "period", "")) == p} for p in set(periods)}
    if len({frozenset(v) for v in coverage.values()}) != 1:
        return False, "coverage differs by geography/season/source"
    return True, "observations share unit scale, periods and estimate type"


def concise_record(
    metric: str, value_text: str, unit: str, crop: str, geography: str,
    period: str, source_name: str, source_url: str,
    estimate_type: str | None = None,
) -> dict[str, Any]:
    """Rule 7: the only fields a concise agriculture answer needs."""
    return {
        "metric": metric, "value": value_text, "unit": unit, "crop": crop,
        "geography": geography, "reporting_period": period,
        "estimate_type": estimate_type or None,
        "source_name": source_name, "source_url": source_url,
    }
