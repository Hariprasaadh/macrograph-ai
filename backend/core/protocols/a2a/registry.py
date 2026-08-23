"""Dynamic Agent Registry for Multi-Agent A2A Discovery, Routing, and Execution."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from .models import AgentCard, AgentSkill, TaskRequest, TaskResponse, TaskState
from .lifecycle import AgentExecutor, TaskManager


class AgentRegistry:
    """Central registry tracking active A2A domain agents, capability indexing, and execution routers."""

    def __init__(self) -> None:
        self._cards: Dict[str, AgentCard] = {}
        self._executors: Dict[str, AgentExecutor] = {}
        self._skill_index: Dict[str, str] = {}  # skill_id -> agent_name
        self._task_manager = TaskManager()

    def register(self, card: AgentCard, executor: Optional[AgentExecutor] = None) -> None:
        self._cards[card.name] = card
        if executor:
            self._executors[card.name] = executor
        for skill in card.skills:
            self._skill_index[skill.id] = card.name

    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        return self._cards.get(agent_name)

    def list_agents(self) -> List[AgentCard]:
        return list(self._cards.values())

    def list_agent_cards(self) -> List[AgentCard]:
        return list(self._cards.values())

    def find_agent_for_skill(self, skill_id: str) -> Optional[AgentCard]:
        agent_name = self._skill_index.get(skill_id)
        if agent_name:
            return self._cards.get(agent_name)
        return None

    def route_query_skills(self, query: str) -> List[str]:
        """Heuristic skill match for query routing."""
        matched_skills: List[str] = []
        q_lower = query.lower()
        for agent_name, card in self._cards.items():
            for skill in card.skills:
                if any(tag.lower() in q_lower for tag in skill.tags):
                    matched_skills.append(skill.id)
                elif any(kw in q_lower for kw in skill.name.lower().split()):
                    matched_skills.append(skill.id)
        return list(set(matched_skills))

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

    def execute_task(self, agent_name: str, request: TaskRequest) -> TaskResponse:
        """Synchronous wrapper for A2A task execution."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.execute_task_async(agent_name, request))
        else:
            return loop.run_until_complete(self.execute_task_async(agent_name, request))


# Global agent registry singleton
registry = AgentRegistry()
agent_registry = registry
