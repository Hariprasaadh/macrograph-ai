"""
Template: PydanticAI Analytical Sector Agent for Macrograph-AI.

Copy this file to backend/<sector>_sector/agent.py and adapt:
  1. Replace SECTOR_NAME with your sector identifier (e.g. 'prices', 'monetary', 'fiscal')
  2. Define your sector-specific Structured Output model
  3. Register your analytical tools and dependency types
  4. Plug the LangGraph node wrapper into the orchestrator graph

Design Contract:
  - Python 3.12, strict type annotations
  - Groq LLM as default provider (llama-3.3-70b-versatile or llama-3.1-8b-instant)
  - Pydantic v2 structured output model
  - Strict attribution chain: every indicator must cite source agent and data source
  - No inter-sector imports: cross-sector coordination uses A2A
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import duckdb
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from tenacity import retry, stop_after_attempt, wait_exponential

# REPLACE: When integrating with orchestrator, import OrchestratorState:
# from backend.core.orchestrator.state import OrchestratorState


# ==============================================================================
# 1. Sector Output Schema (Pydantic v2)
# ==============================================================================

class MetricFinding(BaseModel):
    metric_name: str = Field(description="Canonical metric name (e.g. cpi_headline, repo_rate)")
    latest_value: float = Field(description="Numerical value of the metric")
    unit: str = Field(description="Unit of measurement (e.g. %, index, INR Cr)")
    observation_period: str = Field(description="Period formatted YYYY-MM or YYYY-QX")
    trend: str = Field(description="Trend direction: 'increasing', 'decreasing', 'stable'")
    citation_source: str = Field(description="Official publication or data table cited")


class SectorAnalysisReport(BaseModel):
    sector_id: str = Field(description="Identifier of the sector agent (e.g. 'prices_sector')")
    key_findings: list[MetricFinding] = Field(description="List of extracted metric findings")
    macro_narrative: str = Field(description="Concise analytical synthesis of findings")
    risks_identified: list[str] = Field(default_factory=list, description="Forward-looking risks")
    data_quality_notes: Optional[str] = Field(None, description="Caveats, revisions, or data limits")


# ==============================================================================
# 2. Dependency Container
# ==============================================================================

@dataclass
class SectorAgentDeps:
    db: duckdb.DuckDBPyConnection
    sector_name: str = "prices"


# ==============================================================================
# 3. Agent Definition
# ==============================================================================

sector_agent = Agent[SectorAgentDeps, SectorAnalysisReport](
    "groq:llama-3.3-70b-versatile",
    deps_type=SectorAgentDeps,
    result_type=SectorAnalysisReport,
    retries=2,
    system_prompt=(
        "You are the Macrograph-AI analytical specialist for your sector. "
        "Analyze macro observations, query data tools, and output structured reports. "
        "Strict rule: Every metric must include its exact citation source and observation period."
    ),
)


# ==============================================================================
# 4. Sector Tools
# ==============================================================================

@sector_agent.tool
async def query_canonical_data(
    ctx: RunContext[SectorAgentDeps],
    indicator_code: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Fetch time-series observations from the sector DuckDB database.

    Args:
        ctx: Injected sector context.
        indicator_code: Canonical code for indicator (e.g. 'cpi_headline').
        limit: Number of recent periods to retrieve.
    """
    clean_code = indicator_code.lower().strip()
    # Parameterized DuckDB query (security rule: never use string concatenation)
    query = """
        SELECT period, value_num, unit, source_name 
        FROM sector_time_series 
        WHERE indicator = ? 
        ORDER BY period DESC 
        LIMIT ?
    """
    try:
        rows = ctx.deps.db.execute(query, [clean_code, limit]).fetchall()
        return [
            {"period": r[0], "value": r[1], "unit": r[2], "source": r[3]}
            for r in rows
        ]
    except Exception as e:
        raise ModelRetry(f"Failed to query indicator '{indicator_code}': {str(e)}")


@sector_agent.result_validator
async def validate_sector_report(
    ctx: RunContext[SectorAgentDeps],
    report: SectorAnalysisReport,
) -> SectorAnalysisReport:
    """Enforce data attribution and non-empty findings."""
    if not report.key_findings:
        raise ModelRetry("Report must contain at least one verified metric finding.")
    for finding in report.key_findings:
        if not finding.citation_source or len(finding.citation_source) < 4:
            raise ModelRetry(f"Metric '{finding.metric_name}' is missing a valid citation source.")
    return report


# ==============================================================================
# 5. LangGraph Node Wrapper
# ==============================================================================

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
async def run_sector_agent(prompt: str, deps: SectorAgentDeps) -> SectorAnalysisReport:
    """Execute sector agent with resilience retries."""
    result = await sector_agent.run(prompt, deps=deps)
    return result.data


async def sector_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node function to be plugged into the Orchestrator graph.

    Receives the current state, runs PydanticAI analysis, and updates state.
    """
    user_query = state.get("query", "Provide current sector overview")
    # Initialize or retrieve db connection from shared context/state
    db = state.get("db_conn") or duckdb.connect(":memory:")
    deps = SectorAgentDeps(db=db, sector_name="prices")

    report = await run_sector_agent(user_query, deps)
    
    # Return state update dictionary
    return {
        "sector_reports": {
            deps.sector_name: report.model_dump()
        }
    }
