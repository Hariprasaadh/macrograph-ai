from fastapi import FastAPI, HTTPException, Request
from core.protocols.a2a import AgentCard, TaskManager, TaskRequest, TaskResponse
from ..agents.executor import LabourEmploymentAgentExecutor
from ..agents.tools import LabourToolRegistry
from ..clients.labour_data_client import LabourDataClient

def create_app(client=None):
    app = FastAPI(title="Macrograph AI — Labour & Employment Sector", version="1.0.0")
    active = client or LabourDataClient(); executor = LabourEmploymentAgentExecutor(active); registry = LabourToolRegistry(active); manager = TaskManager()
    @app.get("/health")
    def health(): return {"status": "ok", "service": "Labour & Employment Sector Agent"}
    @app.get("/.well-known/agent.json", response_model=AgentCard)
    def card(request: Request): return executor.get_agent_card(str(request.base_url).rstrip("/") + "/labour-sector")
    @app.post("/a2a/tasks", response_model=TaskResponse)
    async def task(req: TaskRequest): return await manager.run_task(executor, req)
    @app.get("/tools")
    def tools(): return registry.openai_functions()
    @app.post("/tools/{name}")
    def invoke(name: str, payload: dict):
        try: return registry.invoke(name, payload)
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc
    return app
app = create_app()
