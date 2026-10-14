"""
API client for data.gov.in
"""

import time
import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import httpx

from .config import Config
from .cache import Cache
from .exceptions import (
    APIKeyMissingError,
    RateLimitError,
    ResourceNotFoundError,
    APIError,
    NetworkError,
    InvalidParameterError,
)


logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using sliding window"""

    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove calls outside the current window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.calls = []

        self.calls.append(time.time())


class DataGovInClient:
    """
    Client for interacting with data.gov.in API

    This client provides methods to search, retrieve, and download datasets
    from the Indian government's open data portal.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the API client

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or Config.from_env()
        self.config.validate()

        if not self.config.api_key:
            logger.warning("API key not set. Some operations may fail.")

        self.cache = Cache(
            max_size=self.config.cache_max_size,
            default_ttl=self.config.cache_ttl
        ) if self.config.cache_enabled else None

        self.rate_limiter = RateLimiter(
            max_calls=self.config.rate_limit_calls,
            period=self.config.rate_limit_period
        )

        self.client = httpx.Client(
            timeout=self.config.timeout,
            headers={
                "User-Agent": "data-gov-in-mcp/1.0.0",
                "Accept": "application/json",
            }
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def _build_url(self, resource_id: str) -> str:
        """Build API URL for a resource"""
        return urljoin(self.config.base_url, f"/resource/{resource_id}")

    def _make_request(
        self,
        resource_id: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the API with retries and error handling

        Args:
            resource_id: Resource identifier
            params: Query parameters
            use_cache: Whether to use cache

        Returns:
            API response as dictionary

        Raises:
            Various exceptions based on error type
        """
        if not self.config.api_key:
            raise APIKeyMissingError()

        # Prepare parameters
        params = params or {}
        params["api-key"] = self.config.api_key
        params.setdefault("format", "json")

        # Check cache
        if use_cache and self.cache:
            cache_key = self.cache._make_key(resource_id, **params)
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for resource {resource_id}")
                return cached

        # Rate limiting
        self.rate_limiter.wait_if_needed()

        # Make request with retries
        url = self._build_url(resource_id)
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Request to {url} (attempt {attempt + 1}/{self.config.max_retries + 1})")
                response = self.client.get(url, params=params)

                # Handle HTTP errors
                if response.status_code == 404:
                    raise ResourceNotFoundError(resource_id)
                elif response.status_code == 429:
                    raise RateLimitError()
                elif response.status_code >= 400:
                    # Provider error bodies can echo the request URL and API key.
                    raise APIError(response.status_code, "Dataset request rejected")

                response.raise_for_status()
                data = response.json()

                # Cache successful response
                if use_cache and self.cache:
                    self.cache.set(cache_key, data)

                return data

            except httpx.TimeoutException as e:
                last_exception = NetworkError("Request timeout")
                logger.warning("Timeout on attempt %s", attempt + 1)

            except httpx.NetworkError as e:
                last_exception = NetworkError("Network error")
                logger.warning("Network error on attempt %s", attempt + 1)

            except (APIError, RateLimitError, ResourceNotFoundError):
                # Don't retry these errors
                raise

            except Exception as e:
                last_exception = APIError(500, "Unexpected transport error")
                logger.error("Unexpected error on attempt %s: %s", attempt + 1, type(e).__name__)

            # Wait before retry with exponential backoff
            if attempt < self.config.max_retries:
                sleep_time = self.config.retry_delay * (self.config.backoff_factor ** attempt)
                logger.debug(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)

        # All retries failed
        raise last_exception or NetworkError("All retry attempts failed")

    def get_resource(
        self,
        resource_id: str,
        filters: Optional[Dict[str, str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        sort: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Get data from a specific resource

        Args:
            resource_id: Unique identifier for the resource/dataset
            filters: Optional filters to apply to the data
            offset: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            Dictionary containing the resource data

        Example:
            >>> client = DataGovInClient()
            >>> data = client.get_resource("9ef84268-d588-465a-a308-a864a43d0070", limit=5)
        """
        if not re.fullmatch(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", resource_id):
            raise InvalidParameterError("resource_id", "Expected a resource UUID")
        limit = limit or self.config.default_limit
        if limit > self.config.max_limit:
            raise InvalidParameterError("limit", f"Cannot exceed {self.config.max_limit}")

        params = {
            "offset": offset,
            "limit": limit,
        }

        # Add filters
        if filters:
            if any(not re.fullmatch(r"[a-zA-Z0-9_]+", field) for field in filters):
                raise InvalidParameterError("filters", "Field names must be alphanumeric")
            params.update({f"filters[{field}]": value for field, value in filters.items()})
        if sort:
            if any(not re.fullmatch(r"[a-zA-Z0-9_]+", field) or direction not in {"asc", "desc"}
                   for field, direction in sort.items()):
                raise InvalidParameterError("sort", "Invalid field or sort direction")
            params.update({f"sort[{field}]": direction for field, direction in sort.items()})

        return self._make_request(resource_id, params)

    def get_resource_fields(self, resource_id: str) -> List[Dict[str, str]]:
        """
        Get field information for a resource

        Args:
            resource_id: Unique identifier for the resource

        Returns:
            List of field definitions
        """
        data = self._make_request(resource_id, {"limit": 1})

        if "field" in data:
            return data["field"]
        if "fields" in data:
            return data["fields"]
        elif "records" in data and len(data["records"]) > 0:
            # Infer fields from first record
            first_record = data["records"][0]
            return [
                {"id": key, "type": type(value).__name__}
                for key, value in first_record.items()
            ]
        else:
            return []

    def search_resources(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for resources (Note: This might require different API endpoint)

        Args:
            query: Search query string
            offset: Number of results to skip
            limit: Maximum number of results to return

        Returns:
            Search results
        """
        # Note: data.gov.in might not have a direct search API
        # This is a placeholder implementation
        logger.warning("Search functionality may not be directly available in data.gov.in API")
        return {
            "message": "Search functionality requires web scraping or catalog API access",
            "query": query
        }

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.stats()
        return None

    def clear_cache(self) -> None:
        """Clear all cached data"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
