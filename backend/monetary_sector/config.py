"""Monetary Sector configuration loaded from environment.

All secrets are sourced from .env via PlatformSettings.
No hardcoded credentials ever.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class MonetarySectorSettings(BaseSettings):
    """Monetary-sector-specific settings."""

    # API key for the monetary sector LLM calls
    MONETARY_LLM_KEY: str | None = Field(
        default=None,
        validation_alias="CAP_MON_KEY",
        description="Groq key shared by the Capital Markets and Monetary specialist agents.",
    )

    # LLM model for this sector
    MONETARY_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="LLM model used by the monetary sector agent",
    )
    MONETARY_LLM_TEMPERATURE: float = Field(default=0.1)
    MONETARY_LLM_TIMEOUT: int = Field(default=60)
    MONETARY_LLM_MAX_RETRIES: int = Field(default=3)
    MONETARY_LLM_MAX_TOKENS: int = Field(
        default=3500,
        description="Reasoning output budget for the monetary sector agent (longer, detailed responses).",
    )

    # RBI DBIE endpoints
    DBIE_CDN_BASE: str = Field(
        default="https://dbie.rbihub.in/data",
        description="RBI DBIE CloudFront CDN — static JSON mirror",
    )
    DBIE_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables",
        description="RBI DBIE Postgres REST API",
    )
    DBIE_TIMEOUT: int = Field(default=20)
    MONETARY_MCP_TIMEOUT: int = Field(
        default=90,
        description="Per-request budget for MCP stdio transport (covers npx/uvx cold starts).",
    )

    # Local DuckDB path (sector-dedicated, isolated from other sectors)
    MONETARY_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "monetary_sector.duckdb",
        description="Path to the monetary sector's dedicated DuckDB database",
    )

    # HTTP client settings
    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


monetary_settings = MonetarySectorSettings()
