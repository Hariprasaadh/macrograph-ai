"""Normalize transport envelopes without interpreting economic observations."""
from __future__ import annotations

import json
from typing import Any


def normalize_mcp_response(response: Any) -> dict[str, Any]:
    """Accept SDK objects, JSON-RPC, JSON strings, content blocks and SSE.

    Metadata dictionaries retain their keys; bare row lists become ``data``.
    Error messages are never interpreted as observations.
    """
    def merge(parts: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for part in parts:
            for key, value in part.items():
                if key in out and isinstance(out[key], list) and isinstance(value, list):
                    out[key].extend(value)
                elif key == 'error' and key in out:
                    out[key] = f'{out[key]}; {value}'
                else:
                    out[key] = value
        return out

    def decode(obj: Any, depth: int = 0) -> dict[str, Any]:
        if depth > 20:
            return {'error': 'MCP response nesting exceeds limit'}
        if hasattr(obj, 'is_error') and obj.is_error:
            return {'error': str(getattr(obj, 'content', 'MCP tool failed'))}
        for attr in ('structured_content', 'data'):
            if not isinstance(obj, (dict, list, str)) and getattr(obj, attr, None) is not None:
                return decode(getattr(obj, attr), depth + 1)
        if hasattr(obj, 'model_dump'):
            obj = obj.model_dump(mode='json')
        elif hasattr(obj, 'content'):
            obj = {'content': obj.content}
        if isinstance(obj, bytes):
            obj = obj.decode('utf-8', errors='replace')
        if isinstance(obj, str):
            try:
                return decode(json.loads(obj), depth + 1)
            except (ValueError, TypeError):
                pass
            if any(line.startswith('data:') for line in obj.splitlines()):
                events, lines = [], []
                for line in obj.splitlines() + ['']:
                    if line.startswith('data:'):
                        lines.append(line[5:].lstrip())
                    elif not line and lines:
                        body = '\n'.join(lines)
                        lines = []
                        if body != '[DONE]':
                            events.append(decode(body, depth + 1))
                return merge(events)
            return {'error': obj.strip() or 'Empty MCP response'}
        if isinstance(obj, list):
            rows, parts = [], []
            for item in obj:
                if hasattr(item, 'model_dump'):
                    item = item.model_dump(mode='json')
                if isinstance(item, dict) and not any(k in item for k in ('jsonrpc', 'content', 'structuredContent')) and item.get('type') != 'text':
                    rows.append(item)
                else:
                    parts.append(decode(item, depth + 1))
            if rows:
                parts.insert(0, {'data': rows})
            return merge(parts)
        if not isinstance(obj, dict):
            return {'error': 'Empty or unsupported MCP response'}
        if obj.get('isError') or obj.get('is_error') or obj.get('error'):
            return {**obj, 'error': str(obj.get('error') or obj.get('content') or 'MCP tool failed')}
        if obj.get('statusCode') is False:
            return {**obj, 'error': str(obj.get('msg') or obj.get('message') or 'Source request failed')}
        if 'jsonrpc' in obj:
            return decode(obj['result'], depth + 1) if 'result' in obj else {}
        for key in ('structuredContent', 'structured_content'):
            if obj.get(key) is not None:
                return decode(obj[key], depth + 1)
        if obj.get('type') == 'text':
            return decode(obj.get('text'), depth + 1)
        if 'content' in obj:
            return decode(obj['content'], depth + 1)
        if isinstance(obj.get('data'), str):
            return {**obj, **decode(obj['data'], depth + 1)}
        return obj

    return decode(response)
