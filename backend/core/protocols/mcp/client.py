"""Protocol-Level FastMCP Client Invocation Wrapper."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from fastmcp import Client, FastMCP


class MCPClientWrapper:
    """Invokes FastMCP tools through the standard FastMCP client protocol."""

    def __init__(self, server: FastMCP) -> None:
        self.server = server

    async def call_tool_async(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calls a tool asynchronously over the MCP Client session."""
        args = arguments or {}
        async with Client(self.server) as client:
            result = await client.call_tool(tool_name, args)
            if result.is_error:
                return {"status": "error", "message": str(result.content)}
            
            # Extract content from MCP response
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    try:
                        return json.loads(content_item.text)
                    except Exception:
                        return {"status": "success", "content": content_item.text}

            if result.data:
                return result.data

            return {"status": "success", "raw": str(result)}
