"""Finance Sector configuration loaded from environment.

All secrets are sourced from .env via PlatformSettings.
No hardcoded credentials ever.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class FinanceSectorSettings(BaseSettings):
    """Finance-sector-specific settings."""

    # API key for the finance sector LLM calls (FIN_FIS_KEY from .env)
    FIN_FIS_KEY: str | None = Field(default=None, description="Groq API key for finance sector agent")

    # Tavily API key for real-time finance news & intelligence
    TVLY_KEY_1: str | None = Field(default=None, description="Tavily API key for search enrichment")

    # LLM model for this sector
    FINANCE_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="LLM model used by the finance sector agent",
    )
    FINANCE_LLM_TEMPERATURE: float = Field(default=0.1)
    FINANCE_LLM_TIMEOUT: int = Field(default=60)
    FINANCE_LLM_MAX_RETRIES: int = Field(default=3)

    # RBI DBIE endpoints (public, no auth)
    DBIE_CDN_BASE: str = Field(
        default="https://dbie.rbihub.in/data",
        description="RBI DBIE CloudFront CDN — static JSON mirror",
    )
    DBIE_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables",
        description="RBI DBIE Postgres REST API",
    )
    DBIE_TIMEOUT: int = Field(default=20)

    # Local DuckDB path (sector-dedicated, isolated from other sectors)
    FINANCE_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "finance_sector.duckdb",
        description="Path to the finance sector's dedicated DuckDB database",
    )

    # HTTP client settings
    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


finance_settings = FinanceSectorSettings()
