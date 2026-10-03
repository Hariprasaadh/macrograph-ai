"""Real Sector configuration loaded from environment."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class RealSectorSettings(BaseSettings):
    """Real Sector & Industrial Output configuration."""

    AGR_REAL_KEY: str | None = Field(
        default=None,
        description="Groq key shared by the Agriculture and Real Sector specialist agents.",
    )
    REAL_LLM_KEY: str | None = Field(
        default=None,
        validation_alias="AGR_REAL_KEY",
        description="Groq key shared by the Agriculture and Real Sector specialist agents.",
    )
    REAL_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        validation_alias="REASONING_MODEL",
        description="LLM reasoning model for Real Sector.",
    )
    REAL_LLM_TEMPERATURE: float = Field(default=0.1)

    MOSPI_IIP_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables/real_sector",
        description="Base API endpoint for MoSPI IIP series.",
    )
    DPIIT_ICI_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables/real_sector",
        description="Base API endpoint for DPIIT Eight Core Industries index.",
    )
    RBI_DBIE_API_BASE: str = Field(
        default="https://data-api.dbie.rbihub.in/api/tables/real_sector",
        description="Base API endpoint for RBI DBIE GVA and OBICUS tables.",
    )
    YAHOO_FINANCE_CHART_URL: str = Field(
        default="https://query1.finance.yahoo.com/v8/finance/chart",
        description="Yahoo Finance chart endpoint used for infrastructure market snapshot.",
    )

    REAL_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "real_sector.duckdb",
    )

    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)
    DBIE_TIMEOUT: float = Field(default=15.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


real_settings = RealSectorSettings()
