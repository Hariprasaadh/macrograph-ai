"""Platform-wide settings and model-agnostic environment configurations."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class PlatformSettings(BaseSettings):
    # Base paths
    WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[2]
    BACKEND_ROOT: Path = Path(__file__).resolve().parents[1]
    DATA_DIR: Path = BACKEND_ROOT / "real_sector" / "data"

    # API & Port Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Model-Agnostic LLM Configuration
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "groq")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    FAST_MODEL: str = os.getenv("FAST_MODEL", "llama-3.1-8b-instant")
    REASONING_MODEL: str = os.getenv("REASONING_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))

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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = PlatformSettings()
