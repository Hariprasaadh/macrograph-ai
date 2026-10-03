"""External Sector configuration loaded from environment."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class ExternalSectorSettings(BaseSettings):
    """External-sector-specific settings."""

    SERV_EXT_KEY: str | None = Field(
        default=None,
        validation_alias="SERV_EXT_KEY",
        description="Groq key dedicated to the External sector agent.",
    )
    EXTERNAL_LLM_MODEL: str = Field(default="openai/gpt-oss-120b")
    EXTERNAL_LLM_TEMPERATURE: float = Field(default=0.1)

    DBIE_CDN_BASE: str = Field(default="https://dbie.rbihub.in/data")
    DBIE_API_BASE: str = Field(default="https://data-api.dbie.rbihub.in/api/tables")
    DBIE_TIMEOUT: int = Field(default=20)

    EXTERNAL_DB_PATH: Path = Field(
        default=Path(__file__).parent / "data" / "external_sector.duckdb",
    )

    HTTP_CONNECT_TIMEOUT: float = Field(default=10.0)
    HTTP_READ_TIMEOUT: float = Field(default=20.0)

    model_config = {
        "env_file": str(Path(__file__).parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


external_settings = ExternalSectorSettings()
