from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from ..clients.labour_data_client import LabourDataClient

class LabourToolInput(BaseModel):
    include_source_metadata: bool = Field(default=True)

class LabourToolRegistry:
    def __init__(self, client: LabourDataClient | None = None) -> None:
        self.client = client or LabourDataClient()
        self._tools = {"get_epfo_payroll_snapshot": self.client.get_epfo_payroll,
                       "get_unemployment_snapshot": self.client.get_unemployment_rate}
    def openai_functions(self) -> list[dict[str, Any]]:
        schema = LabourToolInput.model_json_schema()
        return [{"type": "function", "function": {"name": n, "description": n.replace("_", " ").title(), "parameters": schema}} for n in self._tools]
    def invoke(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if name not in self._tools: raise KeyError(f"Unknown labour tool: {name}")
        return self._tools[name]()
