"""Agriculture routes mounted by the existing central FastAPI gateway."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastmcp import Client

from core.protocols.a2a import AgentCard, TaskManager, TaskRequest, TaskResponse
from core.protocols.mcp.client import MCPClientWrapper
from ..executor import AgricultureAgentExecutor
from ..mcp_server import OPERATIONS, mcp_server
from ..models import AgricultureQuery, AgricultureResult

mcp_http_app = mcp_server.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_http_app.lifespan(mcp_http_app):
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="Macrograph AI — Agriculture", version="1.0.0", lifespan=lifespan)
    executor, manager = AgricultureAgentExecutor(), TaskManager()
    app.mount("/mcp", mcp_http_app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Report service readiness, not upstream data availability."""
        return {"status": "ok", "service": "Agriculture Agent"}

    @app.get("/.well-known/agent.json", response_model=AgentCard)
    async def card(request: Request) -> AgentCard:
        """Expose the standard Agriculture Agent Card."""
        return executor.get_agent_card(str(request.base_url).rstrip("/"))

    @app.post("/a2a/tasks", response_model=TaskResponse)
    async def task(request: TaskRequest) -> TaskResponse:
        """Run a reasoning task through the shared A2A task manager."""
        return await manager.run_task(executor, request)

    @app.get("/tools")
    async def tools() -> list[dict[str, Any]]:
        """Discover only Agriculture-facing MCP schemas."""
        async with Client(mcp_server) as client:
            return [tool.model_dump(mode="json") for tool in await client.list_tools()]

    @app.post("/data/{tool}", response_model=AgricultureResult)
    async def data(tool: str, query: AgricultureQuery) -> AgricultureResult:
        """Invoke the Agriculture MCP data contract."""
        if tool not in OPERATIONS:
            raise HTTPException(status_code=404, detail="Unknown Agriculture tool")
        result = await MCPClientWrapper(mcp_server).call_tool_async(
            tool, {"query": query.model_dump(mode="json", exclude_none=True)}
        )
        return AgricultureResult.model_validate(result)

    return app


app = create_app()
