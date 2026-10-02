"""Tests for MoSPI FastMCP Client and PricesSectorAgentExecutor."""
from __future__ import annotations

import pytest
import asyncio
from core.protocols.a2a.models import RequestContext
from core.protocols.a2a.lifecycle import EventQueue
from prices_sector.agents.executor import PricesSectorAgentExecutor


@pytest.mark.asyncio
async def test_prices_agent_card():
    card = PricesSectorAgentExecutor.get_agent_card()
    assert card.name == "Prices & Inflation Sector Macroeconomic Agent"
    assert "cpi" in card.capabilities
    assert any(s.id == "cpi_headline_analysis" for s in card.skills)


@pytest.mark.asyncio
async def test_prices_agent_execute():
    executor = PricesSectorAgentExecutor()
    context = RequestContext(
        task_id="test-prices-task-01",
        query="What is the latest headline CPI and food inflation in India?",
    )
    event_queue = EventQueue()
    response = await executor.execute(context, event_queue)

    assert response.status.value == "completed"
    assert len(response.artifacts) == 1
    artifact = response.artifacts[0]
    assert artifact.name == "cpi_inflation_assessment"
    assert "indicators" in artifact.content
    assert "citation" in artifact.content
    assert artifact.content["citation"]["source_agent"] == "prices_sector"
