"""Orchestrator-side A2A delegation: concurrent dispatch, follow-ups and result aggregation."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from core.protocols.a2a import A2AClient, A2ACallContext, A2AResponse, agent_registry
from core.protocols.a2a.executor_adapter import SECTOR_ANALYSIS

from .canonical_ids import CANONICAL_ID_MAP, resolve_canonical_id

ORCHESTRATOR_ID = "orchestrator"
_MAX_FOLLOW_UPS_PER_RESPONSE = 3
_MAX_SOURCES_REPORTED = 30


import concurrent.futures

_SYNC_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_sync(coro: Any) -> Any:
    """Run a coroutine from sync LangGraph nodes, even if an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return _SYNC_POOL.submit(asyncio.run, coro).result()


def agents_for_sectors(sectors: list[str]) -> list[str]:
    """Resolve legacy SectorEnum values to agent ids through card metadata."""
    ids: list[str] = []
    for card in agent_registry.list_agents():
        if card.agent_id and card.metadata.get("sector") in sectors and card.agent_id not in ids:
            ids.append(card.agent_id)
    return ids


async def delegate(
    query: str,
    agent_ids: list[str],
    conversation_id: str,
    client: Optional[A2AClient] = None,
) -> list[A2AResponse]:
    """Send `sector_analysis` to each agent concurrently, then run one bounded follow-up round."""
    a2a = client or A2AClient(ORCHESTRATOR_ID)
    requests = [
        a2a.build_request(agent_id, SECTOR_ANALYSIS, {"query": query},
                          conversation_id=conversation_id, context={"query": query})
        for agent_id in agent_ids
    ]
    # No retries: a timed-out full analysis is expensive to repeat.
    responses = await a2a.send_many(requests, retries=0)

    follow_requests = []
    for response in responses:
        parent = A2ACallContext(
            conversation_id=conversation_id, request_id=response.request_id,
            agent_id=ORCHESTRATOR_ID, depth=0, call_chain=(ORCHESTRATOR_ID,),
        )
        for follow in response.follow_ups[:_MAX_FOLLOW_UPS_PER_RESPONSE]:
            follow_requests.append(a2a.build_request(
                follow.receiver_agent, follow.task, follow.parameters, parent=parent,
                context={"reason": follow.reason, "requested_by": response.sender_agent},
            ))
    if follow_requests:
        responses.extend(await a2a.send_many(follow_requests, retries=0))
    return responses


def _extract_json_artifact(
    agent_id: str, card_name: str, art: dict[str, Any], sources: list[dict[str, Any]],
    analyses: list[dict[str, Any]], observations: list[dict[str, Any]], citations: list[dict[str, Any]],
) -> None:
    content = art["content"]
    metadata = art.get("metadata") or {}
    prov_hash = metadata.get("sha256") or art.get("provenance_hash")
    analyses.append({
        "agent": card_name, "agent_id": agent_id, "artifact_name": art["name"],
        "provenance_hash": prov_hash, "metrics": content, "sources": sources,
    })

    if agent_id == "agriculture_sector":
        for citation in content.get("citations", []):
            if citation.get("value") is None:
                continue
            item = {
                **citation,
                "indicator_id": "in.macro.agri." + citation["mcp_tool"].removeprefix("get_"),
                "observation_period": citation.get("period", "unspecified"),
                "data_status": citation.get("freshness", "official"),
                "period": citation.get("period", "unspecified"),
                "provenance_hash": art.get("provenance_hash") or prov_hash,
            }
            observations.append(item)
            citations.append(item)
        return

    # 1. Indicators or observations represented as a list of dicts (e.g. prices_sector)
    obs_list = content.get("indicators") if isinstance(content.get("indicators"), list) else None
    if not obs_list and isinstance(content.get("observations"), list):
        obs_list = content["observations"]
    if obs_list:
        for obs in obs_list:
            if not isinstance(obs, dict):
                continue
            raw_id = obs.get("indicator_id") or obs.get("indicator") or "unknown"
            can_id = resolve_canonical_id(raw_id, agent_id)
            val = obs.get("value")
            if val is None:
                continue
            period = obs.get("observation_period") or obs.get("period") or "unspecified"
            unit = obs.get("unit", "")
            status = obs.get("data_status") or obs.get("status") or "official"
            item = {
                "indicator_id": can_id,
                "value": val,
                "unit": unit,
                "observation_period": period,
                "data_status": status,
                "period": period,
                "provenance_hash": prov_hash,
            }
            observations.append(item)
            citations.append(item)

    # 2. Indicators at top level as a dict (e.g. fiscal_sector, external_sector)
    top_ind = content.get("indicators")
    if isinstance(top_ind, dict):
        for ind_name, ind_data in top_ind.items():
            can_id = resolve_canonical_id(ind_name, agent_id)
            if isinstance(ind_data, dict):
                val = ind_data.get("latest_value") or ind_data.get("value")
                if val is None:
                    continue
                unit = ind_data.get("unit", "")
                period = ind_data.get("latest_period") or ind_data.get("period", "unspecified")
                status = ind_data.get("data_status", "official")
            elif isinstance(ind_data, (int, float, str)) and ind_data not in (None, ""):
                val = ind_data
                unit = "%" if "pct" in ind_name else ("₹ Cr" if "cr" in ind_name else "")
                period = content.get("period") or "latest"
                status = "official"
            else:
                continue
            item = {
                "indicator_id": can_id,
                "value": val,
                "unit": unit,
                "observation_period": period,
                "data_status": status,
                "period": period,
                "provenance_hash": prov_hash,
            }
            observations.append(item)
            citations.append(item)

    # 3. Indicators nested inside content.values() (e.g. monetary_sector test artifact)
    for val in content.values():
        if isinstance(val, dict) and isinstance(val.get("indicators"), dict):
            for ind_name, ind_data in val["indicators"].items():
                if not isinstance(ind_data, dict):
                    continue
                can_id = resolve_canonical_id(ind_name, agent_id)
                item = {
                    "indicator_id": can_id,
                    "value": ind_data.get("latest_value"),
                    "unit": ind_data.get("unit", ""),
                    "observation_period": ind_data.get("latest_period", "unspecified"),
                    "data_status": ind_data.get("data_status", "unspecified"),
                    "period": ind_data.get("latest_period", "unspecified"),
                    "provenance_hash": prov_hash,
                }
                observations.append(item)
                citations.append(item)

    # 4. Top-level citations list if available
    for cit in content.get("citations", []):
        if not isinstance(cit, dict) or cit.get("value") is None:
            continue
        raw_id = cit.get("indicator_id") or cit.get("indicator") or "unknown"
        can_id = resolve_canonical_id(raw_id, agent_id)
        period = cit.get("period") or cit.get("observation_period") or "unspecified"
        item = {
            "indicator_id": can_id,
            "value": cit["value"],
            "unit": cit.get("unit", ""),
            "observation_period": period,
            "data_status": cit.get("data_status") or cit.get("freshness", "official"),
            "period": period,
            "provenance_hash": prov_hash,
        }
        observations.append(item)
        citations.append(item)


def _extract_markdown_artifact(
    agent_id: str, md_text: str, prov_hash: Optional[str],
    observations: list[dict[str, Any]], citations: list[dict[str, Any]],
) -> None:
    """Parse indicator metrics from structured markdown tables when available."""
    lines = md_text.splitlines()
    in_table = False
    col_idx: dict[str, int] = {}

    for line in lines:
        line_clean = line.strip()
        if not (line_clean.startswith("|") and line_clean.endswith("|")):
            in_table = False
            col_idx = {}
            continue

        parts = [p.strip() for p in line_clean.strip("|").split("|")]
        if not parts:
            continue

        lowered = [p.lower() for p in parts]
        if any("indicator" in p for p in lowered) and any("value" in p for p in lowered):
            in_table = True
            col_idx = {
                "indicator": next(i for i, p in enumerate(lowered) if "indicator" in p),
                "value": next(i for i, p in enumerate(lowered) if "value" in p),
                "unit": next((i for i, p in enumerate(lowered) if "unit" in p), -1),
                "period": next((i for i, p in enumerate(lowered) if "period" in p), -1),
                "source": next((i for i, p in enumerate(lowered) if "source" in p or "authority" in p), -1),
            }
            continue

        if all(set(p).issubset({"-", ":"}) for p in parts):
            continue

        if in_table and "indicator" in col_idx and "value" in col_idx:
            ind_i = col_idx["indicator"]
            val_i = col_idx["value"]
            if ind_i < len(parts) and val_i < len(parts):
                raw_ind = parts[ind_i]
                raw_val = parts[val_i].replace("**", "").replace("$", "").replace("₹", "").strip()
                if raw_val.lower() in ("n/a", "unavailable", "unknown", "-", ""):
                    continue

                unit = parts[col_idx["unit"]] if col_idx.get("unit", -1) != -1 and col_idx["unit"] < len(parts) else ""
                period = parts[col_idx["period"]] if col_idx.get("period", -1) != -1 and col_idx["period"] < len(parts) else "unspecified"
                source = parts[col_idx["source"]] if col_idx.get("source", -1) != -1 and col_idx["source"] < len(parts) else "official"

                val_clean = raw_val.rstrip("%").strip()
                try:
                    val: Any = float(val_clean.replace(",", ""))
                except ValueError:
                    val = raw_val

                can_id = resolve_canonical_id(raw_ind, agent_id)
                item = {
                    "indicator_id": can_id,
                    "value": val,
                    "unit": unit or ("%" if "%" in raw_val else ""),
                    "observation_period": period,
                    "data_status": source,
                    "period": period,
                    "provenance_hash": prov_hash,
                }
                observations.append(item)
                citations.append(item)


def aggregate(responses: list[A2AResponse]) -> dict[str, Any]:
    """Validate and merge A2A responses into orchestrator state; failures degrade, never abort."""
    analyses: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for response in responses:
        agent_id = response.sender_agent
        card = agent_registry.get_agent(agent_id)
        card_name = card.name if card else agent_id
        for err in response.errors:
            errors.append({"agent": agent_id, "request_id": response.request_id,
                           "code": err.code.value, "message": err.message})
        if not response.ok or not isinstance(response.result, dict):
            continue
        source_dicts = [s.model_dump(mode="json") for s in response.sources]
        sources.extend({"agent": agent_id, **s} for s in source_dicts)
        for art in response.result.get("artifacts", []):
            prov_hash = art.get("metadata", {}).get("sha256") or art.get("provenance_hash")
            if art["type"] == "json" and isinstance(art["content"], dict):
                _extract_json_artifact(agent_id, card_name, art, source_dicts,
                                       analyses, observations, citations)
            elif art["type"] == "markdown" and isinstance(art["content"], str):
                analyses.append({
                    "agent": card_name, "agent_id": agent_id, "artifact_name": art["name"],
                    "provenance_hash": prov_hash,
                    "report_markdown": art["content"], "sources": source_dicts,
                })
                _extract_markdown_artifact(agent_id, art["content"], prov_hash,
                                          observations, citations)

    # Deduplicate observations and citations by indicator_id and period
    seen_obs: set[tuple[str, str]] = set()
    deduped_obs: list[dict[str, Any]] = []
    for o in observations:
        key = (o.get("indicator_id", ""), str(o.get("observation_period") or o.get("period")))
        if key not in seen_obs and o.get("value") is not None:
            seen_obs.add(key)
            deduped_obs.append(o)

    seen_cit: set[tuple[str, str]] = set()
    deduped_cit: list[dict[str, Any]] = []
    for c in citations:
        key = (c.get("indicator_id", ""), str(c.get("period") or c.get("observation_period")))
        if key not in seen_cit and c.get("value") is not None:
            seen_cit.add(key)
            deduped_cit.append(c)

    succeeded = sum(1 for r in responses if r.ok)
    status = "a2a_completed" if succeeded == len(responses) else ("a2a_partial" if succeeded else "a2a_failed")
    return {
        "collected_observations": deduped_obs,
        "agent_analyses": analyses,
        "citations": deduped_cit,
        "a2a_sources": sources[:_MAX_SOURCES_REPORTED],
        "a2a_errors": errors,
        "status": status,
    }

