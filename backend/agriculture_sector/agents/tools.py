from pydantic import BaseModel
from ..clients.agri_data_client import AgricultureDataClient
class AgriToolInput(BaseModel): include_source_metadata: bool = True
class AgriToolRegistry:
    def __init__(self,client=None):
        c=client or AgricultureDataClient(); self._tools={"get_foodgrain_production_snapshot":c.get_foodgrain_production,"get_msp_growth_snapshot":c.get_msp_growth}
    def openai_functions(self):
        schema=AgriToolInput.model_json_schema(); return [{"type":"function","function":{"name":n,"description":n.replace("_"," ").title(),"parameters":schema}} for n in self._tools]
    def invoke(self,name,payload=None):
        if name not in self._tools: raise KeyError(f"Unknown agriculture tool: {name}")
        return self._tools[name]()
