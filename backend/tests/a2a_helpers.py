"""Isolated A2A runtime for tests: private registry, trace store, server and fake agents."""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from core.protocols.a2a.client import A2AClient, InProcessTransport
from core.protocols.a2a.messages import (
    A2ACallContext,
    A2ARequest,
    HandlerOutput,
    IndicatorObservation,
    IndicatorSignal,
    SourceProvenance,
)
from core.protocols.a2a.middleware import DelegationGuard
from core.protocols.a2a.models import AgentCard, AgentSkill
from core.protocols.a2a.registry import AgentRegistry
from core.protocols.a2a.server import A2AServer
from core.protocols.a2a.trace import TraceStore

Handler = Callable[[A2ARequest, A2ACallContext], Awaitable[HandlerOutput]]


class Runtime:
    def __init__(self, max_depth: int = 5, max_hops: int = 25, timeout: float = 5.0) -> None:
        self.registry = AgentRegistry()
        self.trace = TraceStore(max_conversations=50)
        self.server = A2AServer(
            self.registry, self.trace, DelegationGuard(max_depth, max_hops), default_timeout=timeout
        )

    def add_agent(
        self,
        agent_id: str,
        capabilities: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
    ) -> AgentCard:
        card = AgentCard(
            name=f"{agent_id} card", description=f"{agent_id} test agent", url="http://test",
            agent_id=agent_id, capabilities=capabilities or [],
            skills=[AgentSkill(id=f"{agent_id}_skill", name=agent_id, description="d", tags=tags or [])],
            metadata={"keywords": keywords or []},
        )
        self.registry.register(card)
        return card

    def add_handler(self, agent_id: str, task: str, handler: Handler, **kwargs) -> None:
        self.server.register_handler(agent_id, task, handler, **kwargs)

    def client(self, agent_id: str, **kwargs) -> A2AClient:
        return A2AClient(
            agent_id, transport=InProcessTransport(self.server), registry=self.registry, **kwargs
        )


def source(name: str = "RBI DBIE", table: str = "Table 1", period: str = "2026-05") -> SourceProvenance:
    return SourceProvenance(
        source_name=name, source_url="https://example.test/data", dataset="Dataset X", table=table,
        reporting_period=period, page_or_section="p.4", record_reference="row-7",
    )


def signal_output(value: float = 5.25, src: Optional[SourceProvenance] = None) -> HandlerOutput:
    obs = IndicatorObservation(
        indicator_id="in.macro.monetary.repo_rate", label="Repo", value=value, unit="%",
        observation_period="2026-05", data_status="live",
    )
    return HandlerOutput(
        result=IndicatorSignal(owner_agent="monetary_sector", observations=[obs]).model_dump(mode="json"),
        sources=[src or source()],
    )
