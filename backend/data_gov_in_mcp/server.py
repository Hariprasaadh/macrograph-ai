"""
MCP Server implementation for data.gov.in
"""

import logging
import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP

from .api_client import DataGovInClient
from .config import Config
from .exceptions import DataGovInException


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# httpx logs full request URLs at INFO, including the API key query parameter.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# Initialize FastMCP server
mcp = FastMCP(
    "data.gov.in MCP Server",
    version="1.0.0"
)

# Global client instance
_client: Optional[DataGovInClient] = None
_configured_key: Optional[str] = None


def get_client() -> DataGovInClient:
    """Get or create the API client instance"""
    global _client
    if _client is None:
        config = Config.from_env()
        _client = DataGovInClient(config)
        logger.info("Initialized data.gov.in API client")
    return _client


def configure_client(api_key: str) -> None:
    """Supply an application-managed key without exposing it in MCP arguments."""
    global _client, _configured_key
    if not api_key:
        raise ValueError("DATA_GOV_IN_API_KEY is required")
    if _client is not None and _configured_key == api_key:
        return
    if _client is not None:
        _client.close()
    _client = DataGovInClient(Config(api_key=api_key))
    _configured_key = api_key


@mcp.tool()
def get_dataset(
    resource_id: str,
    limit: int = 10,
    offset: int = 0,
    filters: Optional[str] = None,
    sort: Optional[str] = None,
) -> str:
    """
    Retrieve data from a specific dataset/resource on data.gov.in

    Args:
        resource_id: The unique identifier for the dataset resource (e.g., "9ef84268-d588-465a-a308-a864a43d0070")
        limit: Maximum number of records to return (default: 10, max: 100)
        offset: Number of records to skip for pagination (default: 0)
        filters: Optional JSON string of filters to apply (e.g., '{"state": "Maharashtra"}')

    Returns:
        JSON string containing the dataset records and metadata

    Example:
        get_dataset("9ef84268-d588-465a-a308-a864a43d0070", limit=5)
    """
    try:
        client = get_client()

        # Parse filters and sort fields supplied by the caller.
        filter_dict = None
        if filters:
            try:
                filter_dict = json.loads(filters)
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "Invalid filters format. Must be valid JSON.",
                    "example": '{"field_name": "value"}'
                })

        sort_dict = None
        if sort:
            try:
                sort_dict = json.loads(sort)
                if not isinstance(sort_dict, dict) or any(
                    direction not in {"asc", "desc"} for direction in sort_dict.values()
                ):
                    raise ValueError("Invalid sort direction")
            except (json.JSONDecodeError, ValueError):
                return json.dumps({"error": "Invalid sort format. Use a JSON object with asc/desc values."})

        data = client.get_resource(
            resource_id=resource_id,
            filters=filter_dict,
            offset=offset,
            limit=limit,
            sort=sort_dict,
        )
        if data.get("status") in {"error", "failed"} or data.get("error"):
            return json.dumps({"error": "Data.gov.in rejected the dataset request"})

        # Format response
        result = {
            "resource_id": resource_id,
            "total_records": data.get("total", len(data.get("records", []))),
            "offset": offset,
            "limit": limit,
            "records": data.get("records", []),
            "fields": data.get("field", []),
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except DataGovInException as e:
        logger.error(f"Error retrieving dataset {resource_id}: {e}")
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def get_dataset_fields(resource_id: str) -> str:
    """
    Get field information and schema for a dataset

    Args:
        resource_id: The unique identifier for the dataset resource

    Returns:
        JSON string containing field definitions including names and types

    Example:
        get_dataset_fields("9ef84268-d588-465a-a308-a864a43d0070")
    """
    try:
        client = get_client()
        fields = client.get_resource_fields(resource_id)

        result = {
            "resource_id": resource_id,
            "field_count": len(fields),
            "fields": fields
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except DataGovInException as e:
        logger.error(f"Error retrieving fields for {resource_id}: {e}")
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def paginate_dataset(
    resource_id: str,
    page: int = 1,
    page_size: int = 10
) -> str:
    """
    Retrieve a specific page of data from a dataset

    Args:
        resource_id: The unique identifier for the dataset resource
        page: Page number to retrieve (starting from 1)
        page_size: Number of records per page (default: 10, max: 100)

    Returns:
        JSON string containing the page of records with pagination metadata

    Example:
        paginate_dataset("9ef84268-d588-465a-a308-a864a43d0070", page=2, page_size=20)
    """
    try:
        if page < 1:
            return json.dumps({"error": "Page number must be >= 1"}, indent=2)

        client = get_client()
        offset = (page - 1) * page_size

        data = client.get_resource(
            resource_id=resource_id,
            offset=offset,
            limit=page_size
        )

        total_records = data.get("total", len(data.get("records", [])))
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

        result = {
            "resource_id": resource_id,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "records": data.get("records", [])
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except DataGovInException as e:
        logger.error(f"Error paginating dataset {resource_id}: {e}")
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def get_dataset_summary(resource_id: str) -> str:
    """
    Get a summary of a dataset including record count and field information

    Args:
        resource_id: The unique identifier for the dataset resource

    Returns:
        JSON string containing dataset summary statistics

    Example:
        get_dataset_summary("9ef84268-d588-465a-a308-a864a43d0070")
    """
    try:
        client = get_client()

        # Get first record to determine structure
        data = client.get_resource(resource_id=resource_id, limit=1)
        fields = client.get_resource_fields(resource_id)

        result = {
            "resource_id": resource_id,
            "total_records": data.get("total", 0),
            "field_count": len(fields),
            "fields": [field.get("id") or field.get("name", "unknown") for field in fields],
            "sample_record": data.get("records", [None])[0] if data.get("records") else None
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except DataGovInException as e:
        logger.error(f"Error getting summary for {resource_id}: {e}")
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def filter_dataset(
    resource_id: str,
    field: str,
    value: str,
    limit: int = 10
) -> str:
    """
    Filter dataset records by a specific field value

    Args:
        resource_id: The unique identifier for the dataset resource
        field: The field name to filter on
        value: The value to filter for
        limit: Maximum number of matching records to return (default: 10)

    Returns:
        JSON string containing filtered records

    Example:
        filter_dataset("9ef84268-d588-465a-a308-a864a43d0070", "state", "Maharashtra", limit=5)
    """
    try:
        client = get_client()
        filters = {field: value}

        data = client.get_resource(
            resource_id=resource_id,
            filters=filters,
            limit=limit
        )

        result = {
            "resource_id": resource_id,
            "filter": {field: value},
            "matched_records": len(data.get("records", [])),
            "records": data.get("records", [])
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except DataGovInException as e:
        logger.error(f"Error filtering dataset {resource_id}: {e}")
        return json.dumps({"error": str(e)}, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def get_cache_statistics() -> str:
    """
    Get statistics about the API response cache

    Returns:
        JSON string containing cache hit/miss rates and size information

    Example:
        get_cache_statistics()
    """
    try:
        client = get_client()
        stats = client.get_cache_stats()

        if stats is None:
            return json.dumps({
                "cache_enabled": False,
                "message": "Caching is disabled"
            }, indent=2)

        return json.dumps({"cache_enabled": True, **stats}, indent=2)

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def clear_cache() -> str:
    """
    Clear all cached API responses

    Returns:
        JSON string confirming cache was cleared

    Example:
        clear_cache()
    """
    try:
        client = get_client()
        client.clear_cache()

        return json.dumps({
            "success": True,
            "message": "Cache cleared successfully"
        }, indent=2)

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool()
def get_server_info() -> str:
    """
    Get information about the MCP server and its configuration

    Returns:
        JSON string containing server version and configuration details

    Example:
        get_server_info()
    """
    try:
        client = get_client()
        config = client.config

        info = {
            "server": "data.gov.in MCP Server",
            "version": "1.0.0",
            "configuration": {
                "api_base_url": config.base_url,
                "cache_enabled": config.cache_enabled,
                "cache_ttl": config.cache_ttl,
                "rate_limit": f"{config.rate_limit_calls} calls per {config.rate_limit_period}s",
                "timeout": f"{config.timeout}s",
                "default_limit": config.default_limit,
                "max_limit": config.max_limit,
            },
            "api_key_configured": bool(config.api_key)
        }

        return json.dumps(info, indent=2)

    except Exception as e:
        logger.error(f"Error getting server info: {e}", exc_info=True)
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, indent=2)


def run_server():
    """Run the MCP server"""
    logger.info("Starting data.gov.in MCP Server")
    mcp.run(transport='stdio')


if __name__ == "__main__":
    run_server()
