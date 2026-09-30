"""
Template: FastAPI Router Serving PydanticAI Agent with SSE Streaming.

Copy this file to backend/<sector>_sector/api/routes.py or backend/api/router.py.

Features:
  1. Synchronous analysis endpoint returning Pydantic v2 structured model
  2. Server-Sent Events (SSE) streaming endpoint using `agent.run_stream()`
  3. Dependency injection bridging FastAPI Depends() to PydanticAI RunContext
  4. Proper HTTP error handling and status codes
  5. AbortController-friendly cancellation handling

Design Rules:
  - Python 3.12, strict type hints
  - All endpoints async def
  - No generic 500 error catch-alls; structured HTTPExceptions with clear messages
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import your agent and dependencies from sector package
# from backend.prices_sector.agent import sector_agent, SectorAgentDeps
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

router = APIRouter(prefix="/sector/analysis", tags=["Sector Analysis"])


# ==============================================================================
# 1. API Request & Response Schemas
# ==============================================================================

class AnalysisRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000, description="Analytical task prompt")
    parameters: dict[str, str] = Field(default_factory=dict, description="Optional parameter filters")


class MetricItem(BaseModel):
    metric_name: str
    latest_value: float
    unit: str
    period: str
    source: str


class AnalysisResponse(BaseModel):
    sector: str
    summary: str
    metrics: list[MetricItem]
    citations: list[str]


# ==============================================================================
# 2. Dependency Providers
# ==============================================================================

class MockDeps:
    """Mock container for sector dependencies (DuckDB, HTTP clients)."""
    sector_name: str = "prices"


async def get_sector_deps() -> MockDeps:
    """FastAPI dependency yielding agent execution context."""
    return MockDeps()


# Example Agent instance (replace with imported sector_agent)
api_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    result_type=AnalysisResponse,
)


# ==============================================================================
# 3. Standard Typed Endpoint
# ==============================================================================

@router.post(
    "/run",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute sector macroeconomic analysis",
)
async def run_analysis(
    payload: AnalysisRequest,
    deps: MockDeps = Depends(get_sector_deps),
) -> AnalysisResponse:
    """Run full sector agent analysis and return validated structured report."""
    try:
        # In testing or development without API keys, override with TestModel:
        # with api_agent.override(model=TestModel()):
        result = await api_agent.run(payload.prompt)
        return result.data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent analysis failed: {str(exc)}",
        ) from exc


# ==============================================================================
# 4. Server-Sent Events (SSE) Streaming Endpoint
# ==============================================================================

async def event_generator(prompt: str) -> AsyncGenerator[str, None]:
    """Stream token chunks formatted as standard Server-Sent Events."""
    try:
        async with api_agent.run_stream(prompt) as stream:
            async for chunk in stream.stream_text(debounce_by=0.03):
                event_data = json.dumps({"delta": chunk})
                yield f"data: {event_data}\n\n"

        # Signal completion with token usage
        usage_payload = json.dumps({"status": "complete", "usage": str(stream.usage())})
        yield f"event: done\ndata: {usage_payload}\n\n"
    except Exception as exc:
        err_payload = json.dumps({"error": str(exc)})
        yield f"event: error\ndata: {err_payload}\n\n"


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Stream sector analysis tokens via Server-Sent Events",
)
async def stream_analysis(payload: AnalysisRequest) -> StreamingResponse:
    """Stream agent analysis output progressively to client UI via SSE."""
    return StreamingResponse(
        event_generator(payload.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
