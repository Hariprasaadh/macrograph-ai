"""In-memory A2A trace store: reconstructs the delegation graph per conversation."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import threading
from typing import Any, Optional

from core.config import settings

from .messages import A2ARequest, A2AResponse


@dataclass
class TraceNode:
    request_id: str
    parent_request_id: Optional[str]
    sender_agent: str
    receiver_agent: str
    task: str
    depth: int
    started_at: str
    status: str = "pending"
    error_codes: list[str] = field(default_factory=list)
    duration_ms: Optional[float] = None


@dataclass
class _Conversation:
    nodes: dict[str, TraceNode] = field(default_factory=dict)
    seen: dict[str, str] = field(default_factory=dict)
    hops: int = 0


def request_key(request: A2ARequest) -> str:
    """Semantic identity of a request, independent of its request_id."""
    payload = json.dumps(
        [request.sender_agent, request.parent_request_id, request.receiver_agent,
         request.task, request.parameters],
        sort_keys=True, default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TraceStore:
    """Thread-safe, bounded store; oldest conversations are evicted first."""

    def __init__(self, max_conversations: int = 500) -> None:
        self._max = max_conversations
        self._conversations: OrderedDict[str, _Conversation] = OrderedDict()
        self._lock = threading.Lock()

    def begin(self, request: A2ARequest) -> tuple[int, Optional[str]]:
        """Register a request. Returns (hop_count, request_id of an equivalent earlier request)."""
        key = request_key(request)
        with self._lock:
            conv = self._conversations.get(request.conversation_id)
            if conv is None:
                conv = _Conversation()
                self._conversations[request.conversation_id] = conv
                while len(self._conversations) > self._max:
                    self._conversations.popitem(last=False)
            self._conversations.move_to_end(request.conversation_id)
            earlier = conv.seen.get(key)
            if request.request_id not in conv.nodes:
                conv.hops += 1
                conv.nodes[request.request_id] = TraceNode(
                    request_id=request.request_id,
                    parent_request_id=request.parent_request_id,
                    sender_agent=request.sender_agent,
                    receiver_agent=request.receiver_agent,
                    task=request.task,
                    depth=request.depth,
                    started_at=datetime.now(timezone.utc).isoformat(),
                )
            duplicate_of = earlier if earlier not in (None, request.request_id) else None
            return conv.hops, duplicate_of

    def remember(self, request: A2ARequest) -> None:
        """Record an accepted request so later equivalent requests are flagged as duplicates."""
        with self._lock:
            conv = self._conversations.get(request.conversation_id)
            if conv is not None:
                conv.seen.setdefault(request_key(request), request.request_id)

    def finish(self, request: A2ARequest, response: A2AResponse, duration_ms: float) -> None:
        with self._lock:
            conv = self._conversations.get(request.conversation_id)
            node = conv.nodes.get(request.request_id) if conv else None
            if node is not None:
                node.status = response.status
                node.error_codes = [e.code.value for e in response.errors]
                node.duration_ms = round(duration_ms, 2)

    def get_trace(self, conversation_id: str) -> list[dict[str, Any]]:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            return [asdict(n) for n in conv.nodes.values()] if conv else []

    def get_tree(self, conversation_id: str) -> list[dict[str, Any]]:
        """Nested call tree rooted at requests without a parent."""
        nodes = self.get_trace(conversation_id)
        children: dict[Optional[str], list[dict[str, Any]]] = {}
        for node in nodes:
            children.setdefault(node["parent_request_id"], []).append(node)

        def build(node: dict[str, Any]) -> dict[str, Any]:
            return {**node, "children": [build(c) for c in children.get(node["request_id"], [])]}

        known = {n["request_id"] for n in nodes}
        roots = [n for n in nodes if n["parent_request_id"] is None or n["parent_request_id"] not in known]
        return [build(r) for r in roots]


trace_store = TraceStore(settings.A2A_TRACE_MAX_CONVERSATIONS)
