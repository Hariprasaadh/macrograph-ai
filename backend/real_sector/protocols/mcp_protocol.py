"""Model Context Protocol (MCP) Models and RPC Handler.

Provides MCP standard schemas for tools, JSON-RPC 2.0 requests, responses,
and dispatcher methods for tools/list and tools/call.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """MCP Tool definition exposed to LLMs."""
    name: str = Field(..., description="Unique tool identifier name")
    description: str = Field(..., description="Detailed description of tool purpose")
    inputSchema: Dict[str, Any] = Field(..., description="JSON Schema of acceptable input parameters")
    outputSchema: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema of return payload")


class MCPToolsListResponse(BaseModel):
    """Result structure for tools/list."""
    tools: List[MCPTool]


class MCPToolCallResponse(BaseModel):
    """Result structure for tools/call."""
    content: List[Dict[str, Any]]
    isError: bool = False


class MCPJsonRpcRequest(BaseModel):
    """Standard JSON-RPC 2.0 request payload."""
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = Field(default=1)
    method: str = Field(..., description="Method name: tools/list or tools/call")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MCPJsonRpcResponse(BaseModel):
    """Standard JSON-RPC 2.0 response payload."""
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = Field(default=None)
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


def handle_mcp_rpc(request_dict: Dict[str, Any], tool_registry: Any) -> Dict[str, Any]:
    """Processes an incoming MCP JSON-RPC 2.0 request dictionary.
    
    Supports:
    - method: "tools/list"
    - method: "tools/call" (with params: {"name": str, "arguments": dict})
    """
    try:
        req = MCPJsonRpcRequest.model_validate(request_dict)
    except Exception as err:
        return MCPJsonRpcResponse(
            id=request_dict.get("id"),
            error={"code": -32600, "message": f"Invalid Request: {err}"}
        ).model_dump()

    if req.method == "tools/list":
        mcp_tools = tool_registry.mcp_tools()
        return MCPJsonRpcResponse(
            id=req.id,
            result={"tools": [t.model_dump() for t in mcp_tools]}
        ).model_dump()

    elif req.method == "tools/call":
        params = req.params or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}

        if not name:
            return MCPJsonRpcResponse(
                id=req.id,
                error={"code": -32602, "message": "Missing tool name in params"}
            ).model_dump()

        try:
            result = tool_registry.invoke(name, arguments)
            return MCPJsonRpcResponse(
                id=req.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": result.model_dump_json(indent=2)
                        }
                    ],
                    "isError": False
                }
            ).model_dump()
        except KeyError as err:
            return MCPJsonRpcResponse(
                id=req.id,
                error={"code": -32601, "message": f"Method/Tool not found: {err}"}
            ).model_dump()
        except Exception as err:
            return MCPJsonRpcResponse(
                id=req.id,
                result={
                    "content": [{"type": "text", "text": str(err)}],
                    "isError": True
                }
            ).model_dump()

    else:
        return MCPJsonRpcResponse(
            id=req.id,
            error={"code": -32601, "message": f"Method not found: {req.method}"}
        ).model_dump()
