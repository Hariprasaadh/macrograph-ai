"""
Template: A2A Sector Agent Server for Macrograph-AI.

Copy this file to backend/<sector>_sector/a2a_server.py and fill in:
  1. SECTOR_NAME — human-readable sector name
  2. SECTOR_PORT — unique port for this sector agent
  3. SECTOR_SKILLS — skills this sector exposes
  4. <Sector>AgentExecutor.execute() — connect your LangGraph node or MCP tools

Each sector agent runs as a standalone A2A server that the Orchestrator
discovers and delegates tasks to via the A2A protocol.

Architecture:
  Orchestrator → A2A → <Sector>AgentExecutor → LangGraph node → FastMCP tools → external APIs
"""
from __future__ import annotations

import logging

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURE: Fill in sector-specific values
# ---------------------------------------------------------------------------

SECTOR_NAME = "Prices & Inflation"          # e.g. "Monetary & Liquidity"
SECTOR_PORT = 8001                           # unique port per sector
SECTOR_DESCRIPTION = (
    "Owns and analyses all inflation indicators: CPI (headline, food, core, "
    "fuel, housing), WPI, and inflation expectations. Data from MOSPI and RBI DBIE."
)

SECTOR_SKILLS: list[AgentSkill] = [
    AgentSkill(
        id="cpi-analysis",
        name="CPI Inflation Analysis",
        description="Decomposes CPI into food, fuel, core, and housing components with trend analysis.",
        tags=["cpi", "inflation", "mospi", "food-inflation", "india"],
        examples=[
            "What is the current headline CPI?",
            "Decompose food vs core inflation.",
            "Is food inflation rising or falling?",
        ],
    ),
    # Add additional skills here
]

# ---------------------------------------------------------------------------
# IMPLEMENT: Sector AgentExecutor
# ---------------------------------------------------------------------------


class SectorAgentExecutor(AgentExecutor):
    """
    A2A AgentExecutor for the <Sector> sector agent.

    Bridges the A2A protocol and the sector's LangGraph node.
    Fetches data via FastMCP tools, reasons using the Groq LLM,
    and returns a strictly cited artifact.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Handle an incoming A2A task.

        Steps:
        1. Extract user question from the A2A Message.
        2. Invoke the sector LangGraph node (which calls FastMCP tools internally).
        3. Send the analysis result back as an A2A artifact.
        """
        # Step 1: Extract user input
        user_text = ""
        for part in context.message.parts or []:
            if hasattr(part.root, "text"):
                user_text = part.root.text
                break

        logger.info("[%s] Received task: %s", SECTOR_NAME, user_text[:120])

        # Step 2: Invoke sector agent logic
        # REPLACE THIS with your actual LangGraph node call:
        # from backend.prices_sector.agent import prices_agent_node
        # from backend.core.orchestrator.state import OrchestratorState
        # result_state = await prices_agent_node(OrchestratorState(user_query=user_text))
        # result_text = result_state["prices_findings"]
        result_text = f"[PLACEHOLDER] {SECTOR_NAME} analysis for: '{user_text}'"

        # Step 3: Return result as A2A artifact
        await event_queue.enqueue_event(new_agent_text_message(result_text))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation. Raise NotImplementedError if not supported."""
        raise NotImplementedError(f"{SECTOR_NAME} Agent does not support task cancellation.")


# ---------------------------------------------------------------------------
# SERVER: AgentCard + A2A Application
# ---------------------------------------------------------------------------


def build_agent_card() -> AgentCard:
    """Build the AgentCard for this sector agent."""
    return AgentCard(
        name=f"{SECTOR_NAME} Agent",
        description=SECTOR_DESCRIPTION,
        url=f"http://localhost:{SECTOR_PORT}",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text", "data"],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
        skills=SECTOR_SKILLS,
        # Uncomment for authenticated agents:
        # authentication={"schemes": ["Bearer"]},
    )


def build_app():
    """Build the A2A Starlette ASGI application."""
    return A2AStarletteApplication(
        agent_card=build_agent_card(),
        request_handler=DefaultRequestHandler(
            agent_executor=SectorAgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    ).build()


if __name__ == "__main__":
    logger.info("Starting %s A2A agent on port %d", SECTOR_NAME, SECTOR_PORT)
    uvicorn.run(build_app(), host=settings.HOST, port=SECTOR_PORT)
