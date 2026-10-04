"""Demo script to run Capital Market Sector A2A Agent and FastMCP tools directly."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from capital_market_sector.agents.executor import CapitalMarketsAgentExecutor
from capital_market_sector.mcp_server import mcp_server
from core.protocols.a2a.lifecycle import EventQueue
from core.protocols.a2a.models import RequestContext, TaskRequest


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 70)
    print(" MACROGRAPH AI -- CAPITAL MARKETS SECTOR AGENT (A2A & MCP DEMO)")
    print("=" * 70)

    executor = CapitalMarketsAgentExecutor()

    # 1. Display Agent Card Capabilities
    card = executor.get_agent_card()
    print(f"\n[Agent Name]: {card.name}")
    print(f"[Description]: {card.description}")
    print("\n[Advertised Skills]:")
    for skill in card.skills:
        print(f"  - [{skill.id}]: {skill.name} -> {skill.description}")

    # 2. Test FastMCP Protocol Tools
    print("\n" + "-" * 70)
    print("Testing Model Context Protocol (FastMCP) Tools:")
    tools = await mcp_server.list_tools()
    print(f"Total FastMCP Tools registered: {len(tools)}")
    for t in tools:
        print(f"  * Tool: {t.name} -> {t.description}")

    # 3. Submit an A2A Task for the Capital Markets Sector
    print("\n" + "-" * 70)
    print("Executing A2A Task: 'Comprehensive Capital Markets Sector Report'...")
    print("Covering: NIFTY 50, VIX, G-Sec Yields, Mutual Fund SIPs, FPI Flows, Valuations")
    req = TaskRequest(
        query="Provide a comprehensive analysis of NIFTY 50, India VIX, corporate earnings, IPO activity, and mutual fund flows.",
        skills_required=[]
    )
    context = RequestContext(task_id=req.task_id, request=req)
    queue = EventQueue()

    response = await executor.execute(context, queue)

    print(f"\nTask Status: {response.status.value.upper()}")
    print(f"Total Artifacts Generated: {len(response.artifacts)}")

    for artifact in response.artifacts:
        print("\n" + "=" * 50)
        print(f"ARTIFACT: {artifact.name} (Type: {artifact.type})")
        print("=" * 50)
        if artifact.type == "markdown":
            print(artifact.content)
        else:
            print(json.dumps(artifact.content, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
