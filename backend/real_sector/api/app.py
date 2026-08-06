"""FastAPI surface for Real Sector Agent — A2A Protocol and MCP Tools integration.

Provides:
- A2A Agent Card Discovery: /.well-known/agent.json & /real-sector/agent-card
- A2A Task Management API: /a2a/tasks, /a2a/tasks/{task_id}, /a2a/tasks/{task_id}/cancel
- MCP (Model Context Protocol) JSON-RPC 2.0 Endpoint: /mcp & /real-sector/mcp
- Legacy tool compatibility: /real-sector/tools and /real-sector/tools/{tool_name}
"""
from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request

from ..agents.executor import RealSectorAgentExecutor
from ..agents.response_models import SectorResponse
from ..agents.tools import SectorToolInput, SectorToolRegistry
from ..protocols.a2a_protocol import (
    AgentCard,
    EventQueue,
    RequestContext,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)
from ..protocols.mcp_protocol import handle_mcp_rpc
from ..services.pipeline import RealSectorPipeline


def create_app(pipeline: RealSectorPipeline | None = None) -> FastAPI:
    application = FastAPI(
        title="Macrograph AI — Real Sector Agent (A2A & MCP)",
        version="1.0.0",
        description="A2A Protocol & MCP Compliant Real Sector Macroeconomic Intelligence Agent"
    )
    active_pipeline = pipeline or RealSectorPipeline()
    registry = SectorToolRegistry(active_pipeline)
    executor = RealSectorAgentExecutor(active_pipeline)

    # In-memory store for active and completed A2A tasks
    task_store: Dict[str, TaskResponse] = {}

    @application.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", **active_pipeline.status()}

    # --- A2A Protocol Discovery ---

    @application.get("/.well-known/agent.json", response_model=AgentCard)
    @application.get("/real-sector/agent-card", response_model=AgentCard)
    def agent_card(request: Request) -> AgentCard:
        base_url = str(request.base_url).rstrip("/")
        return executor.get_agent_card(base_url=f"{base_url}/real-sector")

    # --- A2A Protocol Task Endpoints ---

    @application.post("/a2a/tasks", response_model=TaskResponse)
    async def create_task(task_req: TaskRequest) -> TaskResponse:
        context = RequestContext(task_id=task_req.task_id, request=task_req)
        event_queue = EventQueue()
        
        # Execute task synchronously through the executor
        response = await executor.execute(context, event_queue)
        task_store[response.task_id] = response
        return response

    @application.get("/a2a/tasks/{task_id}", response_model=TaskResponse)
    def get_task(task_id: str) -> TaskResponse:
        if task_id not in task_store:
            raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        return task_store[task_id]

    @application.post("/a2a/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        if task_id not in task_store:
            raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        
        existing = task_store[task_id]
        context = RequestContext(
            task_id=task_id,
            request=TaskRequest(task_id=task_id, query="")
        )
        event_queue = EventQueue()
        success = await executor.cancel(context, event_queue)
        
        existing.status = TaskStatus.CANCELLED
        task_store[task_id] = existing
        return {"task_id": task_id, "status": TaskStatus.CANCELLED, "success": success}

    # --- MCP Protocol JSON-RPC Endpoint ---

    @application.post("/mcp")
    @application.post("/real-sector/mcp")
    async def mcp_rpc_endpoint(request: Request) -> Dict[str, Any]:
        try:
            body = await request.json()
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {err}") from err
        
        return handle_mcp_rpc(body, registry)

    # --- Legacy Tool Endpoints ---

    @application.get("/real-sector/tools")
    def tool_definitions() -> list[dict[str, object]]:
        return registry.openai_functions()

    @application.post("/real-sector/tools/{tool_name}", response_model=SectorResponse)
    def invoke_tool(tool_name: str, payload: SectorToolInput) -> SectorResponse:
        try:
            return registry.invoke(tool_name, payload.model_dump())
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/real-sector/refresh")
    def refresh() -> dict[str, object]:
        tables = active_pipeline.refresh()
        return {"status": "refreshed", "tables": {name: len(table) for name, table in tables.items()}}

    return application


app = create_app()
