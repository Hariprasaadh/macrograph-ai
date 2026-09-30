"""
PydanticAI Agent Verification Utility.

Validates that a PydanticAI Agent definition is structurally sound, conforms
to result schemas, handles dependencies properly, and can run deterministically
under TestModel (offline) or against live LLM APIs.

Usage:
    python scripts/verify_pydantic_ai_agent.py --mode offline
    python scripts/verify_pydantic_ai_agent.py --mode live --model groq:llama-3.3-70b-versatile
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.test import TestModel


class MacroVerificationReport(BaseModel):
    agent_name: str = Field(description="Name or sector of the verified agent")
    status: str = Field(description="Operational status: healthy, warning, or error")
    checks_passed: int = Field(description="Count of passed verification steps")
    sample_metric: str = Field(description="Name of macroeconomic metric tested")
    citation: str = Field(description="Attribution source cited")


@dataclass
class VerificationDeps:
    environment: str
    max_threshold: float = 100.0


def build_test_agent(model_spec: str) -> Agent[VerificationDeps, MacroVerificationReport]:
    agent = Agent[VerificationDeps, MacroVerificationReport](
        model_spec,
        deps_type=VerificationDeps,
        result_type=MacroVerificationReport,
        system_prompt=(
            "You are a verification harness for Macrograph-AI sector agents. "
            "Validate indicators, ensure strict source citations, and return structured reports."
        ),
    )

    @agent.tool
    async def probe_metric(ctx: RunContext[VerificationDeps], metric_name: str) -> float:
        """Probe an economic metric value to test tool calling."""
        if not metric_name:
            raise ModelRetry("metric_name cannot be empty. Specify an indicator like 'cpi' or 'repo_rate'.")
        return 6.50

    @agent.result_validator
    async def validate_report(
        ctx: RunContext[VerificationDeps],
        report: MacroVerificationReport,
    ) -> MacroVerificationReport:
        if not report.citation:
            raise ModelRetry("Report must include a non-empty citation.")
        return report

    return agent


async def run_verification(mode: str, model_name: str) -> None:
    print(f"=== Starting PydanticAI Agent Verification [Mode: {mode.upper()}] ===")
    
    deps = VerificationDeps(environment=mode)
    
    if mode == "offline":
        print("Using TestModel (no API keys or network calls required)...")
        agent = build_test_agent("test")
        with agent.override(model=TestModel()):
            result = await agent.run(
                "Run standard health check for Monetary sector agent.",
                deps=deps,
            )
            print("Run completed successfully!")
            print(f"Data parsed: {result.data.model_dump()}")
            print(f"Usage summary: {result.usage()}")
    else:
        if "groq" in model_name and not os.environ.get("GROQ_API_KEY"):
            print("ERROR: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
            sys.exit(1)
        if "openai" in model_name and not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
            sys.exit(1)

        print(f"Connecting to live model: {model_name}...")
        agent = build_test_agent(model_name)
        result = await agent.run(
            "Execute verification for Inflation sector. Probe 'cpi' metric and cite MOSPI.",
            deps=deps,
        )
        print("Live agent run completed successfully!")
        print(f"Result model: {result.data.model_dump_json(indent=2)}")
        print(f"Token usage: {result.usage()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PydanticAI agent verification script")
    parser.add_argument(
        "--mode",
        choices=["offline", "live"],
        default="offline",
        help="Run offline using TestModel, or live against an LLM provider",
    )
    parser.add_argument(
        "--model",
        default="groq:llama-3.3-70b-versatile",
        help="Provider model identifier (e.g. groq:llama-3.3-70b-versatile or openai:gpt-4o)",
    )
    args = parser.parse_args()

    asyncio.run(run_verification(args.mode, args.model))


if __name__ == "__main__":
    main()
