"""
data.gov.in MCP Server

A production-ready Model Context Protocol server for accessing Indian government open data.
"""

__version__ = "1.0.0"
__author__ = "Data.gov.in MCP Team"

from .api_client import DataGovInClient
from .exceptions import (
    DataGovInException,
    APIKeyMissingError,
    RateLimitError,
    ResourceNotFoundError,
    InvalidParameterError,
)

__all__ = [
    "DataGovInClient",
    "DataGovInException",
    "APIKeyMissingError",
    "RateLimitError",
    "ResourceNotFoundError",
    "InvalidParameterError",
]
