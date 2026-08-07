from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request

from ..clients.market_data_client import CapitalMarketsDataClient
from ..protocols.a2a_protocol import AgentCard, EventQueue, RequestContext, TaskRequest, TaskResponse, TaskStatus
from ..protocols.mcp_protocol import handle_mcp_rpc
from ..agents.executor import CapitalMarketsAgentExecutor
from ..agents.tools import SectorToolInput, SectorToolRegistry
from ..agents.response_models import CapitalMarketsResponse


def create_app(client: CapitalMarketsDataClient | None = None) -> FastAPI:
    application = FastAPI(title="Macrograph AI — Capital Markets Sector", version="1.0.0")
    active_client = client or CapitalMarketsDataClient()
    registry = SectorToolRegistry(active_client)
    executor = CapitalMarketsAgentExecutor(active_client)
    task_store: Dict[str, TaskResponse] = {}

    @application.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "Capital Markets Sector Agent",
            "version": "1.0.0",
        }

    @application.get("/.well-known/agent.json", response_model=AgentCard)
    @application.get("/capital-markets/agent-card", response_model=AgentCard)
    def agent_card(request: Request) -> AgentCard:
        base_url = str(request.base_url).rstrip("/")
        return executor.get_agent_card(base_url=f"{base_url}/capital-markets")

    @application.post("/a2a/tasks", response_model=TaskResponse)
    async def create_task(task_req: TaskRequest) -> TaskResponse:
        context = RequestContext(task_id=task_req.task_id, request=task_req)
        event_queue = EventQueue()
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
        context = RequestContext(task_id=task_id, request=TaskRequest(task_id=task_id, query=""))
        event_queue = EventQueue()
        success = await executor.cancel(context, event_queue)
        existing.status = TaskStatus.CANCELLED
        task_store[task_id] = existing
        return {"task_id": task_id, "status": TaskStatus.CANCELLED, "success": success}

    @application.post("/mcp")
    @application.post("/capital-markets/mcp")
    async def mcp_rpc_endpoint(request: Request) -> Dict[str, Any]:
        try:
            body = await request.json()
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {err}") from err
        return handle_mcp_rpc(body, registry)

    @application.get("/capital-markets/tools")
    def tool_definitions() -> list[dict[str, object]]:
        return registry.openai_functions()

    @application.post("/capital-markets/tools/{tool_name}", response_model=CapitalMarketsResponse)
    def invoke_tool(tool_name: str, payload: SectorToolInput) -> CapitalMarketsResponse:
        try:
            return registry.invoke(tool_name, payload.model_dump())
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return application



app = create_app()
