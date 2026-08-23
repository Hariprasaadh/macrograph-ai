"""Dynamic Agent Registry for Multi-Agent A2A Discovery and Routing."""
from __future__ import annotations

from typing import Dict, List, Optional
from .models import AgentCard, AgentSkill


class AgentRegistry:
    """Central registry tracking active A2A domain agents and capability indexing."""

    def __init__(self) -> None:
        self._cards: Dict[str, AgentCard] = {}
        self._skill_index: Dict[str, str] = {}  # skill_id -> agent_name

    def register(self, card: AgentCard) -> None:
        self._cards[card.name] = card
        for skill in card.skills:
            self._skill_index[skill.id] = card.name

    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        return self._cards.get(agent_name)

    def list_agent_cards(self) -> List[AgentCard]:
        return list(self._cards.values())

    def find_agent_for_skill(self, skill_id: str) -> Optional[AgentCard]:
        agent_name = self._skill_index.get(skill_id)
        if agent_name:
            return self._cards.get(agent_name)
        return None

    def route_query_skills(self, query: str) -> List[str]:
        """Heuristic skill match for query routing fallback."""
        matched_skills: List[str] = []
        q_lower = query.lower()
        for agent_name, card in self._cards.items():
            for skill in card.skills:
                # Check tags or examples
                if any(tag.lower() in q_lower for tag in skill.tags):
                    matched_skills.append(skill.id)
                elif any(kw in q_lower for kw in skill.name.lower().split()):
                    matched_skills.append(skill.id)
        return list(set(matched_skills))


# Global agent registry singleton
registry = AgentRegistry()
