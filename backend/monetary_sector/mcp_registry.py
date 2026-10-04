"""Prompt-driven MCP registry for the Monetary Sector.

Single place that answers, for any user prompt, which functions are necessary —
and nothing more:

* ``MONETARY_TOOLS`` — the sector's dataset tools with routing triggers and
  dependencies (``monetary_stance`` derives from ``policy_rates``).
* ``UPSTREAM_MCP_SERVERS`` — the external MCP servers this sector pulls, with
  launch commands and wiring verdicts.
* Intent predicates — cache-clear, force-live, and MPC-news intents detected
  from prompt keywords.
* ``match_services`` / ``expand_dependencies`` — deterministic prompt routing
  used by the agent before any LLM router call.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.sector_reasoning import select_relevant_services

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPToolSpec:
    """One retrievable monetary function: what it is and when to retrieve it."""

    name: str
    title: str
    description: str
    triggers: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()


MONETARY_TOOLS: dict[str, MCPToolSpec] = {
    "policy_rates": MCPToolSpec(
        name="policy_rates",
        title="RBI Policy Rates & Reserve Requirements",
        description="Repo, reverse repo, SDF, MSF, bank rate, CRR, SLR, corridor width.",
        triggers=(
            "repo", "sdf", "msf", "bank rate", "reverse repo", "crr", "slr",
            "policy rate", "rate corridor",
        ),
    ),
    "money_supply": MCPToolSpec(
        name="money_supply",
        title="Money Supply Aggregates",
        description="M0/M1/M2/M3 stocks and M3 YoY growth.",
        triggers=(
            "money supply", "money stock", "m0", "m1", "m2", "m3",
            "currency in circulation",
        ),
    ),
    "system_liquidity": MCPToolSpec(
        name="system_liquidity",
        title="System Liquidity Operations",
        description="Reported LAF operation components and liquidity condition.",
        triggers=(
            "liquidity", "laf", "absorption", "injection",
            "liquidity operations", "wacr",
        ),
    ),
    "monetary_stance": MCPToolSpec(
        name="monetary_stance",
        title="MPC Stance Snapshot",
        description="MPC stance label derived from the fetched policy rates.",
        triggers=(
            "monetary stance", "mpc stance", "policy stance", "real policy rate",
            "restrictive", "accommodative", "neutral stance",
        ),
        depends_on=("policy_rates",),
    ),
}

DEPENDENCIES: dict[str, tuple[str, ...]] = {
    name: spec.depends_on for name, spec in MONETARY_TOOLS.items() if spec.depends_on
}

# ---------------------------------------------------------------------------
# Upstream MCP servers this sector pulls (launch + wiring verdicts)
# ---------------------------------------------------------------------------

UPSTREAM_MCP_SERVERS: dict[str, dict[str, Any]] = {
    "eco-policy": {
        "command": ("uvx", "eco-policy-mcp"),
        "tools": ("rbi_get_policy_rates",),
        "wired": True,
        "role": "Primary live policy rates + stance label.",
    },
    "dbie": {
        "command": ("https", "dbie.rbihub.in/data"),
        "tools": ("select-economic-indicators.json", "money-stock-measures.json",
                  "liquidity-operations.json"),
        "wired": True,
        "role": "Official RBIH tables pulled by direct CDN HTTP (finance-sector "
        "pattern: plain httpx, no subprocess). Same upstream data as the DBIE "
        "MCP tables; the stdio bridge is no longer used.",
    },
    "tavily-direct": {
        "command": ("https", "api.tavily.com/search"),
        "tools": ("tavily_search",),
        "wired": True,
        "role": "Gated real-time MPC news via direct HTTPS (finance-sector "
        "pattern: no subprocess). The npx mcp-remote bridge is retired.",
    },
    "finstack": {
        "command": ("uvx", "--with", "mcp<2", "finstack-mcp"),
        "tools": ("rbi_policy_rates", "india_macro_indicators", "india_gsec_yields"),
        "wired": False,
        "role": "NOT wired: serves stale Feb-2025 rates and indicative Q1-2025 yields; "
        "needs the mcp<2 pin (plain launch crashes on the mcp 2.x SDK).",
    },
}

# ---------------------------------------------------------------------------
# Prompt intents
# ---------------------------------------------------------------------------

NEWS_TRIGGERS: tuple[str, ...] = (
    "news", "latest", "recent", "mpc meeting", "mpc decision", "announcement",
    "governor", "speech", "press release", "minutes",
)

FORCE_LIVE_TRIGGERS: tuple[str, ...] = (
    "live", "real-time", "real time", "realtime", "up to date", "up-to-date", "fresh",
)

CACHE_CLEAR_TRIGGERS: tuple[str, ...] = (
    "clear cache", "clear the cache", "reset cache", "empty cache",
    "delete cache", "wipe cache",
)


def _mentions(query: str, triggers: tuple[str, ...]) -> bool:
    lowered = query.casefold()
    return any(trigger in lowered for trigger in triggers)


def wants_cache_clear(query: str) -> bool:
    """Detect an explicit cache-clear request (e.g. 'clear the cache')."""
    return _mentions(query, CACHE_CLEAR_TRIGGERS)


def wants_force_live(query: str) -> bool:
    """Detect an explicit live-data request (e.g. 'fetch live rates').

    Forced queries bypass the DuckDB cache entirely: live MCP failure raises
    instead of silently serving cached rows.
    """
    return _mentions(query, FORCE_LIVE_TRIGGERS)


def wants_news(query: str, selected: set[str]) -> bool:
    """Fetch Tavily MPC news only for stance questions or recency-seeking queries.

    Keeps ordinary data queries fast by skipping the remote-search round trip.
    """
    if "monetary_stance" in selected:
        return True
    return _mentions(query, NEWS_TRIGGERS)


def match_services(query: str) -> set[str]:
    """Deterministically match a prompt to registry tools via triggers."""
    return select_relevant_services(
        query, {name: spec.triggers for name, spec in MONETARY_TOOLS.items()}
    )


def expand_dependencies(selected: set[str]) -> set[str]:
    """Add the tools that selected tools derive from (e.g. stance needs rates)."""
    expanded = set(selected)
    for name in selected:
        expanded.update(DEPENDENCIES.get(name, ()))
    unknown = expanded - set(MONETARY_TOOLS)
    if unknown:
        logger.warning("Ignoring unknown monetary services: %s", sorted(unknown))
        expanded -= unknown
    return expanded
