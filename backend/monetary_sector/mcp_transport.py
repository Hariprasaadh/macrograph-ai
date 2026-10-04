"""Stdio MCP transport for the Monetary Sector.

Owns everything needed to spawn MCP servers (uvx/npx) over stdio JSON-RPC,
call one tool, and shut down: subprocess environment, a process-wide cap on
concurrent spawns, result extraction, and tenacity-bounded retries for
transient transport failures.

Nothing in this module knows about monetary datasets; dataset mapping lives
in ``monetary_sector.client``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

STDIO_LINE_LIMIT = 16 * 1024 * 1024

_D_CACHE_DIRS: tuple[tuple[str, str], ...] = (
    ("UV_CACHE_DIR", r"D:\uv-cache"),
    ("npm_config_cache", r"D:\npm-cache"),
    ("TEMP", r"D:\Temp"),
    ("TMP", r"D:\Temp"),
)

# Cap concurrent MCP subprocesses process-wide. Overlapping chat requests each
# fan out into several uvx/npx spawns; uncapped, they contend on package locks
# and cascade into timeouts that force cache fallbacks.
MCP_SPAWN_SEMAPHORE = asyncio.Semaphore(2)


def mcp_spawn_env() -> dict[str, str]:
    """Environment for MCP subprocesses.

    Redirects uv/npm/temp writes to D: when those directories exist (the C:
    drive on this machine is full, which otherwise breaks package execution).
    Never overrides variables the operator already set.
    """
    env = dict(os.environ)
    if os.name == "nt":
        for key, path in _D_CACHE_DIRS:
            if os.path.isdir(path):
                env.setdefault(key, path)
    return env


def _extract_tool_payload(result: Any, label: str, tool_name: str) -> Any:
    """Return the parsed payload of a stdio MCP tools/call result."""
    if not isinstance(result, dict):
        raise ValueError(f"{label} MCP tool {tool_name} returned no result object.")
    if result.get("isError"):
        raise ValueError(f"{label} MCP tool {tool_name} failed: {result.get('content')}")
    structured = result.get("structuredContent")
    if structured is not None:
        return structured
    content = result.get("content")
    if not isinstance(content, list):
        raise ValueError(f"{label} MCP tool {tool_name} returned no content.")
    text = next(
        (
            item.get("text")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ),
        None,
    )
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{label} MCP tool {tool_name} returned empty text content.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} MCP tool {tool_name} returned malformed JSON content.") from error
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(f"{label} MCP tool {tool_name} returned an error payload: {payload}")
    return payload


async def _spawn_and_call(
    argv: tuple[str, ...],
    timeout: float,
    label: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=STDIO_LINE_LIMIT,
        env=mcp_spawn_env(),
    )
    assert process.stdin is not None and process.stdout is not None
    request_id = 0

    async def _rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
        nonlocal request_id
        request_id += 1
        process.stdin.write(
            (
                json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
                + "\n"
            ).encode()
        )
        await process.stdin.drain()
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"{label} MCP timed out during {method}.")
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=remaining)
            except TimeoutError:
                raise TimeoutError(
                    f"{label} MCP produced no reply to {method} within {timeout:.0f}s "
                    f"(cold package start or stuck process)."
                ) from None
            if not line:
                raise ConnectionError(f"{label} MCP exited before replying to {method}.")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if message.get("error"):
                raise ValueError(f"{label} MCP error during {method}: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ValueError(f"{label} MCP returned no result for {method}.")
            return result

    try:
        await _rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "macrograph-ai", "version": "0.1.0"},
            },
        )
        process.stdin.write(
            (json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode()
        )
        result = await _rpc("tools/call", {"name": tool_name, "arguments": arguments})
        return _extract_tool_payload(result, label, tool_name)
    finally:
        try:
            if not process.stdin.is_closing():
                process.stdin.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def call_stdio_mcp_tool(
    command: tuple[str, ...],
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float,
    label: str,
    retries: int = 0,
) -> Any:
    """Spawn a stdio MCP server, initialize it, call one tool, and shut down.

    Returns the parsed tool payload. Transient transport failures
    (TimeoutError/ConnectionError) are retried with tenacity up to ``retries``
    times; tool-level errors and malformed payloads raise immediately.
    At most two MCP sessions run concurrently process-wide.
    """
    if os.name == "nt" and command[0] == "npx":
        argv: tuple[str, ...] = ("cmd.exe", "/d", "/s", "/c", "npx.cmd --yes " + " ".join(command[1:]))
    else:
        argv = tuple(command)
    async with MCP_SPAWN_SEMAPHORE:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(retries + 1),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                return await _spawn_and_call(argv, timeout, label, tool_name, arguments)
