"""Services Sector configuration loaded from environment.

All secrets are sourced from .env via sector settings.
No hardcoded credentials ever.
"""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class ServicesSectorSettings(BaseSettings):
    """Services-sector-specific settings."""

    # Groq key shared with the external sector (SERV_EXT_KEY from .env).
    # Naming follows the platform 6-key convention (AGR_REAL, FIN_FIS,
    # CAP_MON, ORCH, PRIC_LAB, SERV_EXT) — see core/sector_reasoning.py.
    SERV_EXT_KEY: str | None = Field(
        default=None,
        validation_alias="SERV_EXT_KEY",
        description="Groq API key for services sector agent",
    )

    # Tavily API key for real-time services news & intelligence
    TVLY_KEY_1: str | None = Field(
        default=None,
        validation_alias="TVLY_KEY_1",
        description="Tavily API key for search enrichment",
    )

    # LLM model for this sector
    SERVICES_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="LLM model used by the services sector agent",
    )
    SERVICES_LLM_TEMPERATURE: float = Field(default=0.1)
    # Output budget per reasoning call. The sector report spans 7 Markdown
    # sections with per-metric explanations (~2500+ tokens); a small cap
    # truncates the answer mid-section (finish_reason='length').
    SERVICES_LLM_MAX_TOKENS: int = Field(default=4000)
    SERVICES_LLM_MAX_CONTINUATIONS: int = Field(
        default=2,
        description="Bounded follow-up calls when a response stops at the token cap",
    )
    SERVICES_LLM_TIMEOUT: int = Field(default=60)
    SERVICES_LLM_MAX_RETRIES: int = Field(default=3)

    # MoSPI e-Sankhyiki MCP endpoint (public, no auth)
    MOSPI_MCP_URL: str = Field(
        default="https://mcp.mospi.gov.in/",
        description="Official MoSPI e-Sankhyiki MCP server endpoint",
    )
    MOSPI_API_TIMEOUT: int = Field(default=30)

    # Local DuckDB path (sector-dedicated, isolated from other sectors)
    SERVICES_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "services_sector.duckdb",
        description="Path to the services sector's dedicated DuckDB database",
    )

    # HTTP client settings
    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


services_settings = ServicesSectorSettings()
