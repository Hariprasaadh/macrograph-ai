"""Capital Markets Sector configuration loaded from environment."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class CapitalMarketSectorSettings(BaseSettings):
    """Capital Markets sector-specific settings."""

    CAPITAL_LLM_KEY: str | None = Field(
        default=None,
        validation_alias="CAP_MON_KEY",
        description="Groq key shared by the Capital Markets and Monetary specialist agents.",
    )
    CAPITAL_LLM_MODEL: str = Field(default="openai/gpt-oss-120b")

    NSE_BHAVCOPY_MCP: str = Field(default="https://mcp.nseindia.in/bhavcopy/cm/mcp")
    NSE_CMMKT_MCP: str = Field(default="https://mcp.nseindia.in/cmmkt/mcp")
    RBI_DBIE_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables",
        description="RBI DBIE public tables API for Government Security tenor yields.",
    )
    YAHOO_FINANCE_CHART_URL: str = Field(
        default="https://query1.finance.yahoo.com/v8/finance/chart",
        description="Yahoo Finance chart endpoint used for provider-snapshot market observations.",
    )

    CAPITAL_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "capital_market_sector.duckdb",
    )

    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


capital_settings = CapitalMarketSectorSettings()
