"""Labour Sector configuration loaded from environment."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class LabourSectorSettings(BaseSettings):
    """Labour sector-specific settings."""

    LABOUR_LLM_KEY: str | None = Field(
        default=None,
        validation_alias="PRIC_LAB_KEY",
        description="Groq key shared with the Prices sector.",
    )
    LABOUR_LLM_MODEL: str = Field(default="openai/gpt-oss-120b")

    MOSPI_MCP_BASE: str = Field(default="https://mcp.mospi.gov.in/")
    MOSPI_TIMEOUT: int = Field(default=20)

    LABOUR_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "labour_sector.duckdb",
    )

    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


labour_settings = LabourSectorSettings()
