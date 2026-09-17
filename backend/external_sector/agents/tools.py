from pydantic import BaseModel
from ..clients.external_data_client import ExternalDataClient
class ExternalToolInput(BaseModel): include_source_metadata: bool=True
class ExternalToolRegistry:
 def __init__(self,client=None):
  c=client or ExternalDataClient(); self._tools={"get_forex_reserves_snapshot":c.get_forex_reserves,"get_exchange_rate_snapshot":c.get_exchange_rate,"get_trade_balance_snapshot":c.get_trade_balance}
 def openai_functions(self):
  s=ExternalToolInput.model_json_schema(); return [{"type":"function","function":{"name":n,"description":n.replace("_"," ").title(),"parameters":s}} for n in self._tools]
 def invoke(self,name,payload=None):
  if name not in self._tools: raise KeyError(f"Unknown external tool: {name}")
  return self._tools[name]()
