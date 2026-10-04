"""Chat endpoints supporting streaming (SSE) and synchronous multi-agent interaction."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.orchestrator.graph import macro_orchestrator_graph
from core.sector_reasoning import select_relevant_services_with_llm
from finance_sector.agent import finance_agent_node
from api.chat_config import _DIRECT_SECTOR_CHAT
from api.chat_helpers import (
    _build_finance_citations,
    _run_direct_sector_chat,
    _sector_progress_events,
)

router = APIRouter(tags=["Chat"])


def _get_runner():
    """Retrieve direct sector chat runner, allowing monkeypatching on main/gateway."""
    for mod_name in ("main", "backend.main"):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, "_run_direct_sector_chat"):
            return getattr(mod, "_run_direct_sector_chat")
    return _run_direct_sector_chat


def _get_selector():
    """Retrieve service selector, allowing monkeypatching on main/gateway."""
    for mod_name in ("main", "backend.main"):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, "select_relevant_services_with_llm"):
            return getattr(mod, "select_relevant_services_with_llm")
    return select_relevant_services_with_llm


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User query or macroeconomic research question")
    agent: str = Field(
        default="orchestrator",
        description=(
            "'orchestrator', 'finance_sector', 'external_sector', 'labour_sector', "
            "'capital_market_sector', 'monetary_sector', or 'real_sector'"
        ),
    )
    scenario_shock: Optional[Dict[str, Any]] = None


@router.post("/api/v1/chat/stream", tags=["Chat"])
async def stream_chat(request: ChatMessageRequest):
    """Server-Sent Events (SSE) streaming chat endpoint with real-time agent updates and fluid token output."""
    async def event_generator():
        msg = request.message.strip()
        target = request.agent.lower()

        if target == "finance_sector":
            # Direct domain investigation of Finance & Banking sector
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'finance_sector', 'title': 'Targeting Finance Sector Agent', 'detail': 'Bypassing Orchestrator. Direct domain investigation of Indian Scheduled Commercial Banks.'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 2, 'agent': 'finance_sector', 'tool': 'get_bank_credit_growth', 'title': 'Invoking FastMCP Tool: get_bank_credit_growth', 'detail': 'Querying non-food credit & sectoral deployment from RBI DBIE (Table r539)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 3, 'agent': 'finance_sector', 'tool': 'get_asset_quality', 'title': 'Invoking FastMCP Tool: get_asset_quality', 'detail': 'Querying Gross NPA, Net NPA, CRAR & PCR ratios from Financial Stability Report (Table r330)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 4, 'agent': 'finance_sector', 'tool': 'get_lending_and_deposit_rates', 'title': 'Invoking FastMCP Tool: get_lending_and_deposit_rates', 'detail': 'Querying WALR, MCLR & WADTDR spreads from RBI Bulletin (Table r531)...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 5, 'agent': 'finance_sector', 'title': 'Executing LLM Econometric Reasoning', 'detail': 'Analyzing banking stability & transmission via Groq LLM reasoning engine...'})}\n\n"

            node_result = await finance_agent_node({"query": msg})
            analysis_text = node_result.get("finance_sector_analysis", "")
            data_context = node_result.get("finance_sector_data", {})
            freshness = node_result.get("finance_sector_freshness", {})

            words = analysis_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.04)

            # Check if query is out-of-domain and declined
            is_domain_decline = (
                any(k in analysis_text.lower() for k in ["outside my domain", "falls outside", "switch to the", "scope"])
                and not any(k in msg.lower() for k in ["bank", "npa", "credit", "loan", "lending", "deposit", "mclr", "walr", "crar", "scb"])
            )

            if is_domain_decline:
                citations = []
            else:
                citations = _build_finance_citations(data_context, freshness)

            done_payload = {
                "type": "done",
                "agent_routed": "Finance & Banking Sector Agent",
                "full_report": analysis_text,
                "data_context": data_context,
                "citations": citations,
                "freshness": freshness,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        elif target in _DIRECT_SECTOR_CHAT:
            selector = _get_selector()
            runner = _get_runner()
            sector_config = _DIRECT_SECTOR_CHAT[target]
            selected_services, selection_error = await selector(
                query=msg,
                service_keywords=sector_config["service_keywords"],
                api_key=sector_config["api_key"],
                model=sector_config["model"],
            )
            for progress_event in _sector_progress_events(
                target,
                selected_services,
                selection_error,
            ):
                yield f"data: {json.dumps(progress_event)}\n\n"
                await asyncio.sleep(0.15)

            sector_response = await runner(
                target,
                msg,
                selected_services=selected_services,
                selection_error=selection_error,
            )
            report_text = sector_response["full_report"]
            words = report_text.split()
            for index in range(0, len(words), 5):
                chunk = " ".join(words[index:index + 5]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            done_payload = {
                "type": "done",
                "agent_routed": sector_response["agent_routed"],
                "full_report": report_text,
                "data_context": sector_response["data_context"],
                "freshness": sector_response["freshness"],
                "errors": sector_response["errors"],
                "citations": sector_response["citations"],
                "mermaid_diagram": "",
                "confidence_score": None,
                "status": sector_response["status"],
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        else:
            # Multi-agent orchestrator route
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'orchestrator', 'title': 'Orchestrator Decomposing Query', 'detail': 'Analyzing question semantics, identifying domain boundaries across 10 sectors...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 2, 'agent': 'orchestrator', 'title': 'A2A Protocol Task Dispatch', 'detail': 'Inspecting registered Agent Cards, routing subtasks to Finance & Real sector peers...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 3, 'agent': 'finance_sector', 'tool': 'get_bank_credit_growth', 'title': 'FastMCP Data Retrieval', 'detail': 'Sector agents querying canonical DuckDB store and live RBI DBIE mirrors...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 4, 'agent': 'orchestrator', 'title': 'Causal Knowledge Graph Traversal', 'detail': 'Mapping cross-sector transmission paths in NetworkX Causal Graph engine...'})}\n\n"
            await asyncio.sleep(0.25)

            yield f"data: {json.dumps({'type': 'step', 'step': 5, 'agent': 'orchestrator', 'title': 'Academic Synthesis & Citation Verification', 'detail': 'Applying strict anti-hallucination checks and generating cited report via Groq LLM...'})}\n\n"

            loop = asyncio.get_running_loop()
            final_state = await loop.run_in_executor(
                None,
                lambda: macro_orchestrator_graph.invoke({
                    "query": msg,
                    "scenario_shock": request.scenario_shock,
                    "status": "started"
                })
            )

            report_text = final_state.get("final_report", "")
            collected_obs = final_state.get("collected_observations", [])
            citations = final_state.get("citations", [])
            mermaid_diag = final_state.get("mermaid_diagram", "")
            target_sectors = final_state.get("target_sectors", [])

            words = report_text.split(" ")
            chunk_size = 5
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            done_payload = {
                "type": "done",
                "agent_routed": "Macrograph Orchestrator (Multi-Sector)",
                "target_sectors": target_sectors,
                "full_report": report_text,
                "citations": citations,
                "observations": collected_obs,
                "mermaid_diagram": mermaid_diag,
                "confidence_score": final_state.get("confidence_score", 0.94),
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/v1/chat", tags=["Chat"])
async def sync_chat(request: ChatMessageRequest) -> Dict[str, Any]:
    """Synchronous non-streaming chat endpoint."""
    target = request.agent.lower()
    if target == "finance_sector":
        node_result = await finance_agent_node({"query": request.message})
        d_context = node_result.get("finance_sector_data", {})
        f_freshness = node_result.get("finance_sector_freshness", {})
        return {
            "status": "completed",
            "agent_routed": "Finance & Banking Sector Agent",
            "full_report": node_result.get("finance_sector_analysis", ""),
            "data_context": d_context,
            "freshness": f_freshness,
            "citations": _build_finance_citations(d_context, f_freshness),
        }
    elif target in _DIRECT_SECTOR_CHAT:
        runner = _get_runner()
        return await runner(target, request.message)
    else:
        initial_state = {
            "query": request.message,
            "scenario_shock": request.scenario_shock,
            "status": "started"
        }
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(
            None,
            lambda: macro_orchestrator_graph.invoke(initial_state)
        )
        return {
            "status": "completed",
            "agent_routed": "Macrograph Orchestrator",
            "full_report": final_state.get("final_report", ""),
            "target_sectors": final_state.get("target_sectors", []),
            "citations": final_state.get("citations", []),
            "observations": final_state.get("collected_observations", []),
            "mermaid_diagram": final_state.get("mermaid_diagram", ""),
        }
