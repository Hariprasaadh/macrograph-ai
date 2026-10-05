"""Fiscal Sector configuration loaded from environment.

All secrets and endpoints are sourced from .env via Pydantic BaseSettings.
No hardcoded credentials or API keys ever.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class FiscalSectorSettings(BaseSettings):
    """Fiscal & Public Finance sector-specific settings."""

    # API key for the fiscal sector LLM calls (FIN_FIS_KEY from .env)
    FIN_FIS_KEY: str | None = Field(default=None, description="Groq API key for fiscal sector agent")

    # Tavily API key for real-time fiscal news & PIB releases
    TVLY_KEY_1: str | None = Field(default=None, description="Tavily API key for search enrichment")
    TVLY_KEY_2: str | None = Field(default=None, description="Secondary Tavily key")
    TVLY_KEY_3: str | None = Field(default=None, description="Tertiary Tavily key")

    # LLM models for this sector
    FISCAL_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        validation_alias="REASONING_MODEL",
        description="LLM model used by the fiscal sector agent",
    )
    FAST_MODEL: str = Field(
        default="openai/gpt-oss-20b",
        validation_alias="FAST_MODEL",
        description="Fast LLM model used for high-throughput or fallback reasoning",
    )
    FISCAL_LLM_TEMPERATURE: float = Field(default=0.1)
    FISCAL_LLM_MAX_TOKENS: int = Field(default=1500)
    FISCAL_LLM_TIMEOUT: int = Field(default=60)
    FISCAL_LLM_MAX_RETRIES: int = Field(default=3)

    # MoSPI eSankhyiki MCP server endpoint (official Government of India statistics)
    MOSPI_MCP_URL: str = Field(
        default="https://mcp.mospi.gov.in/",
        description="Official MoSPI FastMCP server endpoint",
    )

    # IMF MCP server endpoint (General Government Gross Debt & Fiscal Balance)
    IMF_MCP_URL: str = Field(
        default="https://imf.caseyjhand.com/mcp",
        description="IMF SDMX 3.0 MCP Server endpoint",
    )

    # Direct IMF SDMX API base
    IMF_SDMX_BASE: str = Field(
        default="https://api.imf.org/external/sdmx/3.0",
        description="Direct IMF SDMX 3.0 REST endpoint",
    )

    # RBI DBIE endpoints (public, no auth)
    DBIE_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables",
        description="RBI DBIE Postgres REST API for public finance tables",
    )
    DBIE_TIMEOUT: int = Field(default=20)

    # Local DuckDB path (sector-dedicated, isolated from other sectors)
    FISCAL_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "fiscal_sector.duckdb",
        description="Path to the fiscal sector's dedicated DuckDB database",
    )

    # HTTP client settings
    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=25.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


fiscal_settings = FiscalSectorSettings()
