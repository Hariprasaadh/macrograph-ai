"""Dynamic Agent Registry for Multi-Agent A2A Discovery, Routing, and Execution."""
from __future__ import annotations

from typing import Dict, List, Optional
from .models import AgentCard, TaskRequest, TaskResponse, TaskState
from .lifecycle import AgentExecutor, TaskManager


class AgentRegistry:
    """Central registry tracking active A2A domain agents, capability indexing, and execution routers."""

    def __init__(self) -> None:
        self._cards: Dict[str, AgentCard] = {}
        self._executors: Dict[str, AgentExecutor] = {}
        self._skill_index: Dict[str, str] = {}  # skill_id -> agent_name
        self._ids: Dict[str, str] = {}  # agent_id -> card name
        self._task_manager = TaskManager()

    def register(self, card: AgentCard, executor: Optional[AgentExecutor] = None) -> None:
        self._cards[card.name] = card
        if executor:
            self._executors[card.name] = executor
        if card.agent_id:
            self._ids[card.agent_id] = card.name
        for skill in card.skills:
            self._skill_index[skill.id] = card.name

    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        """Look up by card name or stable agent_id."""
        return self._cards.get(agent_name) or self._cards.get(self._ids.get(agent_name, ""))

    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Look up a card by its stable agent_id (e.g. finance_sector)."""
        name = self._ids.get(agent_id)
        return self._cards.get(name) if name else None

    def find_by_capability(self, capability: str) -> List[AgentCard]:
        """Cards advertising `capability` as a capability tag, supported task, or skill id."""
        wanted = capability.lower()
        return [
            card for card in self._cards.values()
            if wanted in {c.lower() for c in card.capabilities}
            or wanted in {t.lower() for t in card.supported_tasks}
            or wanted in {s.id.lower() for s in card.skills}
        ]

    def agent_ids(self) -> List[str]:
        return list(self._ids)

    def list_agents(self) -> List[AgentCard]:
        return list(self._cards.values())

    def list_agent_cards(self) -> List[AgentCard]:
        return list(self._cards.values())

    def find_agent_for_skill(self, skill_id: str) -> Optional[AgentCard]:
        agent_name = self._skill_index.get(skill_id)
        if agent_name:
            return self._cards.get(agent_name)
        return None

    async def execute_task_async(self, agent_name: str, request: TaskRequest) -> TaskResponse:
        """Executes a task asynchronously through the standard A2A TaskManager lifecycle."""
        executor = self._executors.get(agent_name)
        if not executor:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskState.FAILED,
                messages=[],
                artifacts=[],
                error=f"No active A2A executor registered for '{agent_name}'."
            )
        return await self._task_manager.run_task(executor, request, background=False)


# Global agent registry singleton
registry = AgentRegistry()
agent_registry = registry
