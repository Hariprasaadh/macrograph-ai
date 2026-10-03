"""Small Streamable HTTP MCP client for the NSE market-data endpoints."""
from __future__ import annotations

import json
from typing import Any

import httpx


class NseMcpError(RuntimeError):
    """Raised when the NSE MCP endpoint cannot provide a valid tool result."""


def decode_rpc_response(body: str, content_type: str) -> dict[str, Any]:
    """Decode either a JSON-RPC response or its SSE `data:` event."""
    if "application/json" in content_type:
        payload = json.loads(body)
        if isinstance(payload, dict):
            return payload
        raise NseMcpError("NSE MCP returned a non-object JSON-RPC response.")

    data_lines = [
        line[5:].strip()
        for line in body.splitlines()
        if line.startswith("data:")
    ]
    if not data_lines:
        raise NseMcpError("NSE MCP returned an empty SSE response.")

    for data in data_lines:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise NseMcpError("NSE MCP SSE response did not contain a JSON-RPC object.")


def _check_rpc_error(payload: dict[str, Any], action: str) -> dict[str, Any]:
    error = payload.get("error")
    if error:
        raise NseMcpError(f"NSE MCP {action} failed: {error}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NseMcpError(f"NSE MCP {action} returned no result object.")
    return result


def _unwrap_tool_result(result: dict[str, Any], tool_name: str) -> dict[str, Any]:
    if result.get("isError"):
        raise NseMcpError(f"NSE MCP tool {tool_name!r} reported an error.")

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    content = result.get("content")
    if not isinstance(content, list):
        raise NseMcpError(f"NSE MCP tool {tool_name!r} returned no content.")

    text_parts = [
        item.get("text")
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    for text in text_parts:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            if payload.get("error"):
                raise NseMcpError(
                    f"NSE MCP tool {tool_name!r} failed: {payload['error']}"
                )
            return payload
    raise NseMcpError(
        f"NSE MCP tool {tool_name!r} returned no usable structured JSON."
    )


async def call_nse_tool(
    endpoint: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Initialize an MCP session, confirm the tool exists, and invoke it."""
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0, read=25.0),
        headers={"Accept": "application/json, text/event-stream"},
        follow_redirects=True,
    )
    try:
        initialize_response = await client.post(
            endpoint,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "macrograph-capital-market", "version": "1.0"},
                },
            },
        )
        initialize_response.raise_for_status()
        initialize = decode_rpc_response(
            initialize_response.text,
            initialize_response.headers.get("content-type", ""),
        )
        _check_rpc_error(initialize, "initialize")

        headers = {}
        session_id = initialize_response.headers.get("mcp-session-id")
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        await client.post(
            endpoint,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=headers,
        )

        tools_response = await client.post(
            endpoint,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
            headers=headers,
        )
        tools_response.raise_for_status()
        tools_rpc = decode_rpc_response(
            tools_response.text,
            tools_response.headers.get("content-type", ""),
        )
        tools_result = _check_rpc_error(tools_rpc, "tools/list")
        tools = tools_result.get("tools")
        if not isinstance(tools, list) or not any(
            isinstance(tool, dict) and tool.get("name") == tool_name
            for tool in tools
        ):
            raise NseMcpError(f"NSE MCP does not expose tool {tool_name!r}.")

        tool_response = await client.post(
            endpoint,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers=headers,
        )
        tool_response.raise_for_status()
        tool_rpc = decode_rpc_response(
            tool_response.text,
            tool_response.headers.get("content-type", ""),
        )
        tool_result = _check_rpc_error(tool_rpc, f"tools/call {tool_name}")
        return _unwrap_tool_result(tool_result, tool_name)
    finally:
        if owns_client:
            await client.aclose()
