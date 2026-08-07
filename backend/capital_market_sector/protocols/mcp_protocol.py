from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Tool purpose description")
    inputSchema: Dict[str, Any] = Field(..., description="JSON Schema for input parameters")
    outputSchema: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema for output payload")


class MCPJsonRpcRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = Field(default=1)
    method: str = Field(..., description="Method name: tools/list or tools/call")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MCPJsonRpcResponse(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


def handle_mcp_rpc(request_dict: Dict[str, Any], tool_registry: Any) -> Dict[str, Any]:
    try:
        req = MCPJsonRpcRequest.model_validate(request_dict)
    except Exception as err:
        return MCPJsonRpcResponse(id=request_dict.get("id"), error={"code": -32600, "message": f"Invalid Request: {err}"}).model_dump()

    if req.method == "tools/list":
        tools = [t.model_dump() for t in tool_registry.mcp_tools()]
        return MCPJsonRpcResponse(id=req.id, result={"tools": tools}).model_dump()

    if req.method == "tools/call":
        params = req.params or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}

        if not name:
            return MCPJsonRpcResponse(id=req.id, error={"code": -32602, "message": "Missing tool name in params"}).model_dump()

        try:
            result = tool_registry.invoke(name, arguments)
            return MCPJsonRpcResponse(id=req.id, result={"content": [{"type": "text", "text": result.model_dump_json(indent=2)}], "isError": False}).model_dump()
        except KeyError as err:
            return MCPJsonRpcResponse(id=req.id, error={"code": -32601, "message": f"Method/Tool not found: {err}"}).model_dump()
        except Exception as err:
            return MCPJsonRpcResponse(id=req.id, result={"content": [{"type": "text", "text": str(err)}], "isError": True}).model_dump()

    return MCPJsonRpcResponse(id=req.id, error={"code": -32601, "message": f"Method not found: {req.method}"}).model_dump()
