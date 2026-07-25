"""LLM tool adapters for the independent sector agents.

An LLM integration can register ``openai_functions()`` directly, validate arguments
with the Pydantic schema below, then call ``invoke(name, payload)``.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from .agriculture_agent import AgricultureAgent
from .industry_agent import IndustryAgent
from .national_income_agent import NationalIncomeAgent
from .prices_agent import PricesAgent
from .response_models import SectorResponse


class SectorToolInput(BaseModel):
    """Shared validated input contract for a sector-data tool."""
    include_source_metadata: bool = Field(default=True, description="Include original workbook names, row counts, and freshness dates.")


class SectorToolRegistry:
    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline
        self._tools = {
            "get_agriculture_snapshot": ("Summarize foodgrain production, yield, and minimum-support-price signals from local official workbooks.", AgricultureAgent()),
            "get_industry_snapshot": ("Summarize IIP use-based growth and manufacturing-index signals from local official workbooks.", IndustryAgent()),
            "get_national_income_snapshot": ("Summarize quarterly real and nominal GDP plus gross fixed capital formation from local official workbooks.", NationalIncomeAgent()),
            "get_prices_snapshot": ("Summarize CPI, core CPI, WPI, and house-price signals from local official workbooks.", PricesAgent()),
        }

    def openai_functions(self) -> list[dict[str, Any]]:
        schema = SectorToolInput.model_json_schema()
        return [{"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
                for name, (description, _) in self._tools.items()]

    def invoke(self, name: str, payload: dict[str, Any] | None = None) -> SectorResponse:
        if name not in self._tools:
            raise KeyError(f"Unknown sector tool: {name}")
        options = SectorToolInput.model_validate(payload or {})
        response = self._tools[name][1].analyze(self.pipeline.load())
        return response if options.include_source_metadata else response.model_copy(update={"source_metadata": []})
