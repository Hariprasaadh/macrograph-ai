from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from .earnings_agent import EarningsAgent
from .equity_agent import EquityAgent
from .mf_flows_agent import MFFlowsAgent
from .primary_market_agent import PrimaryMarketAgent
from .response_models import CapitalMarketsResponse
from .vix_agent import VixAgent
from ..clients.market_data_client import CapitalMarketsDataClient
from ..protocols.mcp_protocol import MCPTool


class SectorToolInput(BaseModel):
    include_source_metadata: bool = Field(
        default=True,
        description="Include original source metadata and freshness dates.",
    )
    start_date: str | None = Field(default=None, description="Optional ISO start date filter.")
    end_date: str | None = Field(default=None, description="Optional ISO end date filter.")


class SectorToolRegistry:
    def __init__(self, client: CapitalMarketsDataClient | None = None) -> None:
        self.client = client or CapitalMarketsDataClient()
        self._tools = {
            "get_equity_snapshot": ("Summarize NIFTY 50 and SENSEX levels and momentum signals.", EquityAgent()),
            "get_vix_snapshot": ("Summarize India VIX levels and volatility regime signals.", VixAgent()),
            "get_earnings_snapshot": ("Summarize corporate earnings, EPS, and PAT indicators.", EarningsAgent()),
            "get_primary_market_snapshot": ("Summarize IPO and debt issuance activity in the primary market.", PrimaryMarketAgent()),
            "get_mf_flows_snapshot": ("Summarize mutual fund equity flows and DII net purchase activity.", MFFlowsAgent()),
        }

    def _load_data(self) -> dict[str, Any]:
        return {
            "nifty_50": self.client.get_nifty_50(),
            "sensex": self.client.get_sensex(),
            "india_vix": self.client.get_india_vix(),
            "corporate_earnings": self.client.get_corporate_earnings(),
            "primary_market": self.client.get_primary_market_activity(),
            "mf_flows": self.client.get_mf_flows(),
        }

    def openai_functions(self) -> list[dict[str, Any]]:
        schema = SectorToolInput.model_json_schema()
        return [
            {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
            for name, (description, _) in self._tools.items()
        ]

    def mcp_tools(self) -> list[MCPTool]:
        input_schema = SectorToolInput.model_json_schema()
        output_schema = CapitalMarketsResponse.model_json_schema()
        return [
            MCPTool(name=name, description=description, inputSchema=input_schema, outputSchema=output_schema)
            for name, (description, _) in self._tools.items()
        ]

    def invoke(self, name: str, payload: dict[str, Any] | None = None) -> CapitalMarketsResponse:
        if name not in self._tools:
            raise KeyError(f"Unknown capital markets tool: {name}")
        options = SectorToolInput.model_validate(payload or {})
        data = self._load_data()
        response = self._tools[name][1].analyze(data, options=options)
        return response if options.include_source_metadata else response.model_copy(update={"source_metadata": []})
