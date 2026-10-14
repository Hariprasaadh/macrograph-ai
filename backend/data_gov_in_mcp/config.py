"""
Configuration management for data.gov.in MCP server
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration settings for the MCP server"""

    # API Configuration
    api_key: Optional[str] = None
    base_url: str = "https://api.data.gov.in"
    timeout: int = 30

    # Rate Limiting
    rate_limit_calls: int = 100
    rate_limit_period: int = 60  # seconds

    # Caching
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    cache_max_size: int = 1000

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0

    # Pagination
    default_limit: int = 10
    max_limit: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        return cls(
            api_key=os.getenv("DATA_GOV_IN_API_KEY"),
            base_url=os.getenv("DATA_GOV_IN_BASE_URL", "https://api.data.gov.in"),
            timeout=int(os.getenv("DATA_GOV_IN_TIMEOUT", "30")),
            rate_limit_calls=int(os.getenv("DATA_GOV_IN_RATE_LIMIT_CALLS", "100")),
            rate_limit_period=int(os.getenv("DATA_GOV_IN_RATE_LIMIT_PERIOD", "60")),
            cache_enabled=os.getenv("DATA_GOV_IN_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("DATA_GOV_IN_CACHE_TTL", "3600")),
            cache_max_size=int(os.getenv("DATA_GOV_IN_CACHE_MAX_SIZE", "1000")),
            log_level=os.getenv("DATA_GOV_IN_LOG_LEVEL", "INFO"),
            max_retries=int(os.getenv("DATA_GOV_IN_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("DATA_GOV_IN_RETRY_DELAY", "1.0")),
            backoff_factor=float(os.getenv("DATA_GOV_IN_BACKOFF_FACTOR", "2.0")),
            default_limit=int(os.getenv("DATA_GOV_IN_DEFAULT_LIMIT", "10")),
            max_limit=int(os.getenv("DATA_GOV_IN_MAX_LIMIT", "100")),
        )

    def validate(self) -> None:
        """Validate configuration settings"""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.rate_limit_calls <= 0:
            raise ValueError("rate_limit_calls must be positive")
        if self.rate_limit_period <= 0:
            raise ValueError("rate_limit_period must be positive")
        if self.cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.default_limit <= 0 or self.default_limit > self.max_limit:
            raise ValueError(f"default_limit must be between 1 and {self.max_limit}")
