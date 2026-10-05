"""A2A Prices executor delegates data retrieval to the same Prices MCP path."""
from __future__ import annotations

from core.protocols.a2a.models import (
    A2AArtifact, A2AMessage, A2AMessagePart, AgentCard, AgentSkill,
    RequestContext, TaskResponse, TaskState, TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
)
from core.protocols.a2a.lifecycle import AgentExecutor, EventQueue
from ..agent import prices_agent_node


class PricesSectorAgentExecutor(AgentExecutor):
    @classmethod
    def get_agent_card(cls, base_url: str = 'http://localhost:8000/prices-sector') -> AgentCard:
        return AgentCard(
            name='Prices & Inflation Sector Macroeconomic Agent', url=base_url,
            description='Retrieves Indian CPI, food/CFPI, rural, urban, combined, available CPI subgroups, and WPI inflation and monthly trends. MoSPI by default; IMF headline CPI only when explicitly requested. Categories depend on source metadata.',
            capabilities=['prices_sector', 'inflation', 'cpi', 'food_inflation', 'cfpi', 'rural_cpi', 'urban_cpi',
                          'combined_cpi', 'cpi_subgroups', 'wpi', 'historical_trends', 'mospi', 'imf_cpi'],
            skills=[AgentSkill(id='cpi_headline_analysis', name='CPI inflation data', description='Source-cited CPI headline and sector observations.'),
                    AgentSkill(id='subgroup_inflation_analysis', name='CPI subgroup data', description='Food/CFPI, housing, fuel, health and transport when the selected official series exposes them.'),
                    AgentSkill(id='prices_trends', name='CPI and WPI trends', description='Period-aligned monthly tables with series provenance.'),
                    AgentSkill(id='imf_cpi', name='IMF CPI data', description='Explicitly requested India monthly headline CPI from IMF MCP.')])

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        await event_queue.emit(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskState.WORKING,
                                                     metadata={'step': 'prices_mcp_query'}))
        result = await prices_agent_node({'query': context.query or ''})
        data = result['prices_sector_data']
        artifact = A2AArtifact(name='cpi_inflation_assessment', type='json', content={
            'sector': 'prices_sector', **data, 'indicators': data.get('observations', []),
            'citation': {'source_agent': 'prices_sector', 'observations': result['prices_sector_citations']}})
        await event_queue.emit(TaskArtifactUpdateEvent(task_id=context.task_id, artifact=artifact))
        return TaskResponse(task_id=context.task_id, status=TaskState.COMPLETED, artifacts=[artifact],
                            messages=[A2AMessage(role='assistant', parts=[A2AMessagePart(
                                kind='text', content=result['prices_sector_analysis'])])])
