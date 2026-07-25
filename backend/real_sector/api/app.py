"""FastAPI surface for individual LLM-callable Real Sector tools.

There is intentionally no cross-sector query orchestrator in this version.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ..agents.response_models import SectorResponse
from ..agents.tools import SectorToolInput, SectorToolRegistry
from ..services.pipeline import RealSectorPipeline


def create_app(pipeline: RealSectorPipeline | None = None) -> FastAPI:
    application = FastAPI(title="Macrograph AI — Real Sector Tools", version="0.1.0")
    active_pipeline = pipeline or RealSectorPipeline()
    registry = SectorToolRegistry(active_pipeline)

    @application.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", **active_pipeline.status()}

    @application.get("/real-sector/tools")
    def tool_definitions() -> list[dict[str, object]]:
        return registry.openai_functions()

    @application.post("/real-sector/tools/{tool_name}", response_model=SectorResponse)
    def invoke_tool(tool_name: str, payload: SectorToolInput) -> SectorResponse:
        try:
            return registry.invoke(tool_name, payload.model_dump())
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/real-sector/refresh")
    def refresh() -> dict[str, object]:
        tables = active_pipeline.refresh()
        return {"status": "refreshed", "tables": {name: len(table) for name, table in tables.items()}}

    return application


app = create_app()
