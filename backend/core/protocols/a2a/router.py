"""Capability-based query routing driven entirely by registered Agent Cards."""
from __future__ import annotations

import json
import logging
import re
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

from core.config import settings

from .executor_adapter import SECTOR_ANALYSIS
from .models import AgentCard
from .registry import AgentRegistry

logger = logging.getLogger("macrograph.a2a")

_GENERIC_TERMS = frozenset({"macroeconomics", "macroeconomic", "macro"})
_MAX_AGENTS = 5
_MIN_DISTINCTIVE_SCORE = 0.75

LLMComplete = Callable[[str], Awaitable[str]]


class RouteChoice(BaseModel):
    agent_id: str
    task: str = SECTOR_ANALYSIS
    score: float = 0.0
    matched: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    method: str
    choices: list[RouteChoice]


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower())]


def _contains(haystack: list[str], needle: tuple[str, ...]) -> bool:
    n = len(needle)
    return n > 0 and any(tuple(haystack[i:i + n]) == needle for i in range(len(haystack) - n + 1))


def card_terms(card: AgentCard) -> dict[str, tuple[str, ...]]:
    """Routable phrases from capabilities, skill tags and metadata keywords (phrase -> tokens)."""
    raw = [*card.capabilities, *(t for s in card.skills for t in s.tags), *card.metadata.get("keywords", [])]
    terms: dict[str, tuple[str, ...]] = {}
    for phrase in raw:
        toks = tuple(_tokens(str(phrase).replace("_", " ")))
        if toks and not set(toks) <= _GENERIC_TERMS:
            terms[str(phrase)] = toks
    return terms


def lexical_route(query: str, registry: AgentRegistry) -> list[RouteChoice]:
    """Score agents by the terms their cards advertise.

    A term shared by several agents (e.g. "rbi") counts 1/n for each, so only an agent with
    distinctive evidence is selected. If nothing is distinctive, the best-scoring agents are used.
    """
    q_tokens = _tokens(query)
    cards = [c for c in registry.list_agents() if c.agent_id and SECTOR_ANALYSIS in c.supported_tasks]
    terms = {c.agent_id: card_terms(c) for c in cards}
    holders: dict[tuple[str, ...], int] = {}
    for agent_terms in terms.values():
        for toks in set(agent_terms.values()):
            holders[toks] = holders.get(toks, 0) + 1

    scored: list[RouteChoice] = []
    for agent_id, agent_terms in terms.items():
        matched = {p: t for p, t in agent_terms.items() if _contains(q_tokens, t)}
        if matched:
            score = sum(1.0 / holders[t] for t in set(matched.values()))
            scored.append(RouteChoice(agent_id=agent_id, score=round(score, 3), matched=sorted(matched)))
    scored.sort(key=lambda c: (-c.score, c.agent_id))
    chosen = [c for c in scored if c.score >= _MIN_DISTINCTIVE_SCORE]
    if not chosen and scored:
        chosen = [c for c in scored if c.score == scored[0].score]
    return chosen[:_MAX_AGENTS]


def _parse_agent_ids(text: str, valid: set[str]) -> list[str]:
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    ids = [x for x in data if isinstance(x, str) and x in valid]
    return list(dict.fromkeys(ids))[:_MAX_AGENTS]


async def llm_route(query: str, registry: AgentRegistry, complete: LLMComplete) -> list[RouteChoice]:
    """Ask the LLM to pick agents. Output is restricted to registered agent ids."""
    cards = [c for c in registry.list_agents() if c.agent_id and SECTOR_ANALYSIS in c.supported_tasks]
    catalogue = "\n".join(f"- {c.agent_id}: {c.description[:240]}" for c in cards)
    prompt = (
        "Select the sector agents needed to answer the macroeconomic question. "
        "Reply with only a JSON array of agent ids from the catalogue.\n\n"
        f"Catalogue:\n{catalogue}\n\nQuestion: {query[:500]}"
    )
    try:
        text = await complete(prompt)
    except Exception as exc:  # LLM outage must not break routing
        logger.warning("LLM routing unavailable: %s", exc)
        return []
    ids = _parse_agent_ids(text, {c.agent_id for c in cards if c.agent_id})
    return [RouteChoice(agent_id=i, matched=["llm"]) for i in ids]


async def route_query(
    query: str, registry: AgentRegistry, llm_complete: Optional[LLMComplete] = None
) -> RoutingDecision:
    """Lexical card routing first; LLM only when no card matches; configured defaults last."""
    choices = lexical_route(query, registry)
    if choices:
        return RoutingDecision(method="lexical", choices=choices)
    if llm_complete is not None and settings.A2A_LLM_ROUTING:
        choices = await llm_route(query, registry, llm_complete)
        if choices:
            return RoutingDecision(method="llm", choices=choices)
    defaults = [
        RouteChoice(agent_id=a, matched=["default"])
        for a in settings.A2A_DEFAULT_AGENTS
        if (card := registry.get_agent(a)) is not None and SECTOR_ANALYSIS in card.supported_tasks
    ]
    return RoutingDecision(method="default", choices=defaults)
