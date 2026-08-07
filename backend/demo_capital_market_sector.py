"""Demo script to run Capital Market Sector A2A Agent and MCP tools directly."""
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
from capital_market_sector.clients.market_data_client import CapitalMarketsDataClient
from capital_market_sector.protocols.a2a_protocol import EventQueue, RequestContext, TaskRequest
from capital_market_sector.protocols.mcp_protocol import handle_mcp_rpc


async def main() -> None:
    print("=" * 70)
    print(" MACROGRAPH AI -- CAPITAL MARKETS SECTOR AGENT (A2A & MCP DEMO)")
    print("=" * 70)

    client = CapitalMarketsDataClient()
    executor = CapitalMarketsAgentExecutor(client)

    # 1. Display Agent Card Capabilities
    card = executor.get_agent_card()
    print(f"\n[Agent Name]: {card.name}")
    print(f"[Description]: {card.description}")
    print("\n[Advertised Skills]:")
    for skill in card.skills:
        print(f"  - [{skill.id}]: {skill.name}")

    # 2. Test MCP JSON-RPC Protocol (tools/list)
    print("\n" + "-" * 70)
    print("Testing Model Context Protocol (MCP) -- tools/list:")
    mcp_list_response = handle_mcp_rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        executor.registry
    )
    tools = mcp_list_response["result"]["tools"]
    for t in tools:
        print(f"  * Tool: {t['name']} -> {t['description']}")

    # 3. Submit an A2A Task for the Capital Markets Sector
    print("\n" + "-" * 70)
    print("Executing A2A Task: 'Comprehensive Capital Markets Sector Report'...")
    print("Indicators: NIFTY 50, VIX, Corporate Earnings, IPO Activity, Mutual Fund Flows")
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
