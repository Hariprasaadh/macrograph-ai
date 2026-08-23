"""State definitions for LangGraph Macroeconomic Orchestrator."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class OrchestratorState(TypedDict, total=False):
    """The central state passed across LangGraph nodes."""
    query: str
    scenario_shock: Optional[Dict[str, Any]]
    decomposed_tasks: List[Dict[str, Any]]
    target_sectors: List[str]
    collected_observations: List[Dict[str, Any]]
    agent_analyses: List[Dict[str, Any]]
    causal_paths: List[Dict[str, Any]]
    scenario_result: Optional[Dict[str, Any]]
    mermaid_diagram: str
    final_report: str
    citations: List[Dict[str, Any]]
    confidence_score: float
    status: str
