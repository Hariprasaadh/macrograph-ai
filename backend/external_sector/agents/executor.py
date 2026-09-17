from datetime import datetime,timezone
from core.protocols.a2a import *
from ..clients.external_data_client import ExternalDataClient
from .tools import ExternalToolInput,ExternalToolRegistry
class ExternalSectorAgentExecutor(AgentExecutor):
 def __init__(self,client=None): self.registry=ExternalToolRegistry(client or ExternalDataClient())
 @classmethod
 def get_agent_card(cls,base_url="http://localhost:8000/external-sector"):
  s=ExternalToolInput.model_json_schema(); return AgentCard(name="External Sector Macroeconomic Agent",description="Indian foreign exchange, reserves, and trade-balance intelligence.",url=base_url,capabilities=["external","forex","exchange_rate","trade"],skills=[AgentSkill(id=i,name=i.replace("_"," ").title(),description="Verified external-sector indicator analysis.",tags=["external","forex"],input_schema=s) for i in ["forex_reserves_analysis","exchange_rate_analysis","trade_balance_analysis"]])
 def _select(self,q,skills):
  names=["get_forex_reserves_snapshot","get_exchange_rate_snapshot","get_trade_balance_snapshot"]
  if skills:
   ids=["forex_reserves_analysis","exchange_rate_analysis","trade_balance_analysis"]; return [names[ids.index(s)] for s in skills if s in ids] or names
  if "exchange" in q or "usd" in q or "rupee" in q:return [names[1]]
  if "trade" in q or "deficit" in q:return [names[2]]
  if "reserve" in q or "forex" in q:return [names[0]]
  return names
 async def execute(self,context,event_queue):
  await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.WORKING,message="Fetching external-sector indicators.")); results={n:self.registry.invoke(n,context.request.parameters) for n in self._select(context.request.query.lower(),context.request.skills_required)}; narrative="# External Sector Report\n\n"+"\n".join(f"- **{v.get('indicator',k)}**: {v.get('latest_value','N/A')} ({v.get('data_status','error')})" for k,v in results.items()); arts=[A2AArtifact(name="External Indicators",type="json",content=results),A2AArtifact(name="External Report",type="markdown",content=narrative)]
  for a in arts: await event_queue.emit(TaskArtifactUpdateEvent(task_id=context.task_id,artifact=a))
  await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.COMPLETED,message="External analysis completed.")); return TaskResponse(task_id=context.task_id,status=TaskState.COMPLETED,messages=[A2AMessage(role="agent",parts=[A2AMessagePart(kind="markdown",content=narrative),A2AMessagePart(kind="json",content=results)])],artifacts=arts,updated_at=datetime.now(timezone.utc).isoformat())
 async def cancel(self,context,event_queue): await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.CANCELLED,message="Cancelled.")); return True
