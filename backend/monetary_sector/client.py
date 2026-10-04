"""Async fetch orchestrators for Monetary Sector RBI data.

Dataset fetchers with the live-first chain (Eco-Policy MCP via the standard
MCP SDK stdio client, DBIE CDN direct HTTP exactly like the finance sector,
DuckDB cache), the stance derivation, Tavily direct search, and explicit
live-data enforcement. Caching lives in ``cache_loaders``.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import json
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from monetary_sector import cache_loaders
from monetary_sector import database as db
from monetary_sector.cache_loaders import MonetaryDataUnavailableError
from monetary_sector.config import monetary_settings
from monetary_sector.models import (
    Citation,
    DataFreshness,
    MoneySupplyRecord,
    MonetaryStanceRecord,
    PolicyRatesRecord,
    SystemLiquidityRecord,
)
from monetary_sector.parsers import (
    parse_money_supply,
    parse_policy_rates,
    parse_system_liquidity,
    safe_float_val as _safe_float,
)

logger = logging.getLogger(__name__)

# ── DBIE direct HTTP (finance-sector pattern: plain httpx, no subprocesses) ──
_CDN = monetary_settings.DBIE_CDN_BASE

_HTTP_TABLES: dict[str, dict[str, str]] = {
    "policy_rates": {
        "url": f"{_CDN}/select-economic-indicators.json",
        "database_table": "policy_rates",
        "document_title": "Select Economic Indicators (Monthly), RBI Bulletin Table 1",
        "table_reference": "/banking/select-economic-indicators",
        "frequency": "Monthly",
    },
    "money_supply": {
        "url": f"{_CDN}/money-stock-measures.json",
        "database_table": "money_supply",
        "document_title": "Money Stock Measures, RBI Bulletin Table 6",
        "table_reference": "/banking/money-stock-measures",
        "frequency": "Monthly",
    },
    "system_liquidity": {
        "url": f"{_CDN}/liquidity-operations.json",
        "database_table": "system_liquidity",
        "document_title": "Liquidity Operations by RBI, RBI Bulletin Table 3",
        "table_reference": "/banking/liquidity-operations",
        "frequency": "Daily",
    },
}


def _make_retry():
    return retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


@_make_retry()
async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any:
    """Fetch and parse a JSON response. Raises on non-2xx."""
    response = await client.get(url, params=params, timeout=monetary_settings.DBIE_TIMEOUT)
    if response.is_error:
        response.raise_for_status()
    return response.json()


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            float(monetary_settings.DBIE_TIMEOUT),
            connect=monetary_settings.HTTP_CONNECT_TIMEOUT,
            read=monetary_settings.HTTP_READ_TIMEOUT,
        ),
        headers={"User-Agent": "macrograph-ai/monetary-sector"},
        follow_redirects=True,
    )


async def _fetch_live_records(dataset: str, lookback: int) -> list[Any]:
    """Fetch a dataset from the DBIE CDN static JSON mirror (finance pattern).

    Same upstream data as the DBIE MCP tables, without spawning any
    subprocess. Raises on any fetch/parse failure for the caller to handle.
    """
    parser = {
        "policy_rates": parse_policy_rates,
        "money_supply": parse_money_supply,
        "system_liquidity": parse_system_liquidity,
    }[dataset]
    spec = _HTTP_TABLES[dataset]
    async with _build_client() as http_client:
        payload = await _fetch_json(http_client, spec["url"])
    if not isinstance(payload, dict):
        raise ValueError(f"DBIE CDN {spec['url']} returned no JSON object.")
    context = {
        "document_title": spec["document_title"],
        "table_reference": spec["table_reference"],
        "retrieval_url": spec["url"],
        "source_base_url": "https://dbie.rbihub.in",
        "source_note": (
            "RBI DBIE CloudFront CDN static JSON mirror; reflects the "
            "deployment's last scrape, not real-time values."
        ),
        "frequency": spec["frequency"],
        "unit": payload.get("unit") or payload.get("units"),
        "as_of": None,
    }
    return parser(payload, lookback, context)

_ECO_POLICY_COMMAND: tuple[str, ...] = ("uvx", "eco-policy-mcp")


def _log_fallback(tool_name: str, error: Exception) -> None:
    logger.warning("%s failed; falling back to DuckDB: %s", tool_name, error)
    try:
        db.log_fetch(tool_name, "cache_fallback", error_msg=str(error))
    except Exception as log_error:
        logger.warning("Could not record %s fallback in fetch log: %s", tool_name, log_error)


async def _fetch_with_cache(
    dataset: str,
    lookback: int,
    record_type: Any,
    *,
    force_live: bool = False,
) -> list[Any]:
    db.initialise_schema()
    spec = _HTTP_TABLES[dataset]
    tool_name = f"get_{dataset}"
    if not force_live:
        fresh = cache_loaders._load_fresh_cache(
            spec["database_table"], lookback, record_type, tool_name,
            cache_loaders._DATASET_TTL_SECONDS[dataset],
        )
        if fresh is not None:
            return fresh
    try:
        records = await _fetch_live_records(dataset, lookback)
        cache_loaders._save_records(spec["database_table"], records, tool_name)
        return records
    except Exception as exc:
        if force_live:
            raise MonetaryDataUnavailableError(
                f"{tool_name} unavailable: live MCP sources failed and the DuckDB "
                f"cache is bypassed for this explicit live-data request ({exc})."
            ) from exc
        _log_fallback(tool_name, exc)
        return cache_loaders._load_cache(spec["database_table"], lookback, record_type, tool_name)


def _subprocess_env() -> dict[str, str] | None:
    """Environment for the eco-policy MCP subprocess.

    Redirects uv/temp writes to D: when those directories exist (the C: drive
    on this machine is full, which otherwise breaks package execution).
    Returns None to inherit the process environment untouched otherwise.
    """
    if os.name != "nt":
        return None
    redirect = False
    env = dict(os.environ)
    for key, path in (
        ("UV_CACHE_DIR", r"D:\uv-cache"),
        ("TEMP", r"D:\Temp"),
        ("TMP", r"D:\Temp"),
    ):
        if os.path.isdir(path) and key not in env:
            env[key] = path
            redirect = True
    return env if redirect else None


async def _call_eco_policy_tool() -> Any:
    """Call `rbi_get_policy_rates` on the Eco-Policy MCP server via stdio.

    Uses the standard MCP SDK client (this data source is distributed as a
    local MCP server with no plain-HTTP data API). Raises on any transport
    or tool failure; callers translate that into fallback behavior.
    """
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command="uvx", args=["eco-policy-mcp"], env=_subprocess_env()
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "rbi_get_policy_rates", {}, read_timeout_seconds=90.0
            )
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    if getattr(result, "is_error", False):
        raise ValueError(f"Eco-Policy MCP tool reported an error: {getattr(result, 'content', None)}")
    texts = [
        getattr(item, "text", None)
        for item in (getattr(result, "content", None) or [])
    ]
    text = next((t for t in texts if isinstance(t, str) and t.strip()), None)
    if text is None:
        raise ValueError("Eco-Policy MCP tool returned no text content.")
    payload = json.loads(text)
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(f"Eco-Policy MCP tool returned an error payload: {payload}")
    return payload


async def _fetch_policy_rates_from_eco_policy() -> PolicyRatesRecord | None:
    """Live RBI policy rates from the Eco-Policy MCP server (`rbi_get_policy_rates`).

    Returns None when the server is unreachable or returns no repo rate, so the
    caller falls through to the DBIE CDN mirror and then the DuckDB cache.
    """
    try:
        payload = await _call_eco_policy_tool()
    except Exception as exc:
        logger.warning("Eco-Policy MCP unavailable, will try DBIE: %s", exc)
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    provenance = payload.get("provenance") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not isinstance(provenance, dict):
        return None
    repo = _safe_float(data.get("policy_repo_rate"))
    if repo is None:
        logger.warning("Eco-Policy MCP returned no repo rate; will try DBIE.")
        return None
    effective = str(data.get("rates_effective_from") or "").strip()
    if not effective:
        effective = str(provenance.get("as_of") or "")[:10].strip()
    if not effective:
        return None
    sdf = _safe_float(data.get("standing_deposit_facility_sdf"))
    msf = _safe_float(data.get("marginal_standing_facility_msf"))
    corridor = round((msf - sdf) * 100, 1) if msf is not None and sdf is not None else None
    stance = data.get("stance")
    citation = Citation(
        source_agent="monetary_sector",
        source_authority="Reserve Bank of India (RBI) via Eco-Policy MCP",
        document_title="Monetary Policy Committee Key Rates & Reserve Requirements",
        table_reference="eco-policy:rbi_get_policy_rates",
        retrieval_url=provenance.get("reference") or "https://rbi.org.in",
        observation_period=effective,
        freshness=DataFreshness.LIVE,
        as_of=provenance.get("as_of"),
        source_note=provenance.get("note")
        or "Official RBI policy-rate announcement via the Eco-Policy MCP registry.",
        unit=str(data.get("unit") or "percent per annum"),
        source_values={key: value for key, value in data.items() if value is not None},
    )
    return PolicyRatesRecord(
        period=effective,
        repo_rate_pct=repo,
        reverse_repo_rate_pct=_safe_float(data.get("reverse_repo_rate")),
        sdf_rate_pct=sdf,
        msf_rate_pct=msf,
        bank_rate_pct=_safe_float(data.get("bank_rate")),
        crr_pct=_safe_float(data.get("cash_reserve_ratio_crr")),
        slr_pct=_safe_float(data.get("statutory_liquidity_ratio_slr")),
        corridor_width_bps=corridor,
        stance=str(stance).strip() if isinstance(stance, str) and stance.strip() else None,
        rates_effective_from=effective,
        citation=citation,
    )


async def fetch_policy_rates(
    lookback_months: int = 12, *, force_live: bool = False
) -> list[PolicyRatesRecord]:
    """Live RBI policy rates: Eco-Policy MCP first, DBIE MCP second, DuckDB cache last.

    With force_live=True the cache fallback is skipped: live MCP failure raises
    MonetaryDataUnavailableError instead of serving cached rows.
    """
    db.initialise_schema()
    if not force_live:
        fresh = cache_loaders._load_fresh_cache(
            "policy_rates", lookback_months, PolicyRatesRecord, "get_policy_rates",
            cache_loaders._DATASET_TTL_SECONDS["policy_rates"],
        )
        if fresh is not None:
            return fresh
    eco_record = await _fetch_policy_rates_from_eco_policy()
    if eco_record is not None:
        cache_loaders._save_records("policy_rates", [eco_record], "get_policy_rates", fetch_status="live")
        return [eco_record]
    return await _fetch_with_cache(
        "policy_rates", lookback_months, PolicyRatesRecord, force_live=force_live
    )


async def fetch_money_supply(
    lookback_months: int = 12, *, force_live: bool = False
) -> list[MoneySupplyRecord]:
    """Fetch the published money-stock table, preserving its reported values."""
    return await _fetch_with_cache(
        "money_supply", lookback_months, MoneySupplyRecord, force_live=force_live
    )


async def fetch_system_liquidity(
    lookback_months: int = 6, *, force_live: bool = False
) -> list[SystemLiquidityRecord]:
    """Fetch RBI liquidity-operation components without inventing a net total."""
    return await _fetch_with_cache(
        "system_liquidity", lookback_months, SystemLiquidityRecord, force_live=force_live
    )


def derive_and_save_stance_snapshot(rate_records: list[Any]) -> MonetaryStanceRecord | None:
    """Build the stance snapshot from already-fetched policy-rate records.

    Pure derivation plus a save: no MCP calls, so the agent can reuse one
    rates fetch instead of spawning a second live pull. The stance label comes
    only from the policy-rate table; real rate, M3 growth, and liquidity
    status stay absent unless their own sources provide them. Returns None
    when no snapshot can be derived; callers fall back to the standalone
    fetcher below.
    """
    try:
        if not rate_records:
            return None
        rate = rate_records[0]
        repo = getattr(rate, "repo_rate_pct", None)
        if repo is None:
            return None
        record = MonetaryStanceRecord(
            period=getattr(rate, "period", None),
            repo_rate_pct=repo,
            stance_label=getattr(rate, "stance", None),
            real_policy_rate_pct=None,
            m3_growth_pct=None,
            system_liquidity_status=None,
            citation=getattr(rate, "citation", None),
        )
        rate_freshness = getattr(getattr(rate, "citation", None), "freshness", None)
        rate_freshness = getattr(rate_freshness, "value", "") or ""
        cache_loaders._save_records(
            "monetary_stance",
            [record],
            "get_monetary_stance_snapshot",
            fetch_status="live" if rate_freshness == "live" else "upstream_snapshot",
        )
        return record
    except Exception as exc:
        logger.warning("Could not derive stance snapshot from rates: %s", exc)
        return None


async def fetch_monetary_stance_snapshot(
    *, force_live: bool = False
) -> list[MonetaryStanceRecord]:
    """Return a sourced policy-rate snapshot; unsupported stance metrics remain absent."""
    db.initialise_schema()
    if not force_live:
        fresh = cache_loaders._load_fresh_cache(
            "monetary_stance", 1, MonetaryStanceRecord, "Monetary stance snapshot",
            cache_loaders._DATASET_TTL_SECONDS["monetary_stance"],
        )
        if fresh is not None:
            return fresh
    try:
        rates = await fetch_policy_rates(lookback_months=1, force_live=force_live)
        record = derive_and_save_stance_snapshot(rates)
        if record is None:
            raise ValueError("No policy-rate observations were returned.")
        return [record]
    except Exception as exc:
        if force_live:
            raise MonetaryDataUnavailableError(
                "get_monetary_stance_snapshot unavailable: live MCP sources failed "
                f"and the cache is bypassed for this explicit live-data request ({exc})."
            ) from exc
        _log_fallback("get_monetary_stance_snapshot", exc)
        return cache_loaders._load_cache(
            "monetary_stance", 1, MonetaryStanceRecord, "Monetary stance snapshot",
        )


def _get_tavily_key() -> str | None:
    return (
        monetary_settings.TVLY_KEY_1
        or os.getenv("TVLY_KEY_1")
    )


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    stop=stop_after_attempt(2),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def fetch_mpc_news_via_tavily_mcp(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Real-time MPC news through the Tavily AI Search API (finance pattern).

    Plain HTTPS POST with no subprocess, so a full disk or busy process table
    cannot break it. Never raises: returns [] on any transport, auth, or
    schema failure so news enrichment can never break a sector answer.
    """
    from monetary_sector.models import TavilyNewsItem

    api_key = _get_tavily_key()
    if not api_key:
        logger.info("Tavily API key not configured for monetary sector. Skipping search enrichment.")
        return []

    tavily_url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query[:240],
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(tavily_url, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    "Tavily monetary search returned status %s: %s",
                    resp.status_code, resp.text[:200],
                )
                return []

            data = resp.json()
            raw_results = data.get("results", [])
            items: list[dict[str, Any]] = []
            for entry in raw_results:
                if not isinstance(entry, dict):
                    continue
                item = TavilyNewsItem(
                    title=str(entry.get("title", "")).strip(),
                    url=str(entry.get("url", "")).strip(),
                    content=str(entry.get("content", "")).strip()[:800],
                    published_date=entry.get("published_date"),
                    source="Tavily AI Search",
                    score=entry.get("score"),
                )
                if not item.title or not item.url:
                    continue
                items.append({
                    "title": item.title,
                    "url": item.url,
                    "snippet": item.content[:500],
                    "date": item.published_date,
                    "source": item.source,
                })
            return items
    except Exception as exc:
        logger.warning("Tavily search failed for monetary sector: %s", exc)
        return []
