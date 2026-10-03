from __future__ import annotations

import json

import httpx
import pytest

from capital_market_sector.mcp_client import NseMcpError, call_nse_tool, decode_rpc_response


def test_decode_rpc_response_from_sse_message():
    payload = {"jsonrpc": "2.0", "id": 5, "result": {"tools": []}}
    response = decode_rpc_response(
        f"event: message\ndata: {json.dumps(payload)}\n\n",
        "text/event-stream",
    )

    assert response == payload


@pytest.mark.asyncio
async def test_call_nse_tool_negotiates_session_and_unwraps_tool_result():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        requests.append((body, request.headers.get("mcp-session-id")))
        method = body["method"]
        if method == "initialize":
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "mcp-session-id": "session-test",
                },
                json={"jsonrpc": "2.0", "id": body["id"], "result": {}},
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"tools": [{"name": "get_market_breadth"}]},
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({"date": "2026-10-02", "advances": 100}),
                    }],
                    "isError": False,
                },
            }
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=f"event: message\ndata: {json.dumps(response)}\n\n",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await call_nse_tool(
            "https://mcp.example.test/mcp",
            "get_market_breadth",
            {"date": "2026-10-03"},
            http_client=client,
        )

    assert result == {"date": "2026-10-02", "advances": 100}
    assert [request[0]["method"] for request in requests] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert requests[-1][1] == "session-test"
    assert requests[-1][0]["params"]["arguments"] == {"date": "2026-10-03"}


@pytest.mark.asyncio
async def test_call_nse_tool_rejects_unknown_tools():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"jsonrpc": "2.0", "id": body["id"], "result": {}},
            )
        if body["method"] == "notifications/initialized":
            return httpx.Response(202)
        result = {"tools": []}
        payload = {"jsonrpc": "2.0", "id": body["id"], "result": result}
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=f"event: message\ndata: {json.dumps(payload)}\n\n",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NseMcpError, match="does not expose tool"):
            await call_nse_tool(
                "https://mcp.example.test/mcp",
                "get_not_a_real_tool",
                {},
                http_client=client,
            )
