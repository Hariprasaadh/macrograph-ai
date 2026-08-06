"""Demo script to run Real Sector A2A Agent and MCP tools directly."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from real_sector.agents.executor import RealSectorAgentExecutor
from real_sector.protocols.a2a_protocol import EventQueue, RequestContext, TaskRequest
from real_sector.protocols.mcp_protocol import handle_mcp_rpc
from real_sector.services.pipeline import RealSectorPipeline


async def main() -> None:
    print("=" * 70)
    print(" MACROGRAPH AI -- REAL SECTOR AGENT (A2A & MCP DEMO)")
    print("=" * 70)

    pipeline = RealSectorPipeline()
    executor = RealSectorAgentExecutor(pipeline)

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

    # 3. Submit an A2A Task
    print("\n" + "-" * 70)
    print("Executing A2A Task: 'Comprehensive Real Sector Macroeconomic Report'...")
    req = TaskRequest(
        query="Provide a comprehensive macroeconomic analysis of India's GDP, IIP, and CPI inflation.",
        skills_required=["real_sector_comprehensive_synthesis"]
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
