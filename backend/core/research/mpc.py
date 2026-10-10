"""Idea 4: simulated six-seat MPC. Archetype personas, deterministic rule baseline, optional LLM wording."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from .series_provider import get_series

logger = logging.getLogger(__name__)

CPI = "in.macro.prices.cpi_headline"
GDP = "in.macro.real.gdp_growth"
REPO = "in.macro.monetary.repo_rate"
VOTES = ("HIKE", "HOLD", "CUT")

SEATS = [
    ("Governor archetype", "centrist"), ("RBI deputy archetype", "hawk"), ("RBI officer archetype", "centrist"),
    ("External member 1", "hawk"), ("External member 2", "dove"), ("External member 3", "dove"),
]
_PERSONA_BRIEF = {
    "hawk": "You prioritise price stability and weigh inflation above growth.",
    "dove": "You prioritise growth and employment and tolerate inflation inside the target band.",
    "centrist": "You balance inflation and growth and move only when both signals agree.",
}


def build_evidence_pack() -> Dict[str, Dict[str, Any]]:
    pack: Dict[str, Dict[str, Any]] = {}
    try:
        from core.database.macro_store import macro_store

        for indicator_id in (CPI, REPO, GDP):
            df = macro_store.get_canonical_series(indicator_id)
            rows = [r for r in df.itertuples() if r.value is not None]
            if rows:
                last = rows[-1]
                pack[indicator_id] = {"id": indicator_id, "value": float(last.value), "period": str(last.date),
                                      "prior_value": float(rows[-2].value) if len(rows) > 1 else None,
                                      "freshness": str(last.data_status)}
    except Exception:  # noqa: BLE001
        logger.exception("macro_store evidence unavailable")
    for indicator_id in ("in.macro.external.usd_inr", "in.macro.monetary.bank_credit_growth"):
        series = get_series(indicator_id)
        if series:
            pack[indicator_id] = {"id": indicator_id, "value": series[-1][1], "period": series[-1][0],
                                  "prior_value": series[-2][1] if len(series) > 1 else None, "freshness": "cached"}
    return pack


def _rule_vote(persona: str, cpi: Optional[float], growth_weakening: bool) -> Dict[str, str]:
    if cpi is None:
        return {"vote": "HOLD", "reason": "No inflation reading available, so no basis to move."}
    if persona == "hawk":
        if cpi > 6:
            return {"vote": "HIKE", "reason": f"CPI {cpi:g}% is above the 6% upper band."}
        return {"vote": "HOLD", "reason": f"CPI {cpi:g}% is not below the 4% target midpoint; no room to cut."}
    if persona == "dove":
        if cpi < 2:
            return {"vote": "CUT", "reason": f"CPI {cpi:g}% is below the 2% lower band."}
        if growth_weakening and cpi <= 6:
            return {"vote": "CUT", "reason": f"GDP growth is decelerating and CPI {cpi:g}% is inside the band."}
        return {"vote": "HOLD", "reason": f"CPI {cpi:g}% is inside the band and growth is not weakening."}
    if cpi > 6:
        return {"vote": "HIKE", "reason": f"CPI {cpi:g}% is above the 6% upper band."}
    if cpi < 2:
        return {"vote": "CUT", "reason": f"CPI {cpi:g}% is below the 2% lower band."}
    if growth_weakening and cpi < 4:
        return {"vote": "CUT", "reason": f"Growth is decelerating and CPI {cpi:g}% is below the 4% target."}
    return {"vote": "HOLD", "reason": f"Inflation and growth signals do not agree on a move (CPI {cpi:g}%)."}


def _decide(seats: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    tally = {v: sum(1 for s in seats if s[key] == v) for v in VOTES}
    top = max(tally.values())
    winners = [v for v, c in tally.items() if c == top]
    decision = winners[0] if len(winners) == 1 else seats[0][key]  # Governor casting vote on a tie
    return {"tally": tally, "decision": decision, "dissent": round(1 - top / len(seats), 3)}


async def _llm_persona(persona: str, pack: Dict[str, Dict[str, Any]], sem: asyncio.Semaphore) -> Optional[Dict[str, str]]:
    from core.orchestrator.llm_client import llm_client

    lines = "\n".join(f"- {p['id']}: {p['value']} (period {p['period']}, prior {p['prior_value']}, {p['freshness']})"
                      for p in pack.values())
    prompt = (f"{_PERSONA_BRIEF[persona]}\nEvidence (use ONLY these numbers):\n{lines}\n"
              'Reply with JSON only: {"vote":"HIKE|HOLD|CUT","reason":"<=40 words quoting a number","cited_indicator":"<id from the list>"}')
    async with sem:
        text = await llm_client.complete(prompt, "You simulate an archetype monetary policy committee member.", False)
    if text == llm_client._unavailable_notice():
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if data.get("vote") not in VOTES or data.get("cited_indicator") not in pack or not data.get("reason"):
        return None
    return {"vote": data["vote"], "reason": str(data["reason"]), "cited_indicator": data["cited_indicator"]}


async def simulate_mpc(use_llm: bool = True) -> Dict[str, Any]:
    pack = await asyncio.to_thread(build_evidence_pack)
    cpi_row, gdp_row = pack.get(CPI), pack.get(GDP)
    cpi = cpi_row["value"] if cpi_row else None
    weakening = bool(gdp_row and gdp_row.get("prior_value") is not None and gdp_row["value"] < gdp_row["prior_value"])

    llm_results: Dict[str, Optional[Dict[str, str]]] = {}
    if use_llm and pack:
        from core.orchestrator.llm_client import llm_client

        if llm_client._get_api_key():
            sem = asyncio.Semaphore(2)
            personas = ["hawk", "dove", "centrist"]
            results = await asyncio.gather(*[_llm_persona(p, pack, sem) for p in personas], return_exceptions=True)
            llm_results = {p: (r if isinstance(r, dict) else None) for p, r in zip(personas, results)}

    seats: List[Dict[str, Any]] = []
    for seat, persona in SEATS:
        rule = _rule_vote(persona, cpi, weakening)
        llm = llm_results.get(persona)
        seats.append({
            "seat": seat, "persona": persona, "rule_vote": rule["vote"],
            "vote": llm["vote"] if llm else rule["vote"],
            "reason": llm["reason"] if llm else rule["reason"],
            "cited_indicator": llm["cited_indicator"] if llm else (CPI if CPI in pack else None),
            "source": "LLM" if llm else "RULE_BASED",
        })
    final = _decide(seats, "vote")
    baseline = _decide(seats, "rule_vote")
    return {"meeting_label": "SIMULATED", "evidence": list(pack.values()), "seats": seats,
            "tally": final["tally"], "decision": final["decision"], "dissent": final["dissent"],
            "rule_baseline": {"decision": baseline["decision"], "tally": baseline["tally"]},
            "agrees_with_rule_baseline": final["decision"] == baseline["decision"],
            "labels": {"data": "SIM", "llm_used": any(s["source"] == "LLM" for s in seats)}}
