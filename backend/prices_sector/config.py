"""Prices-only settings; secrets are loaded without copying them into code."""
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND = Path(__file__).resolve().parents[1]


class PricesSettings(BaseSettings):
    PRICES_MOSPI_URL: str = 'https://mcp.mospi.gov.in/'
    PRICES_IMF_URL: str = 'https://imf.caseyjhand.com/mcp'
    PRICES_MCP_TIMEOUT: float = Field(default=45, gt=0, le=120)
    GROQ_API_KEY: SecretStr = SecretStr('')
    TVLY_KEY_3: SecretStr = SecretStr('')
    PRIC_LAB_KEY: SecretStr = SecretStr('')
    REASONING_MODEL: str = 'openai/gpt-oss-120b'
    PRICES_WEB_SEARCH_ENABLED: bool = True
    PRICES_MARKET_ENABLED: bool = True
    PRICES_NEWS_ENABLED: bool = True
    PRICES_LLM_TEMPERATURE: float = 0.2
    PRICES_LLM_MAX_TOKENS: int = 2500
    PRICES_SEARCH_TIMEOUT: float = Field(default=12, gt=0, le=30)
    PRICES_SYNTHESIS_TIMEOUT: float = Field(default=50, gt=0, le=120)
    PRICES_SEARCH_MAX_RESULTS: int = Field(default=4, ge=1, le=8)

    model_config = SettingsConfigDict(env_file=(BACKEND.parent / '.env', BACKEND / '.env'), extra='ignore')


prices_settings = PricesSettings()
