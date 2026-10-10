"""Chat endpoints: SSE streaming and synchronous multi-agent interaction."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from core.protocols.a2a.messages import new_id
from core.protocols.a2a.trace import trace_store
from core.orchestrator.a2a_stream import a2a_summary, trace_step_events
from core.orchestrator.graph import macro_orchestrator_graph
from agriculture_sector.agent import (
    select_agriculture_tools,
)
from prices_sector.agent import is_direct_prices_query
import json
import asyncio
from fastapi.responses import StreamingResponse
from core.sector_reasoning import select_relevant_services_with_llm
from finance_sector.agent import finance_agent_node
from real_sector.agent import (
    _select_services_deterministically,
)
from services_sector.agent import (
    _select_services_deterministically as _select_services_services,
)

from fastapi import APIRouter
from api.chat_config import _DIRECT_SECTOR_CHAT
from api.chat_helpers import (
    _build_finance_citations,
    _run_direct_sector_chat,
    _sector_progress_events,
)

try:
    from core.research import safe_extra
    from core.research.consensus import build_consensus
    from core.research.model_card import build_model_card
except Exception:  # optional research layer; chat must work without it
    safe_extra = None

router = APIRouter(tags=["Chat"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User query or macroeconomic research question")
    agent: str = Field(
        default="orchestrator",
        description=(
            "'orchestrator', 'finance_sector', 'external_sector', 'labour_sector', "
            "'capital_market_sector', 'monetary_sector', 'agriculture_sector', "
            "'real_sector' or 'services_sector'"
        ),
    )
    scenario_shock: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Optional sector query scope, e.g. city, crop, state")


@router.post("/api/v1/chat/stream", tags=["Chat"])
async def stream_chat(request: ChatMessageRequest):
    """Server-Sent Events (SSE) streaming chat endpoint with real-time agent updates and fluid token output."""
    async def event_generator():
        msg = request.message.strip()
        target = request.agent.lower()
        if target == "orchestrator" and is_direct_prices_query(msg):
            target = "prices_sector"

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

        elif target == "fiscal_sector":
            # Direct domain investigation of Fiscal & Public Finance sector
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'fiscal_sector', 'title': 'Targeting Fiscal & Public Finance Sector Agent', 'detail': 'Direct domain investigation of Union Budget, GST & Sovereign Debt.'})}\n\n"
            await asyncio.sleep(0.15)

            yield f"data: {json.dumps({'type': 'step', 'step': 2, 'agent': 'fiscal_sector', 'tool': 'get_union_fiscal_deficit', 'title': 'Invoking FastMCP Tool: get_union_fiscal_deficit', 'detail': 'Querying Union Budget receipts, capital expenditures & fiscal deficit (% of GDP)...'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 3, 'agent': 'fiscal_sector', 'tool': 'get_general_government_debt', 'title': 'Invoking FastMCP Tool: get_general_government_debt', 'detail': 'Querying IMF WEO sovereign gross debt & net lending/borrowing ratios (IND.GGXWDG_NGDP.A)...'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 4, 'agent': 'fiscal_sector', 'tool': 'get_gst_collections', 'title': 'Invoking FastMCP Tool: get_gst_collections', 'detail': 'Querying monthly gross GST revenues (CGST, SGST, IGST, Cess)...'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 5, 'agent': 'fiscal_sector', 'tool': 'get_mospi_product_taxes', 'title': 'Invoking FastMCP Tool: get_mospi_product_taxes', 'detail': 'Querying MoSPI eSankhyiki National Accounts (NAS) Net Taxes on Products...'})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'type': 'step', 'step': 6, 'agent': 'fiscal_sector', 'title': 'Executing LLM Econometric Reasoning', 'detail': 'Synthesizing fiscal consolidation, debt sustainability & tax buoyancy via Groq LLM...'})}\n\n"

            from fiscal_sector.agent import fiscal_agent_node
            node_result = await fiscal_agent_node({"query": msg})
            analysis_text = node_result.get("fiscal_analysis", "")
            raw_citations = node_result.get("citations", [])

            words = analysis_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                await asyncio.sleep(0.03)

            citations = [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in raw_citations
            ]

            done_payload = {
                "type": "done",
                "agent_routed": "Fiscal & Public Finance Sector Agent",
                "full_report": analysis_text,
                "citations": citations,
                "observations": node_result.get("collected_observations", []),
                "freshness": {"union_deficit": "live", "debt": "live", "gst": "live", "mospi": "live"},
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        elif target in _DIRECT_SECTOR_CHAT:
            sector_config = _DIRECT_SECTOR_CHAT[target]
            if target == "real_sector":
                selected_services = _select_services_deterministically(msg)
                selection_error = None
            elif target == "services_sector":
                selected_services = _select_services_services(msg)
                selection_error = None
            elif target == "agriculture_sector":
                selected_services = select_agriculture_tools(msg)
                selection_error = None
            elif target == "prices_sector":
                selected_services = set()
                selection_error = None
            else:
                selected_services, selection_error = await select_relevant_services_with_llm(
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

            sector_response = await _run_direct_sector_chat(
                target,
                msg,
                selected_services=selected_services,
                selection_error=selection_error,
                parameters=request.parameters,
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
                "answer": report_text,
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
            # Multi-agent orchestrator route: steps mirror the real A2A trace, not a script.
            conversation_id = new_id("conv")
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'agent': 'orchestrator', 'title': 'Orchestrator routing query', 'detail': 'Matching the question against registered Agent Cards.'})}\n\n"

            loop = asyncio.get_running_loop()
            graph_task = asyncio.ensure_future(loop.run_in_executor(
                None,
                lambda: macro_orchestrator_graph.invoke({
                    "query": msg,
                    "scenario_shock": request.scenario_shock,
                    "conversation_id": conversation_id,
                    "status": "started"
                })
            ))
            emitted: dict[str, str] = {}
            step_no = 2
            while True:
                finished = graph_task.done()
                for event in trace_step_events(trace_store.get_trace(conversation_id), emitted, step_no):
                    step_no = event["step"] + 1
                    yield f"data: {json.dumps(event)}\n\n"
                if finished:
                    break
                await asyncio.wait({graph_task}, timeout=0.4)
            try:
                final_state = graph_task.result()
            except Exception:
                logging.getLogger(__name__).exception("Orchestrator graph failed conversation_id=%s", conversation_id)
                failed_payload = {
                    "type": "done",
                    "agent_routed": "Macrograph Orchestrator (Multi-Sector)",
                    "full_report": (
                        "### Research Request Failed\n\nThe orchestrator could not complete this request. "
                        "No observations are available."
                    ),
                    "citations": [],
                    "status": "failed",
                    "a2a": a2a_summary({
                        "conversation_id": conversation_id,
                        "a2a_trace": trace_store.get_trace(conversation_id),
                        "status": "failed",
                    }),
                }
                yield f"data: {json.dumps(failed_payload)}\n\n"
                return

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
                "causal_paths": final_state.get("causal_paths", []),
                "scenario_result": final_state.get("scenario_result"),
                "confidence_score": final_state.get("confidence_score"),
                "a2a": a2a_summary(final_state),
            }
            if safe_extra is not None:
                for _key, _builder in (("consensus", build_consensus), ("model_card", build_model_card)):
                    _extra = safe_extra(_key, _builder, final_state)
                    if _extra is not None:
                        done_payload[_key] = _extra
                done_payload["live_baseline_ids"] = final_state.get("live_baseline_ids", [])
            yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/v1/chat", tags=["Chat"])
async def sync_chat(request: ChatMessageRequest) -> Dict[str, Any]:
    """Synchronous non-streaming chat endpoint."""
    target = request.agent.lower()
    if target == "orchestrator" and is_direct_prices_query(request.message):
        target = "prices_sector"
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
    elif target == "fiscal_sector":
        from fiscal_sector.agent import fiscal_agent_node
        node_result = await fiscal_agent_node({"query": request.message})
        raw_citations = node_result.get("citations", [])
        citations = [c.model_dump() if hasattr(c, "model_dump") else c for c in raw_citations]
        return {
            "status": "completed",
            "agent_routed": "Fiscal & Public Finance Sector Agent",
            "full_report": node_result.get("fiscal_analysis", ""),
            "citations": citations,
            "observations": node_result.get("collected_observations", []),
            "freshness": {"union_deficit": "live", "debt": "live", "gst": "live", "mospi": "live"},
        }
    elif target in _DIRECT_SECTOR_CHAT:
        return await _run_direct_sector_chat(target, request.message, parameters=request.parameters)
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
            "conversation_id": final_state.get("conversation_id"),
            "a2a_errors": final_state.get("a2a_errors", []),
            "citations": final_state.get("citations", []),
            "observations": final_state.get("collected_observations", []),
            "mermaid_diagram": final_state.get("mermaid_diagram", ""),
            "causal_paths": final_state.get("causal_paths", []),
            "scenario_result": final_state.get("scenario_result"),
        }
