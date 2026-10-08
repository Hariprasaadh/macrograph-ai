"""Platform-wide settings and model-agnostic environment configurations."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class PlatformSettings(BaseSettings):
    AGRICULTURE_MCP_SOURCES: dict[str, dict[str, Any]] = Field(default_factory=dict)
    AGRICULTURE_OGD_RESOURCES: dict[str, dict[str, Any]] = Field(default_factory=dict)
    AGRICULTURE_MCP_TIMEOUT: float = Field(default=90, gt=0, le=180)
    AGRICULTURE_USE_READYMADE_SOURCES: bool = True
    AGRICULTURE_MOSPI_URL: str = "https://mcp.mospi.gov.in/"
    AGRICULTURE_WEATHER_COMMAND: str = "node"
    AGRICULTURE_WEATHER_SCRIPT: str = ".mcp-sources/Indian-Weather-MCP-Server/build/index.js"
    DATA_GOV_IN_API_KEY: SecretStr = SecretStr("")
    CEDA_API_KEY: SecretStr = SecretStr("")

    # Base paths
    WORKSPACE_ROOT: Path = PROJECT_ROOT
    BACKEND_ROOT: Path = BACKEND_ROOT
    DATA_DIR: Path = BACKEND_ROOT / "real_sector" / "data"

    # API & Port Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Model-Agnostic LLM Configuration
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "groq")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY") or os.getenv("ORCH_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    FAST_MODEL: str = os.getenv("FAST_MODEL", "openai/gpt-oss-20b")
    REASONING_MODEL: str = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))

    # Browser origins allowed to call the API (the Vite dev proxy is same-origin and needs none).
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173"])

    # A2A protocol guards and transport defaults
    A2A_MAX_DEPTH: int = Field(default=5, ge=1, le=20)
    A2A_MAX_HOPS: int = Field(default=25, ge=1, le=500)
    A2A_REQUEST_TIMEOUT: float = Field(default=90.0, gt=0)
    A2A_PEER_TIMEOUT: float = Field(default=25.0, gt=0)
    A2A_MAX_RETRIES: int = Field(default=1, ge=0, le=5)
    A2A_TRACE_MAX_CONVERSATIONS: int = Field(default=500, ge=1)
    A2A_LLM_ROUTING: bool = True
    A2A_API_KEY: SecretStr = SecretStr("")
    # POST /a2a/v1/requests runs sector analyses on demand; with no key set it is refused unless this is true.
    A2A_ALLOW_ANONYMOUS_REQUESTS: bool = False
    A2A_DEFAULT_AGENTS: list[str] = Field(
        default_factory=lambda: ["real_sector", "prices_sector", "monetary_sector"]
    )

    # Persistent Knowledge Graph (Neo4j)
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    # Staged 8-Sector Endpoints
    REAL_SECTOR_URL: str = "http://127.0.0.1:8000/real-sector"
    PRICES_SECTOR_URL: str = "http://127.0.0.1:8000/prices-sector"
    MONETARY_SECTOR_URL: str = "http://127.0.0.1:8000/monetary-sector"
    FISCAL_SECTOR_URL: str = "http://127.0.0.1:8000/fiscal-sector"
    EXTERNAL_SECTOR_URL: str = "http://127.0.0.1:8000/external-sector"
    CAPITAL_MARKETS_URL: str = "http://127.0.0.1:8000/capital-markets"
    AGRICULTURE_SECTOR_URL: str = "http://127.0.0.1:8000/agriculture-sector"
    LABOUR_SECTOR_URL: str = "http://127.0.0.1:8000/labour-sector"

    model_config = {
        "env_file": (PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        "extra": "ignore",
    }


settings = PlatformSettings()
