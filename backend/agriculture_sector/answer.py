"""Agriculture-specific primary-answer selection, audit, and rendering.

Self-contained module: it uses only the Agriculture sector's own records and
the existing LLM client. It does not import or modify any other sector,
shared pipeline, or global configuration.

Internal validation verdicts (PASS/FAIL) produced here are consumed
exclusively by backend selection logic. They must never be copied into the
user-facing answer. Use :func:`scan_forbidden` in tests to enforce that.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# User-facing text must never match any of these (case-insensitive).
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    ("pass_fail", r"\bPASS\b|\bFAIL\b"),
    ("verdict", r"\bverdict\b"),
    ("decision_reject", r"\bdecision\b.{0,20}\breject\b"),
    ("validation_failed", r"\bvalidation\b.{0,20}\b(failed|failure)\b"),
    ("data_inadequate", r"\bdata\b.{0,20}\binadequate\b"),
    ("insufficient", r"\binsufficient\b"),
    ("data_unavailable", r"\bdata\b.{0,20}\bunavailable\b"),
    ("no_validated_observation", r"\bno\b.{0,30}\bvalidated\b.{0,30}\bobservation\b"),
    ("not_verified", r"\bnot\b.{0,20}\bverified\b"),
    ("not_extracted", r"\bnot\b.{0,20}\bextracted\b"),
    ("data_status", r"\bdata status\b"),
    ("availability_note", r"\bavailability note\b"),
    ("search_limitation", r"\bsearch limitation\b"),
    ("tavily_searched", r"\btavily was searched\b"),
    ("search_not_completed", r"\bcould not be completed\b"),
    ("no_verified_mapping", r"\bno verified\b"),
    ("mcp_failed", r"\bmcp server failed\b"),
    ("tool_error", r"\btool returned an error\b"),
    ("retry_log", r"\bretry\b"),
    ("ranking_decision", r"\bsource.?ranking\b"),
    ("out_of_scope", r"\bout of scope\b"),
    ("confidence_score", r"\bconfidence\b.{0,20}\b(score|assessment)\b"),
)


def scan_forbidden(text: str) -> list[str]:
    """Return the names of forbidden internal-verdict patterns found in text."""
    hits = []
    for name, pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text or "", re.IGNORECASE):
            hits.append(name)
    return hits


def sanitize_user_text(text: str) -> str:
    """Backend guard: drop any residual internal-diagnostic lines from user text."""
    line_patterns = (
        r"availability note\s*:",
        r"data status\s*:",
        r"search limitation\s*:",
        r"tavily was searched",
        r"could not be completed",
        r"no verified .* mapping",
        r"mcp server failed",
        r"tool returned an error",
        r"^\s*(PASS|FAIL|Verdict\s*:|Decision\s*:)",
    )
    kept = []
    for line in (text or "").splitlines():
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in line_patterns):
            continue
        kept.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


@dataclass
class PrimaryObservation:
    """The single evidence-backed observation selected for the user."""

    value_text: str
    unit: str
    crop: str
    indicator: str
    geography: str
    period: str
    source_name: str
    source_url: str
    estimate_status: str | None = None
    published_date: str | None = None
    is_fallback: bool = False
    fallback_note: str = ""
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "value": self.value_text,
            "unit": self.unit,
            "crop": self.crop,
            "indicator": self.indicator,
            "geography": self.geography,
            "period": self.period,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "estimate_status": self.estimate_status,
            "is_fallback": self.is_fallback,
            "fallback_note": self.fallback_note,
        }


def _safe_float(text: Any) -> float | None:
    try:
        return float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _display_value(raw: Any) -> tuple[float | None, str]:
    numeric = _safe_float(raw)
    if numeric is None:
        return None, str(raw or "")
    return numeric, f"{numeric:g}"


def _is_official_source(url: str) -> bool:
    lowered = (url or "").casefold()
    return any(host in lowered for host in (
        "pib.gov.in", "agricoop.nic.in", "desagri.gov.in", "data.gov.in",
        "mospi.gov.in", ".gov.in", ".nic.in"))


_METRIC_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("production", ("production", "output", "crop output")),
    ("yield", ("yield", "productivity")),
    ("area", ("area", "acreage", "sowing", "cultivated area")),
    ("price", ("price", "mandi", "msp", "rate", "wholesale", "modal price")),
)


def metric_family_of(text: str) -> str:
    """Map an indicator/crop-query word to a strict metric family, else 'other'."""
    lowered = (text or "").casefold()
    for family, words in _METRIC_FAMILIES:
        if any(word in lowered for word in words):
            return family
    return "other"


def metric_mismatch(requested_indicator: str, candidate_indicator: str) -> bool:
    """True only when both sides are known strict metrics and they differ.

    Production, yield, area, and price are never interchangeable. Anything
    unrecognized (weather metrics, MSP phrasing already maps to price) is
    left to the other validation checks instead of being rejected here.
    """
    wanted = metric_family_of(requested_indicator)
    got = metric_family_of(candidate_indicator)
    return wanted in {"production", "yield", "area", "price"} \
        and got in {"production", "yield", "area", "price"} and wanted != got


def deterministic_audit(query_dims: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Backend checks; returns failure reasons (empty means the checks pass)."""
    failures: list[str] = []
    requested_indicator = str(query_dims.get("indicator") or "production").casefold()
    cand_indicator = str(candidate.get("indicator") or "").casefold()
    if metric_mismatch(requested_indicator, cand_indicator):
        # Yield is not production, area is not production, price is not
        # production: never substitute one metric for another.
        failures.append("metric_mismatch")
        return failures
    if "production" in requested_indicator and any(
            word in cand_indicator for word in ("area", "yield", "price", "arrival")):
        failures.append("indicator_mismatch")
    requested_geo = str(query_dims.get("geography") or "").casefold()
    cand_geo = str(candidate.get("geography") or "").casefold()
    if requested_geo and requested_geo not in ("india", ""):
        if not cand_geo or "india-wide" in cand_geo or "broader" in cand_geo:
            failures.append("geography_mismatch")
        elif requested_geo not in cand_geo and cand_geo not in requested_geo:
            failures.append("geography_mismatch")
    requested_period = str(query_dims.get("period") or "")
    cand_period = str(candidate.get("period") or "")
    if requested_period and cand_period and not candidate.get("allow_period_fallback"):
        if not (cand_period == requested_period or cand_period.startswith(requested_period)):
            failures.append("period_mismatch")
    unit = str(candidate.get("unit") or "").strip()
    if not unit or unit.casefold() in {"unit", "value", "number", "n/a", "na", "-"}:
        failures.append("unit_missing")
    # Rule 5: an unresolved quantity discrepancy must not be presented as
    # verified.
    if candidate.get("verified") is False:
        failures.append("unverified_quantity")
    if candidate.get("value_num") is None:
        failures.append("value_missing")
    if not candidate.get("source_url"):
        failures.append("provenance_missing")
    return failures


async def audit_candidate_llm(query: str, query_dims: dict[str, Any],
                              candidate: dict[str, Any],
                              conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal LLM audit. Returns a verdict dict for backend use only."""
    try:
        from core.orchestrator.llm_client import llm_client
    except Exception as exc:  # noqa: BLE001
        return {"verdict": "ABSTAIN", "reasons": [f"llm_unavailable:{type(exc).__name__}"]}
    if not llm_client._get_api_key():
        return {"verdict": "ABSTAIN", "reasons": ["llm_unavailable:no_key"]}
    system_prompt = (
        "You are an internal agriculture data auditor. Assess whether the candidate "
        "observation answers the user's question based ONLY on the supplied evidence. "
        "Reply with a single JSON object: "
        '{"verdict": "PASS" or "FAIL", "reasons": ["short reason codes"], '
        '"needs_retry": true or false}. '
        "Check: 1 indicator relevance, 2 crop and geography match, 3 period and "
        "season match, 4 numeric extraction accuracy, 5 unit consistency, 6 source "
        "credibility and provenance, 7 conversion correctness, 8 estimate or "
        "revision status, 9 conflicting observations, 10 whether further retrieval "
        "is needed. Never invent values, units, or sources. Output JSON only."
    )
    payload = {
        "question": query[:500],
        "parsed_requirement": query_dims,
        "candidate": {k: candidate.get(k) for k in (
            "value_text", "unit", "indicator", "crop", "geography", "period",
            "season", "source_name", "source_url", "estimate_status",
            "published_date", "excerpt")},
        "conflicts": conflicts[:4],
    }
    try:
        raw = await llm_client.complete(
            "Audit this candidate:\n" + json.dumps(payload, default=str)[:8000],
            system_prompt,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Agriculture LLM audit failed: %s", type(exc).__name__)
        return {"verdict": "ABSTAIN", "reasons": ["llm_error"]}
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        verdict = json.loads(match.group(0) if match else raw)
        label = str(verdict.get("verdict", "")).upper()
        if label not in {"PASS", "FAIL"}:
            return {"verdict": "ABSTAIN", "reasons": ["unparseable_verdict"]}
        return {"verdict": label,
                "reasons": list(verdict.get("reasons") or []),
                "needs_retry": bool(verdict.get("needs_retry", label == "FAIL"))}
    except (ValueError, AttributeError):
        return {"verdict": "ABSTAIN", "reasons": ["unparseable_verdict"]}


def build_candidates(query_dims: dict[str, Any], structured: list[dict[str, Any]],
                     published: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order candidates: exact geo+period, latest same geo, same period closest geo, fallback."""
    requested_geo = str(query_dims.get("geography") or "").casefold()
    requested_period = str(query_dims.get("period") or "")
    candidates: list[dict[str, Any]] = []
    for record in structured:
        geo = str(record.get("geography") or "")
        period = str(record.get("period") or "")
        geo_exact = bool(requested_geo) and requested_geo in geo.casefold()
        period_exact = bool(requested_period) and (
            period == requested_period or period.startswith(requested_period))
        rank = 0 if (geo_exact and period_exact) else 1 if geo_exact else 2 if period_exact else 3
        numeric, display = _display_value(record.get("value"))
        candidates.append({
            "kind": "structured",
            "value_num": numeric,
            "value_text": display,
            "unit": str(record.get("unit") or ""),
            "indicator": str(record.get("indicator") or "Crop production"),
            "crop": str(record.get("crop") or query_dims.get("crop") or ""),
            "geography": geo or requested_geo,
            "period": period,
            "season": str(record.get("season") or ""),
            "source_name": str(record.get("source_name") or ""),
            "source_url": str(record.get("source_url") or ""),
            "estimate_status": record.get("estimate_status") or record.get("estimate_type"),
            "published_date": record.get("published_date"),
            "scope_match": bool(record.get("scope_match", True)),
            "verified": record.get("verified", True),
            "reporting_period": record.get("reporting_period") or period,
            "original_unit": record.get("original_unit") or str(record.get("unit") or ""),
            "allow_period_fallback": rank == 1,
            "rank": rank,
        })
    for row in published:
        geo = str(row.get("geography") or "")
        period = str(row.get("year") or "")
        scope_match = bool(row.get("scope_match"))
        period_exact = bool(requested_period) and (
            period == requested_period or period.startswith(requested_period))
        if scope_match and period_exact:
            rank = 0
        elif scope_match:
            rank = 1
        elif period_exact:
            rank = 2
        else:
            rank = 3
        candidates.append({
            "kind": "published",
            "value_num": _display_value(row.get("value"))[0],
            "value_text": _display_value(row.get("value"))[1],
            "unit": str(row.get("unit") or ""),
            "indicator": str(row.get("indicator") or "Crop production"),
            "crop": str(query_dims.get("crop") or ""),
            "geography": geo,
            "period": period,
            "season": str(row.get("season") or ""),
            "source_name": str(row.get("title") or ""),
            "source_url": str(row.get("url") or ""),
            "estimate_status": row.get("estimate_type"),
            "published_date": str(row.get("published_date") or "")[:10] or None,
            "excerpt": str(row.get("excerpt") or "")[:600],
            "scope_match": scope_match,
            "verified": row.get("verified", True),
            "reporting_period": row.get("reporting_period") or period,
            "original_unit": row.get("original_unit") or str(row.get("unit") or ""),
            "allow_period_fallback": scope_match,
            "rank": rank,
        })
    # Deduplicate identical underlying estimates (same value, unit, period,
    # geography, and indicator) even when repeated under different URLs.
    # The first kept entry wins, with official sources preferred.
    requested_metric = str(query_dims.get("indicator") or "")
    candidates = [candidate for candidate in candidates
                  if not metric_mismatch(requested_metric, str(candidate.get("indicator") or ""))]
    seen: set[tuple] = set()
    unique: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda c: (
            c["rank"], not _is_official_source(c["source_url"]), c["period"])):
        # Rule 3: estimate rounds stay distinct; identical values with
        # different estimate labels are not deduplicated away.
        key = (candidate["value_text"], candidate["unit"].casefold(),
               candidate["period"], candidate["geography"].casefold(),
               candidate["indicator"].casefold(),
               str(candidate.get("estimate_status") or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    unique.sort(key=lambda c: (c["rank"], c["period"]), reverse=False)
    # Within the same rank prefer the newest period.
    ordered: list[dict[str, Any]] = []
    for rank in (0, 1, 2, 3):
        group = sorted((c for c in unique if c["rank"] == rank),
                       key=lambda c: c["period"], reverse=True)
        ordered.extend(group)
    return ordered


async def select_primary(query: str, query_dims: dict[str, Any],
                         structured: list[dict[str, Any]],
                         published: list[dict[str, Any]],
                         max_audits: int = 3) -> tuple[PrimaryObservation | None, list[dict[str, Any]]]:
    """Validate candidates and return exactly one primary observation (or None).

    Internal audit trail is returned alongside for backend logic only.
    """
    candidates = build_candidates(query_dims, structured, published)
    # "Latest" wins no matter what: audit the newest valid reporting period
    # first so a stale older row can never shadow a newer observation.
    try:
        from .validation import is_latest_query as _is_latest_q
    except Exception:  # noqa: BLE001
        _is_latest_q = lambda q: False  # type: ignore
    if _is_latest_q(query):
        candidates = sorted(
            candidates,
            key=lambda c: (str(c.get("period") or ""),
                           -int(c.get("rank", 3)),
                           c.get("published_date") or ""),
            reverse=True,
        )
    trail: list[dict[str, Any]] = []
    fallback: dict[str, Any] | None = None
    audits = 0
    for candidate in candidates:
        deterministic = deterministic_audit(query_dims, candidate)
        verdict: dict[str, Any] | None = None
        if not deterministic and audits < max_audits:
            audits += 1
            conflicts = [c for c in candidates if c is not candidate
                         and c.get("period") == candidate.get("period")][:4]
            verdict = await audit_candidate_llm(query, query_dims, candidate, conflicts)
        trail.append({"candidate": {k: candidate.get(k) for k in (
            "kind", "value_text", "unit", "geography", "period", "source_url")},
            "deterministic": deterministic,
            "llm": verdict})
        if deterministic:
            continue
        if verdict is None or verdict.get("verdict") in {"PASS", "ABSTAIN"}:
            return _to_primary(query_dims, candidate, trail), trail
        # FAIL: keep the strongest deterministic-passing candidate as fallback.
        if fallback is None:
            fallback = candidate
    if fallback is not None:
        return _to_primary(query_dims, fallback, trail), trail
    # Last resort: strongest candidate that at least has a number, unit, and source.
    for candidate in candidates:
        if (candidate.get("value_num") is not None and candidate.get("unit")
                and candidate.get("source_url")):
            return _to_primary(query_dims, candidate, trail), trail
    return None, trail


def _to_primary(query_dims: dict[str, Any], candidate: dict[str, Any],
                trail: list[dict[str, Any]]) -> PrimaryObservation:
    requested_period = str(query_dims.get("period") or "")
    requested_geo = str(query_dims.get("geography") or "").casefold()
    period_matches = not requested_period or candidate["period"] == requested_period \
        or candidate["period"].startswith(requested_period)
    geo_matches = not requested_geo or requested_geo in candidate["geography"].casefold()
    is_fallback = not (period_matches and geo_matches)
    note = ""
    if is_fallback:
        bits = []
        if not period_matches and requested_period:
            bits.append(f"reported for {candidate['period']} rather than {requested_period}")
        if not geo_matches and requested_geo:
            bits.append(f"covers {candidate['geography']}")
        note = "; ".join(bits)
    return PrimaryObservation(
        value_text=candidate["value_text"],
        unit=candidate["unit"],
        crop=candidate["crop"] or str(query_dims.get("crop") or ""),
        indicator=candidate["indicator"],
        geography=candidate["geography"] or requested_geo,
        period=candidate["period"],
        source_name=candidate["source_name"],
        source_url=candidate["source_url"],
        estimate_status=candidate.get("estimate_status"),
        published_date=candidate.get("published_date"),
        is_fallback=is_fallback,
        fallback_note=note,
        audit_trail=[dict(entry) for entry in trail],
    )


def display_geography(primary: PrimaryObservation) -> str:
    """User-facing scope label; national figures are named as national."""
    geo = primary.geography or ""
    if "india-wide" in geo.casefold() or "broader source context" in geo.casefold():
        return "India (national-level)"
    return geo


def render_answer_card(query_dims: dict[str, Any],
                       primary: PrimaryObservation | None) -> str:
    """Direct single-observation answer card. Deterministic, no verdicts.

    Only the requested metric, crop, actual scope, true period, value, and
    source link appear, plus one short note for estimate status or fallback.
    """
    if primary is None:
        crop = str(query_dims.get("crop") or "crop")
        metric = str(query_dims.get("indicator") or "observation")
        geo = str(query_dims.get("geography") or "the requested area")
        period = str(query_dims.get("period") or "")
        when = f" for {period}" if period else ""
        return (f"I couldn't find a verified {crop} {metric} figure for {geo}{when} "
                "in the sources I checked, so I'm not guessing a number.")
    indicator = primary.indicator
    if indicator.casefold() == "crop production":
        metric = f"{primary.crop} production" if primary.crop else "Crop production"
    elif primary.crop and primary.crop.casefold() not in indicator.casefold():
        metric = f"{primary.crop} {indicator}"
    else:
        metric = indicator or "production"
    source = (f"[{primary.source_name}]({primary.source_url})"
              if primary.source_url else primary.source_name)
    try:
        from .validation import display_with_equivalent as _with_equiv
    except Exception:  # noqa: BLE001
        _with_equiv = lambda v, u: f"{v} {u}".strip()  # type: ignore
    # Keep "**<value> <unit>**" verbatim so scale can never be misread,
    # with the converted equivalent in plain text after it.
    _equiv_text = _with_equiv(primary.value_text, primary.unit)
    _suffix = _equiv_text[len(f"{primary.value_text} {primary.unit}".strip()):]
    value_display = f"**{primary.value_text} {primary.unit}**{_suffix}"
    lines = [
        f"**Metric:** {metric} — {value_display}",
        f"**Crop/commodity:** {primary.crop or metric}",
        f"**Geography:** {display_geography(primary)}",
        f"**Reporting period:** {primary.period}",
        f"**Source:** {source}",
    ]
    notes: list[str] = []
    if primary.estimate_status and "final" not in primary.estimate_status.casefold():
        notes.append(f"Reported as {primary.estimate_status}.")
    if primary.is_fallback and primary.fallback_note:
        notes.append(f"Note: this figure {primary.fallback_note}.")
    if notes:
        lines.append("")
        lines.extend(notes)
    return "\n".join(lines)


def template_answer(query_dims: dict[str, Any], primary: PrimaryObservation) -> str:
    """Deterministic user-facing answer used when the LLM is unavailable."""
    indicator = primary.indicator
    if indicator.casefold() == "crop production":
        what = f"{primary.crop} production" if primary.crop else "Crop production"
    elif primary.crop and primary.crop.casefold() not in indicator.casefold():
        what = f"{primary.crop} {indicator}"
    else:
        what = indicator or "production"
    try:
        from .validation import display_with_equivalent as _with_equiv2
    except Exception:  # noqa: BLE001
        _with_equiv2 = lambda v, u: f"{v} {u}".strip()  # type: ignore
    _equiv2 = _with_equiv2(primary.value_text, primary.unit)
    _suffix2 = _equiv2[len(f"{primary.value_text} {primary.unit}".strip()):]
    value = f"**{primary.value_text} {primary.unit}**{_suffix2}"
    source = f"[{primary.source_name}]({primary.source_url})" if primary.source_url else primary.source_name
    estimate = (f" (reported as {primary.estimate_status})"
                if primary.estimate_status and "final" not in primary.estimate_status.casefold() else "")
    if not primary.is_fallback:
        lead = f"{what} in {primary.geography} was {value} for **{primary.period}**{estimate}, according to {source}."
        return f"{lead[:1].upper()}{lead[1:]}"
    fallback = (f"The latest verified figure retrieved for {what} is {value}, "
                f"reported for **{primary.period}**{estimate} by {source}.")
    if primary.fallback_note:
        fallback += f" Note: this figure {primary.fallback_note}."
    elif primary.geography:
        fallback += f" It covers {primary.geography}."
    return fallback


async def render_final_answer(query: str, query_dims: dict[str, Any],
                              primary: PrimaryObservation | None) -> str:
    """Generate the single user-facing answer; never exposes internal verdicts."""
    if primary is None:
        short = query.strip()[:160]
        return (f"I couldn't find a verified figure for {short} in the sources I checked, "
                "so I'm not guessing a number.")
    try:
        from core.orchestrator.llm_client import llm_client
    except Exception:  # noqa: BLE001
        return template_answer(query_dims, primary)
    if not llm_client._get_api_key():
        return template_answer(query_dims, primary)
    system_prompt = (
        "Write one direct answer sentence for the user's agriculture question using ONLY "
        "the supplied observation. Include the single value with its unit, the actual "
        "reporting period, the crop or indicator, the geographic scope, and the source "
        "as a Markdown link with the exact URL given. If the observation is a fallback "
        "(is_fallback true), briefly note its actual period or scope in plain words. "
        "Mention estimate status only if given. Plain natural English, no tables, no "
        "bullet lists. Never mention validation, verdicts, confidence, retrieval, "
        "missing data, or other candidates. Never invent numbers, units, periods, or links."
    )
    try:
        draft = await llm_client.complete(
            "Question: " + query[:500] + "\nObservation:\n"
            + json.dumps(primary.to_public_dict(), default=str),
            system_prompt,
        )
    except Exception:  # noqa: BLE001
        return template_answer(query_dims, primary)
    draft = (draft or "").strip()
    if not draft or draft == llm_client._unavailable_notice():
        return template_answer(query_dims, primary)
    if scan_forbidden(draft):
        return template_answer(query_dims, primary)
    if primary.value_text not in draft or primary.period not in draft:
        return template_answer(query_dims, primary)
    # Unit must survive verbatim: an LLM rewrite of "102.97 lakh tonnes"
    # as "102.97 million tonnes" is a 10x fabrication — reject it.
    if primary.unit and primary.unit.casefold() not in draft.casefold():
        return template_answer(query_dims, primary)
    if primary.source_url and primary.source_url not in draft:
        return template_answer(query_dims, primary)
    return draft


def refined_query(query: str, query_dims: dict[str, Any]) -> str:
    """Build one targeted follow-up query (bounded retry, not an identical repeat)."""
    bits = [query_dims.get("crop") or "", query_dims.get("geography") or "",
            query_dims.get("period") or "", "production official estimate"]
    return f"{query} {' '.join(b for b in bits if b)}"[:240]


_EXCERPT_QUANTITY = re.compile(
    r"(?<![\w.])([\d,]+(?:\.\d+)?)\s*(million(?:\s+metric)?\s+tonnes?|"
    r"lakh(?:\s+metric)?\s+tonnes?|thousand\s+tonnes?|crore\s+tonnes?|"
    r"million\s+bales?|lakh\s+bales?|thousand\s+bales?|"
    r"lmt|mmt|mt|tonnes?|tons?|bales?)\b",
    re.IGNORECASE,
)

_EXCERPT_OFFICIAL_HOSTS = (
    "pib.gov.in", "agricoop.nic.in", "desagri.gov.in", "data.gov.in",
    "mospi.gov.in", ".gov.in", ".nic.in",
)


def extract_excerpt_figure(excerpt: str) -> tuple[str, str] | None:
    """Extract the first production-quantity figure from a source excerpt."""
    match = _EXCERPT_QUANTITY.search(excerpt or "")
    if not match:
        return None
    unit = re.sub(r"\s+", " ", match.group(2)).strip()
    return match.group(1), unit


def score_excerpt(query_dims: dict[str, Any], item: dict[str, Any]) -> tuple[float, bool, bool]:
    """Rank one Tavily excerpt. Returns (score, has_number, geo_match).

    Prefers excerpts that name the requested place, match the requested
    period, carry an actual numeric figure, and come from official domains.
    Generic blurbs without numbers score lowest and are never picked.
    """
    excerpt = str(item.get("relevant_excerpt") or item.get("excerpt") or "")
    lowered = excerpt.casefold()
    title_url = f"{item.get('title') or ''} {item.get('url') or ''}".casefold()
    requested_geo = str(query_dims.get("geography") or "").casefold()
    requested_period = str(query_dims.get("period") or "")
    score = 0.0
    geo_match = bool(requested_geo) and (
        requested_geo in lowered or requested_geo in title_url)
    if geo_match:
        score += 3.0
    elif re.search(r"\bindia\b|national|all-india", lowered):
        score += 0.5
    year = str(item.get("relevant_year") or "")
    if requested_period and (year == requested_period or year.startswith(requested_period)):
        score += 2.0
    figure = extract_excerpt_figure(excerpt)
    has_number = figure is not None
    if has_number:
        score += 3.0
    else:
        score -= 2.0
    if any(host in (item.get("url") or "").casefold() for host in _EXCERPT_OFFICIAL_HOSTS):
        score += 1.0
    if re.search(r"\b(advance|final|provisional|revised)\s+(estimate|estimates)\b", lowered):
        score += 0.5
    return score, has_number, geo_match


_EXCERPT_PERIOD = re.compile(
    r"\b((?:19|20)\d{2}(?:[-/](?:\d{2}|20\d{2}))?)\b")


def excerpt_full_period(excerpt: str, relevant_year: str) -> str:
    """Recover the full reporting period (e.g. 2024-25, not just 2024).

    Calendar years, financial years, and agricultural seasons are never
    treated as equivalent: the exact token from the source is preserved.
    """
    tokens = [match.group(1) for match in _EXCERPT_PERIOD.finditer(excerpt or "")]
    for token in tokens:
        if relevant_year and token.startswith(relevant_year):
            return token
    return tokens[0] if tokens else (relevant_year or "")


def excerpt_to_published_row(query_dims: dict[str, Any],
                             item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert the best excerpt into a candidate row. None when no figure exists."""
    figure = extract_excerpt_figure(str(item.get("relevant_excerpt") or ""))
    if figure is None:
        return None
    value, unit = figure
    _score, _has_number, geo_match = score_excerpt(query_dims, item)
    requested_geo = str(query_dims.get("geography") or "")
    combined = f"{item.get('relevant_excerpt') or ''} {item.get('title') or ''}".casefold()
    if geo_match:
        geography = requested_geo
    elif re.search(r"\bindia\b|national|all-india", combined):
        geography = "India-wide context; not specific to the requested area"
    else:
        geography = "Broader source context; not specific to the requested area"
    year = excerpt_full_period(str(item.get("relevant_excerpt") or ""),
                               str(item.get("relevant_year") or ""))
    return {
        "title": item.get("title") or item.get("url") or "Source",
        "url": item.get("url") or "",
        "published_date": item.get("published_date") or "",
        "year": year,
        "indicator": "Crop production",
        "year_start": year[:4],
        "value": value, "unit": unit,
        "excerpt": str(item.get("relevant_excerpt") or "")[:600],
        "district": "Not stated", "season": "Not stated",
        "geography": geography, "scope_match": geo_match,
        "label": "Published source claim",
    }


async def pick_best_excerpt(query: str, query_dims: dict[str, Any],
                            excerpts: list[dict[str, Any]]
                            ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Reason over candidate excerpts and return the single best one.

    Deterministic scoring shortlists; the LLM makes the final pick. The
    returned trail is internal backend data, never user-facing text.
    """
    trail: list[dict[str, Any]] = []
    if not excerpts:
        return None, trail
    ranked = sorted(excerpts,
                    key=lambda item: score_excerpt(query_dims, item)[0],
                    reverse=True)
    shortlist = ranked[:3]
    trail.append({"shortlist": [
        {"title": item.get("title"), "url": item.get("url"),
         "score": score_excerpt(query_dims, item)[0]} for item in shortlist]})
    try:
        from core.orchestrator.llm_client import llm_client
    except Exception as exc:  # noqa: BLE001
        trail.append({"llm_pick": f"ABSTAIN:llm_unavailable:{type(exc).__name__}"})
        return shortlist[0], trail
    if not llm_client._get_api_key():
        trail.append({"llm_pick": "ABSTAIN:no_key"})
        return shortlist[0], trail
    system_prompt = (
        "You are an internal agriculture evidence router. Exactly one Tavily excerpt "
        "will be shown to answer the user's question. Reply with a single JSON object "
        '{"pick": N, "reason": "short reason code"} where N is the 0-based index of '
        "the excerpt that best answers the question. Prefer excerpts that match the "
        "requested crop, indicator, geographic scope, and reporting period, carry an "
        "actual numeric figure from a credible official source, and state estimate or "
        "revision status. Reject generic blurbs without numbers and wrong-geography "
        "figures. Output JSON only."
    )
    listing = [{"index": index,
                "title": item.get("title"), "url": item.get("url"),
                "year": item.get("relevant_year"),
                "excerpt": item.get("relevant_excerpt")}
               for index, item in enumerate(shortlist)]
    try:
        raw = await llm_client.complete(
            "Question: " + query[:500] + "\nParsed requirement:\n"
            + json.dumps(query_dims, default=str)
            + "\nCandidate excerpts:\n" + json.dumps(listing, default=str)[:8000],
            system_prompt,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Agriculture excerpt pick failed: %s", type(exc).__name__)
        trail.append({"llm_pick": "ABSTAIN:llm_error"})
        return shortlist[0], trail
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        verdict = json.loads(match.group(0) if match else raw)
        index = int(verdict.get("pick", 0))
        if not 0 <= index < len(shortlist):
            raise ValueError("pick out of range")
        trail.append({"llm_pick": index, "reason": str(verdict.get("reason") or "")})
        return shortlist[index], trail
    except (ValueError, AttributeError, TypeError):
        trail.append({"llm_pick": "ABSTAIN:unparseable"})
        return shortlist[0], trail
