from datetime import datetime, timezone
from core.protocols.a2a import A2AArtifact,A2AMessage,A2AMessagePart,AgentCard,AgentExecutor,AgentSkill,TaskResponse,TaskState,TaskStatusUpdateEvent,TaskArtifactUpdateEvent
from ..clients.agri_data_client import AgricultureDataClient
from .tools import AgriToolInput,AgriToolRegistry
class AgricultureRuralAgentExecutor(AgentExecutor):
 def __init__(self,client=None): self.registry=AgriToolRegistry(client or AgricultureDataClient())
 @classmethod
 def get_agent_card(cls,base_url="http://localhost:8000/agriculture-sector"):
  s=AgriToolInput.model_json_schema(); return AgentCard(name="Agriculture & Rural Macroeconomic Agent",description="Indian agriculture, MSP, and foodgrain intelligence.",url=base_url,capabilities=["agriculture","rural","foodgrain","msp"],skills=[AgentSkill(id=i,name=i.replace("_"," ").title(),description="Verified agriculture and rural indicator analysis.",tags=["agriculture","rural"],input_schema=s) for i in ["foodgrain_production_analysis","msp_growth_analysis"]])
 def _select(self,q,skills):
  names=["get_foodgrain_production_snapshot","get_msp_growth_snapshot"]
  if skills:
   ids=["foodgrain_production_analysis","msp_growth_analysis"]; return [names[ids.index(s)] for s in skills if s in ids] or names
  if "msp" in q:return [names[1]]
  if "foodgrain" in q or "crop" in q:return [names[0]]
  return names
 async def execute(self,context,event_queue):
  await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.WORKING,message="Fetching agriculture indicators.")); results={n:self.registry.invoke(n,context.request.parameters) for n in self._select(context.request.query.lower(),context.request.skills_required)}; narrative="# Agriculture & Rural Report\n\n"+"\n".join(f"- **{v.get('indicator',k)}**: {v.get('latest_value','N/A')} ({v.get('data_status','error')})" for k,v in results.items()); arts=[A2AArtifact(name="Agriculture Indicators",type="json",content=results),A2AArtifact(name="Agriculture Report",type="markdown",content=narrative)]
  for a in arts: await event_queue.emit(TaskArtifactUpdateEvent(task_id=context.task_id,artifact=a))
  await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.COMPLETED,message="Agriculture analysis completed.")); return TaskResponse(task_id=context.task_id,status=TaskState.COMPLETED,messages=[A2AMessage(role="agent",parts=[A2AMessagePart(kind="markdown",content=narrative),A2AMessagePart(kind="json",content=results)])],artifacts=arts,updated_at=datetime.now(timezone.utc).isoformat())
 async def cancel(self,context,event_queue): await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id,status=TaskState.CANCELLED,message="Cancelled.")); return True
