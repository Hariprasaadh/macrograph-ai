"""Platform-wide settings and environment configurations."""
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

    # LLM Settings (Groq Free Tier Optimized)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"  # Lightweight for routing / parsing
    GROQ_REASONING_MODEL: str = "llama-3.3-70b-versatile"  # Deep synthesis / reasoning
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 30

    # Sector URLs (for A2A routing)
    REAL_SECTOR_URL: str = "http://127.0.0.1:8000/real-sector"
    FINANCE_SECTOR_URL: str = "http://127.0.0.1:8000/finance-sector"
    CAPITAL_MARKETS_URL: str = "http://127.0.0.1:8000/capital-markets"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = PlatformSettings()
