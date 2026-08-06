"""FastAPI surface for Finance Sector Agent — A2A Protocol & MCP Tools Integration."""
from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request

from ..agents.executor import FinanceSectorAgentExecutor
from ..agents.response_models import FinanceSectorResponse
from ..agents.tools import FinanceToolInput, FinanceToolRegistry
from ..clients.finance_data_client import FinanceDataClient
from ..protocols.a2a_protocol import (
    AgentCard,
    EventQueue,
    RequestContext,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)
from ..protocols.mcp_protocol import handle_mcp_rpc


def create_app(client: FinanceDataClient | None = None) -> FastAPI:
    application = FastAPI(
        title="Macrograph AI — Finance Sector Agent (A2A & MCP)",
        version="1.0.0",
        description="A2A Protocol & MCP Compliant Finance Sector Macroeconomic Intelligence Agent"
    )
    active_client = client or FinanceDataClient()
    registry = FinanceToolRegistry(active_client)
    executor = FinanceSectorAgentExecutor(active_client)

    task_store: Dict[str, TaskResponse] = {}

    @application.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "agent": "Finance Sector Agent", "version": "1.0.0"}

    # --- A2A Protocol Discovery ---

    @application.get("/.well-known/agent.json", response_model=AgentCard)
    @application.get("/finance-sector/agent-card", response_model=AgentCard)
    def agent_card(request: Request) -> AgentCard:
        base_url = str(request.base_url).rstrip("/")
        return executor.get_agent_card(base_url=f"{base_url}/finance-sector")

    # --- A2A Protocol Task Endpoints ---

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
    @application.post("/finance-sector/mcp")
    async def mcp_rpc_endpoint(request: Request) -> Dict[str, Any]:
        try:
            body = await request.json()
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {err}") from err
        
        return handle_mcp_rpc(body, registry)

    # --- Tool Endpoints ---

    @application.get("/finance-sector/tools")
    def tool_definitions() -> list[dict[str, object]]:
        return registry.openai_functions()

    @application.post("/finance-sector/tools/{tool_name}", response_model=FinanceSectorResponse)
    def invoke_tool(tool_name: str, payload: FinanceToolInput) -> FinanceSectorResponse:
        try:
            return registry.invoke(tool_name, payload.model_dump())
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return application


app = create_app()
