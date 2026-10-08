"""A2A protocol errors with stable machine-readable codes."""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Structured failure codes carried in A2AResponse.errors."""
    INVALID_REQUEST = "INVALID_REQUEST"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    DEPENDENCY_NOT_ALLOWED = "DEPENDENCY_NOT_ALLOWED"
    MAX_DEPTH_EXCEEDED = "MAX_DEPTH_EXCEEDED"
    MAX_HOPS_EXCEEDED = "MAX_HOPS_EXCEEDED"
    CIRCULAR_DELEGATION = "CIRCULAR_DELEGATION"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_ERROR = "AGENT_ERROR"
    DATA_SOURCE_ERROR = "DATA_SOURCE_ERROR"
    LLM_ERROR = "LLM_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"


RETRYABLE_CODES = frozenset({ErrorCode.AGENT_TIMEOUT, ErrorCode.TRANSPORT_ERROR})


class A2AException(Exception):
    """Base class; every subclass maps to exactly one ErrorCode."""
    code: ErrorCode = ErrorCode.AGENT_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRequestError(A2AException):
    code = ErrorCode.INVALID_REQUEST


class AgentNotFoundError(A2AException):
    code = ErrorCode.AGENT_NOT_FOUND


class AgentUnavailableError(A2AException):
    code = ErrorCode.AGENT_UNAVAILABLE


class UnsupportedCapabilityError(A2AException):
    code = ErrorCode.UNSUPPORTED_CAPABILITY


class DependencyNotAllowedError(A2AException):
    code = ErrorCode.DEPENDENCY_NOT_ALLOWED


class MaxDepthExceededError(A2AException):
    code = ErrorCode.MAX_DEPTH_EXCEEDED


class MaxHopsExceededError(A2AException):
    code = ErrorCode.MAX_HOPS_EXCEEDED


class CircularDelegationError(A2AException):
    code = ErrorCode.CIRCULAR_DELEGATION


class DuplicateRequestError(A2AException):
    code = ErrorCode.DUPLICATE_REQUEST


class A2ATimeoutError(A2AException):
    code = ErrorCode.AGENT_TIMEOUT


class DataSourceError(A2AException):
    """Raised by handlers when MCP tools or upstream data sources fail."""
    code = ErrorCode.DATA_SOURCE_ERROR


class LLMError(A2AException):
    code = ErrorCode.LLM_ERROR


class InvalidResponseError(A2AException):
    code = ErrorCode.INVALID_RESPONSE


class TransportError(A2AException):
    code = ErrorCode.TRANSPORT_ERROR
