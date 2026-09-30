"""
Mock A2A Server for local development and testing.

Starts a fully functional A2A agent that serves its own AgentCard,
accepts tasks via message/send and message/stream, and returns
realistic simulated responses.

Usage:
    python scripts/mock_a2a_server.py --port 8099 --name "Test Agent" --sector prices

Requirements:
    pip install a2a-sdk uvicorn click
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

import click
import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SECTOR_MOCK_RESPONSES: dict[str, str] = {
    "prices": (
        "Mock analysis: Food CPI is +4.8% YoY, Headline CPI is +5.1% YoY. "
        "Core inflation (ex food & fuel) stands at 3.9%. [Mock data — Prices Agent]"
    ),
    "monetary": (
        "Mock analysis: RBI Repo Rate is 6.50%. SDF is 6.25%. MSF is 6.75%. "
        "Policy stance: withdrawal of accommodation. [Mock data — Monetary Agent]"
    ),
    "agriculture": (
        "Mock analysis: Kharif sowing is down 8% vs 5-year average due to 18% monsoon deficit. "
        "Tomato prices up +120% MoM. Onion prices up +60% MoM. [Mock data — Agriculture Agent]"
    ),
    "fiscal": (
        "Mock analysis: Fiscal deficit at 5.1% of GDP YTD. GST revenue at Rs 1.87 lakh crore in August. "
        "Capital expenditure at 48% of annual budget target. [Mock data — Fiscal Agent]"
    ),
    "external": (
        "Mock analysis: Forex reserves at USD 621.5 billion. Trade deficit at USD 23.8 billion in August. "
        "Current account deficit at 1.2% of GDP. [Mock data — External Agent]"
    ),
    "capital_market": (
        "Mock analysis: NIFTY 50 at 24,850. FII net inflows of Rs 12,400 crore MTD. "
        "10-year G-Sec yield at 6.95%. [Mock data — Capital Markets Agent]"
    ),
    "labour": (
        "Mock analysis: Urban unemployment rate at 7.1% (PLFS Q2 2025). EPFO net additions at 14.6 lakh "
        "in July 2025. LFPR at 42.3%. [Mock data — Labour Agent]"
    ),
    "real": (
        "Mock analysis: GDP growth at 6.7% in Q1 FY26. GVA growth at 6.4%. "
        "Industry GVA grew 7.2%, Services 8.1%. [Mock data — Real Sector Agent]"
    ),
    "finance": (
        "Mock analysis: Credit growth at 12.3% YoY. Gross NPA ratio at 3.1%. "
        "Deposit growth at 10.8% YoY. NBFC sector credit at Rs 36.8 lakh crore. [Mock data — Finance Agent]"
    ),
    "services": (
        "Mock analysis: Services PMI at 58.4 (expansion). IT sector revenue growth at 9.2% in Q1 FY26. "
        "Services GVA growth at 8.1% in Q1 FY26. [Mock data — Services Agent]"
    ),
    "default": (
        "Mock agent response: This is a simulated A2A response for testing. "
        "Replace with real sector agent logic connected to FastMCP data sources."
    ),
}


class MockAgentExecutor(AgentExecutor):
    """Mock AgentExecutor that returns pre-defined sector-specific responses."""

    def __init__(self, sector: str) -> None:
        self._sector = sector
        self._response = SECTOR_MOCK_RESPONSES.get(sector, SECTOR_MOCK_RESPONSES["default"])

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Return a mock sector analysis response."""
        user_text = ""
        for part in context.message.parts or []:
            if hasattr(part.root, "text"):
                user_text = part.root.text
                break

        logger.info("Mock agent received task. Query: %s", user_text[:100])

        # Simulate brief processing delay
        await asyncio.sleep(0.3)

        response = f"Query received: '{user_text}'\n\n{self._response}"
        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Mock cancel — always raises as mock agents do not support cancellation."""
        raise NotImplementedError("Mock agent does not support task cancellation.")


def build_mock_agent_card(name: str, sector: str, port: int) -> AgentCard:
    """Build an AgentCard for the mock agent."""
    descriptions: dict[str, str] = {
        "prices": "Mock Prices Agent: simulates CPI, WPI, and inflation analysis.",
        "monetary": "Mock Monetary Agent: simulates RBI policy and liquidity analysis.",
        "agriculture": "Mock Agriculture Agent: simulates crop, rainfall, and mandi price analysis.",
        "default": "Mock A2A Agent for local testing of the Agent2Agent protocol.",
    }
    return AgentCard(
        name=name,
        description=descriptions.get(sector, descriptions["default"]),
        url=f"http://localhost:{port}",
        version="0.1.0-mock",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
        skills=[
            AgentSkill(
                id=f"{sector}-mock",
                name=f"Mock {sector.replace('_', ' ').title()} Analysis",
                description=f"Returns simulated {sector} sector analysis for local testing.",
                tags=["mock", "testing", sector],
                examples=[
                    f"What is the current {sector} status?",
                    "Give me a summary.",
                ],
            )
        ],
    )


@click.command()
@click.option("--port", default=8099, help="Port to run the mock A2A server on.", type=int)
@click.option("--name", default="Mock A2A Agent", help="Agent display name.")
@click.option(
    "--sector",
    default="default",
    help="Sector to simulate: prices, monetary, agriculture, fiscal, external, capital_market, labour, real, finance, services.",
)
def main(port: int, name: str, sector: str) -> None:
    """Start a local mock A2A server for testing."""
    logger.info("Starting mock A2A server: name=%s, sector=%s, port=%d", name, sector, port)

    agent_card = build_mock_agent_card(name=name, sector=sector, port=port)
    request_handler = DefaultRequestHandler(
        agent_executor=MockAgentExecutor(sector=sector),
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=agent_card,
        request_handler=request_handler,
    ).build()

    logger.info(
        "Mock A2A server ready. AgentCard: http://localhost:%d/.well-known/agent.json",
        port,
    )
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
