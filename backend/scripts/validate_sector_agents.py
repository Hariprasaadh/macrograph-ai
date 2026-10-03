"""Smoke-test gateway schemas and direct chat for implemented sectors.

Run from the repository root with:
    uv run python backend\\scripts\\validate_sector_agents.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import main as gateway  # noqa: E402


SECTORS = {
    "external_sector": {
        "prefix": "/external-sector",
        "query": "Summarize latest available forex reserves and trade data.",
    },
    "labour_sector": {
        "prefix": "/labour-sector",
        "query": "What PLFS unemployment, LFPR, and WPR observations are available?",
    },
    "capital_market_sector": {
        "prefix": "/capital-markets",
        "query": "Summarize available NIFTY, India VIX, and G-Sec observations.",
    },
    "monetary_sector": {
        "prefix": "/monetary-sector",
        "query": "Summarize available RBI policy rates, money supply, and liquidity data.",
    },
}

DATABASES = {
    "external_sector": (
        "external_sector.database",
        {"forex_reserves", "trade_balance", "bop", "exchange_rates", "external_flows", "fetch_log"},
    ),
    "labour_sector": (
        "labour_sector.database",
        {"unemployment", "lfpr", "wpr", "labour_conditions", "fetch_log"},
    ),
    "capital_market_sector": (
        "capital_market_sector.database",
        {"nifty_snapshot", "market_history", "india_vix", "market_breadth", "gsec_yields", "fetch_log"},
    ),
    "monetary_sector": (
        "monetary_sector.database",
        {"policy_rates", "money_supply", "system_liquidity", "monetary_stance", "fetch_log"},
    ),
}


def check_schemas() -> None:
    from importlib import import_module

    for sector, (module_name, expected) in DATABASES.items():
        database = import_module(module_name)
        with database.get_connection() as connection:
            actual = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        missing = expected - actual
        if missing:
            raise RuntimeError(f"{sector} schema is missing tables: {sorted(missing)}")
        print(f"PASS schema {sector}: {len(expected)} tables initialized")


def _stream_events(response_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in response_text.splitlines():
        if line.startswith("data:"):
            events.append(json.loads(line.removeprefix("data:").strip()))
    return events


async def check_chat(mode: str, selected: set[str]) -> None:
    transport = httpx.ASGITransport(app=gateway.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=None,
    ) as client:
        for sector, config in SECTORS.items():
            if selected and sector not in selected:
                continue

            health = await client.get(f"{config['prefix']}/health")
            health.raise_for_status()
            if health.json().get("sector") != sector:
                raise RuntimeError(f"{sector} mounted health endpoint returned the wrong sector")

            body = {"agent": sector, "message": config["query"]}
            if mode in {"sync", "both"}:
                response = await client.post("/api/v1/chat", json=body)
                response.raise_for_status()
                result = response.json()
                _validate_result(sector, result)
                print(
                    f"PASS sync {sector}: status={result['status']}, "
                    f"citations={len(result['citations'])}"
                )

            if mode in {"stream", "both"}:
                async with client.stream("POST", "/api/v1/chat/stream", json=body) as response:
                    response.raise_for_status()
                    await response.aread()
                    events = _stream_events(response.text)
                types = {event.get("type") for event in events}
                if not {"step", "token", "done"}.issubset(types):
                    raise RuntimeError(
                        f"{sector} stream missing event types: "
                        f"{sorted({'step', 'token', 'done'} - types)}"
                    )
                done = next(event for event in reversed(events) if event.get("type") == "done")
                _validate_result(sector, done)
                print(
                    f"PASS stream {sector}: status={done['status']}, "
                    f"citations={len(done['citations'])}"
                )


def _validate_result(sector: str, result: dict[str, Any]) -> None:
    expected_keys = {"status", "agent_routed", "full_report", "data_context", "freshness", "errors", "citations"}
    missing = expected_keys - result.keys()
    if missing:
        raise RuntimeError(f"{sector} response is missing fields: {sorted(missing)}")
    if result["status"] not in {"completed", "partial", "unavailable", "failed"}:
        raise RuntimeError(f"{sector} returned unrecognized status {result['status']!r}")
    if result["status"] == "failed":
        details = "; ".join(str(error) for error in result["errors"])
        raise RuntimeError(f"{sector} agent failed: {details}")
    if not isinstance(result["full_report"], str) or not result["full_report"].strip():
        raise RuntimeError(f"{sector} returned an empty report")
    if not isinstance(result["data_context"], dict):
        raise RuntimeError(f"{sector} returned invalid data_context")
    if not isinstance(result["freshness"], dict) or not isinstance(result["citations"], list):
        raise RuntimeError(f"{sector} returned invalid freshness/citations")
    citation_fields = {
        "source_agent",
        "source_authority",
        "table_reference",
        "retrieval_url",
        "observation_period",
        "freshness",
    }
    for citation in result["citations"]:
        if not isinstance(citation, dict) or not citation_fields <= citation.keys():
            raise RuntimeError(f"{sector} returned citation metadata without required provenance")
    for error in result["errors"]:
        print(f"  NOTE {sector} retrieval: {error}")
    if result["status"] == "unavailable":
        print(f"  NOTE {sector}: sources/cache supplied no usable observations")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("sync", "stream", "both"),
        default="stream",
        help="chat contract(s) to exercise; both is the default",
    )
    parser.add_argument(
        "--sector",
        choices=tuple(SECTORS),
        action="append",
        help="limit checks to one or more sectors; defaults to all four",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="check gateway schema initialization without making source requests",
    )
    args = parser.parse_args()

    check_schemas()
    if not args.schema_only:
        asyncio.run(check_chat(args.mode, set(args.sector or ())))
    print("All selected sector gateway checks passed.")


if __name__ == "__main__":
    main()
