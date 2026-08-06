"""LLM tool adapters and registry for Finance Sector agents."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..clients.finance_data_client import FinanceDataClient
from ..protocols.mcp_protocol import MCPTool
from .finance_agent import (
    CPIInflationAgent,
    DebtToGDPAgent,
    ForexReservesAgent,
    GDPGrowthAgent,
    RepoRateAgent,
)
from .response_models import FinanceSectorResponse


class FinanceToolInput(BaseModel):
    """Shared input parameters for Finance Sector tools."""
    include_source_metadata: bool = Field(
        default=True,
        description="Include source attribution, dataset provider, and freshness dates."
    )
    prices: Optional[str] = Field(
        default="Constant",
        description="Price type for GDP calculations: 'Constant' or 'Current'."
    )


class FinanceToolRegistry:
    def __init__(self, client: Optional[FinanceDataClient] = None) -> None:
        self.client = client or FinanceDataClient()
        self._tools = {
            "get_gdp_growth_snapshot": (
                "Fetch quarterly and annual GDP growth rates from official MoSPI Power BI data service.",
                GDPGrowthAgent(self.client)
            ),
            "get_cpi_inflation_snapshot": (
                "Fetch headline CPI inflation rate YoY metrics for price stability analysis.",
                CPIInflationAgent(self.client)
            ),
            "get_repo_rate_snapshot": (
                "Fetch Reserve Bank of India (RBI) policy Repo Rate, SDF, MSF, and interest rate stance.",
                RepoRateAgent(self.client)
            ),
            "get_debt_to_gdp_snapshot": (
                "Fetch General Government Debt-to-GDP ratio for fiscal sustainability assessment.",
                DebtToGDPAgent(self.client)
            ),
            "get_forex_reserves_snapshot": (
                "Fetch total Foreign Exchange Reserves in USD for external liquidity buffer assessment.",
                ForexReservesAgent(self.client)
            ),
        }

    def openai_functions(self) -> List[Dict[str, Any]]:
        schema = FinanceToolInput.model_json_schema()
        return [
            {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
            for name, (description, _) in self._tools.items()
        ]

    def mcp_tools(self) -> List[MCPTool]:
        """Returns standard Model Context Protocol (MCP) tool specifications."""
        input_schema = FinanceToolInput.model_json_schema()
        output_schema = FinanceSectorResponse.model_json_schema()
        return [
            MCPTool(
                name=name,
                description=description,
                inputSchema=input_schema,
                outputSchema=output_schema
            )
            for name, (description, _) in self._tools.items()
        ]

    def invoke(self, name: str, payload: Optional[Dict[str, Any]] = None) -> FinanceSectorResponse:
        if name not in self._tools:
            raise KeyError(f"Unknown Finance tool: {name}")
        options = FinanceToolInput.model_validate(payload or {})
        response = self._tools[name][1].analyze(options=options)
        return response if options.include_source_metadata else response.model_copy(update={"source_metadata": []})
