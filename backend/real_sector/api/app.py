"""FastAPI surface for Real Sector Agent — A2A Protocol and FastMCP Tools integration."""
from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from core.protocols.a2a import (
    AgentCard,
    TaskManager,
    TaskRequest,
    TaskResponse,
    TaskState,
    task_event_stream,
)
from ..agents.executor import RealSectorAgentExecutor
from ..agents.response_models import SectorResponse
from ..agents.tools import SectorToolInput, SectorToolRegistry
from ..services.pipeline import RealSectorPipeline
from ..mcp_server import mcp_server


def create_app(pipeline: RealSectorPipeline | None = None) -> FastAPI:
    application = FastAPI(
        title="Macrograph AI — Real Sector Agent (A2A & FastMCP)",
        version="1.0.0",
        description="A2A Protocol & FastMCP Compliant Real Sector Macroeconomic Intelligence Agent"
    )
    active_pipeline = pipeline or RealSectorPipeline()
    registry = SectorToolRegistry(active_pipeline)
    executor = RealSectorAgentExecutor(active_pipeline)
    task_manager = TaskManager()

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
        return await task_manager.run_task(executor, task_req, background=False)

    @application.get("/a2a/tasks/{task_id}", response_model=TaskResponse)
    def get_task(task_id: str) -> TaskResponse:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        return task

    @application.get("/a2a/tasks/{task_id}/events")
    async def task_events(task_id: str) -> EventSourceResponse:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        event_queue = task_manager.get_event_queue(task_id)
        return EventSourceResponse(task_event_stream(event_queue, task_id))

    @application.post("/a2a/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        success = await task_manager.cancel_task(task_id, executor)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        return {"task_id": task_id, "status": TaskState.CANCELLED, "success": True}

    # --- FastMCP Tool Endpoints ---

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
