from fastapi import FastAPI,Request
from core.protocols.a2a import AgentCard,TaskManager,TaskRequest,TaskResponse
from ..agents.executor import AgricultureRuralAgentExecutor
from ..agents.tools import AgriToolRegistry
def create_app(client=None):
 app=FastAPI(title="Macrograph AI — Agriculture & Rural Sector",version="1.0.0"); ex=AgricultureRuralAgentExecutor(client); registry=AgriToolRegistry(client); manager=TaskManager()
 @app.get("/health")
 def health(): return {"status":"ok","service":"Agriculture & Rural Sector Agent"}
 @app.get("/.well-known/agent.json",response_model=AgentCard)
 def card(request:Request): return ex.get_agent_card(str(request.base_url).rstrip("/")+"/agriculture-sector")
 @app.post("/a2a/tasks",response_model=TaskResponse)
 async def task(req:TaskRequest): return await manager.run_task(ex,req)
 @app.get("/tools")
 def tools(): return registry.openai_functions()
 return app
app=create_app()
