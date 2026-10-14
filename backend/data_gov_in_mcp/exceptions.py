"""
Custom exceptions for data.gov.in MCP server
"""


class DataGovInException(Exception):
    """Base exception for all data.gov.in errors"""
    pass


class APIKeyMissingError(DataGovInException):
    """Raised when API key is not provided"""
    def __init__(self, message: str = "API key is required. Set DATA_GOV_IN_API_KEY environment variable."):
        super().__init__(message)


class RateLimitError(DataGovInException):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message)


class ResourceNotFoundError(DataGovInException):
    """Raised when requested resource is not found"""
    def __init__(self, resource_id: str):
        super().__init__(f"Resource '{resource_id}' not found")


class InvalidParameterError(DataGovInException):
    """Raised when invalid parameters are provided"""
    def __init__(self, param: str, message: str):
        super().__init__(f"Invalid parameter '{param}': {message}")


class APIError(DataGovInException):
    """Raised when API returns an error response"""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"API Error ({status_code}): {message}")


class NetworkError(DataGovInException):
    """Raised when network-related errors occur"""
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message)
