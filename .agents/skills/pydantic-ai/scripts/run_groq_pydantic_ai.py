"""
Demonstration: Running a Macrograph-AI Sector Agent with PydanticAI and Groq.

Demonstrates:
  1. Groq model provider integration (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`)
  2. Dependency injection with DuckDB connection via RunContext
  3. Structured output validation with Pydantic v2
  4. Tool definitions with self-correction via ModelRetry
  5. Strict citation enforcement

Requirements:
  pip install "pydantic-ai[groq]" duckdb
  export GROQ_API_KEY="gsk_..."

Usage:
  python scripts/run_groq_pydantic_ai.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Literal

import duckdb
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry


# --- Pydantic v2 Structured Output Schema ---

class MonetaryPolicyAssessment(BaseModel):
    policy_stance: Literal["accommodative", "neutral", "tightening"] = Field(
        description="Assessed monetary policy stance"
    )
    repo_rate: float = Field(description="Policy repo rate in percentage")
    inflation_cpi: float = Field(description="Current headline CPI rate in percentage")
    spread_pct: float = Field(description="Spread between repo rate and headline CPI (real rate)")
    summary: str = Field(description="Concise 2-sentence rationale")
    citation_source: str = Field(description="Attribution source for cited rates")


# --- Injected Dependencies ---

@dataclass
class MonetaryAgentDeps:
    db: duckdb.DuckDBPyConnection
    analyst_id: str


def setup_mock_database() -> duckdb.DuckDBPyConnection:
    """Setup in-memory DuckDB containing mock RBI and MOSPI indicators."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE policy_rates (
            rate_name VARCHAR,
            value_pct DOUBLE,
            effective_date DATE,
            source VARCHAR
        );
    """)
    conn.execute("""
        INSERT INTO policy_rates VALUES
            ('repo_rate', 6.50, '2024-10-09', 'RBI MPC Statement Oct 2024'),
            ('sdf_rate', 6.25, '2024-10-09', 'RBI MPC Statement Oct 2024'),
            ('msf_rate', 6.75, '2024-10-09', 'RBI MPC Statement Oct 2024');
    """)
    conn.execute("""
        CREATE TABLE inflation_metrics (
            metric_name VARCHAR,
            value_pct DOUBLE,
            period VARCHAR,
            source VARCHAR
        );
    """)
    conn.execute("""
        INSERT INTO inflation_metrics VALUES
            ('headline_cpi', 5.49, '2024-09', 'MOSPI CPI Press Release Sep 2024'),
            ('food_cpi', 9.24, '2024-09', 'MOSPI CPI Press Release Sep 2024');
    """)
    return conn


# --- Agent Definition ---

agent = Agent[MonetaryAgentDeps, MonetaryPolicyAssessment](
    "groq:llama-3.3-70b-versatile",
    deps_type=MonetaryAgentDeps,
    result_type=MonetaryPolicyAssessment,
    system_prompt=(
        "You are the Macrograph-AI Monetary Sector Specialist. "
        "Your task is to analyze India's current policy stance by querying policy rates and inflation. "
        "You must calculate the real interest rate (repo rate minus headline CPI) and strictly cite sources."
    ),
)


@agent.tool
async def fetch_policy_rate(ctx: RunContext[MonetaryAgentDeps], rate_name: str) -> dict[str, float | str]:
    """Retrieve official RBI policy rate from the database.

    Args:
        ctx: Injected database context.
        rate_name: Identifier of rate (e.g. 'repo_rate', 'sdf_rate', 'msf_rate').
    """
    clean_name = rate_name.lower().strip()
    # Parameterized DuckDB query (security requirement)
    query = "SELECT value_pct, source FROM policy_rates WHERE rate_name = ?"
    row = ctx.deps.db.execute(query, [clean_name]).fetchone()
    
    if not row:
        raise ModelRetry(f"Rate '{rate_name}' not found. Available rates: repo_rate, sdf_rate, msf_rate.")
    
    return {"value_pct": row[0], "source": row[1]}


@agent.tool
async def fetch_inflation_metric(ctx: RunContext[MonetaryAgentDeps], metric_name: str) -> dict[str, float | str]:
    """Retrieve official MOSPI inflation rate from the database.

    Args:
        ctx: Injected database context.
        metric_name: Identifier of metric (e.g. 'headline_cpi', 'food_cpi').
    """
    clean_name = metric_name.lower().strip()
    query = "SELECT value_pct, source FROM inflation_metrics WHERE metric_name = ?"
    row = ctx.deps.db.execute(query, [clean_name]).fetchone()

    if not row:
        raise ModelRetry(f"Metric '{metric_name}' not found. Available metrics: headline_cpi, food_cpi.")

    return {"value_pct": row[0], "source": row[1]}


@agent.result_validator
async def validate_assessment(
    ctx: RunContext[MonetaryAgentDeps],
    assessment: MonetaryPolicyAssessment,
) -> MonetaryPolicyAssessment:
    """Enforce domain consistency and attribution chain."""
    if not assessment.citation_source:
        raise ModelRetry("Attribution chain missing: please specify official RBI/MOSPI citations.")
    return assessment


async def main() -> None:
    if not os.environ.get("GROQ_API_KEY"):
        print("Note: GROQ_API_KEY environment variable not set. Running with TestModel fallback.")
        from pydantic_ai.models.test import TestModel
        with agent.override(model=TestModel()):
            db = setup_mock_database()
            deps = MonetaryAgentDeps(db=db, analyst_id="analyst-001")
            result = await agent.run(
                "Evaluate the current stance of RBI monetary policy given recent CPI inflation.",
                deps=deps,
            )
            print("Completed via TestModel:")
            print(result.data.model_dump_json(indent=2))
            return

    db = setup_mock_database()
    deps = MonetaryAgentDeps(db=db, analyst_id="analyst-001")

    print("Running Monetary Sector Agent on Groq (llama-3.3-70b-versatile)...")
    result = await agent.run(
        "Evaluate the current stance of RBI monetary policy given recent CPI inflation.",
        deps=deps,
    )

    print("\n--- Assessment Completed ---")
    print(f"Policy Stance:   {result.data.policy_stance.upper()}")
    print(f"Repo Rate:       {result.data.repo_rate}%")
    print(f"Headline CPI:    {result.data.inflation_cpi}%")
    print(f"Real Rate:       {result.data.spread_pct:.2f}%")
    print(f"Citations:       {result.data.citation_source}")
    print(f"Summary:         {result.data.summary}")
    print(f"\nToken Usage:     {result.usage()}")


if __name__ == "__main__":
    asyncio.run(main())
