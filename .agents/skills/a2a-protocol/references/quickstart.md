# A2A Protocol Quickstart — End-to-End Example for Macrograph-AI

This guide walks through building a complete A2A sector agent using the `a2a-sdk`, from AgentCard definition to accepting and streaming task results.

**Prerequisites:**
```bash
pip install a2a-sdk uvicorn httpx
```

---

## Step 1 — Install and Verify

```bash
pip install a2a-sdk
python -c "import a2a; print(a2a.__version__)"
```

---

## Step 2 — Define AgentCard and Skills

Every A2A server agent must declare what it can do via an `AgentCard` served at `/.well-known/agent.json`.

```python
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

def build_prices_agent_card() -> AgentCard:
    """Build the AgentCard for the Prices & Inflation sector agent."""
    return AgentCard(
        name="Prices & Inflation Agent",
        description=(
            "Owns and analyses all inflation indicators: CPI (headline, food, core, "
            "fuel, housing), WPI, and inflation expectations. Data from MOSPI and RBI DBIE."
        ),
        url="http://localhost:8001",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text", "data"],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
        skills=[
            AgentSkill(
                id="cpi-analysis",
                name="CPI Inflation Analysis",
                description="Decomposes CPI into food, fuel, core, and housing components.",
                tags=["cpi", "inflation", "mospi", "food-inflation"],
                examples=[
                    "What is the current headline CPI?",
                    "Decompose food vs core inflation.",
                    "Is food inflation rising or falling?",
                ],
            ),
        ],
    )
```

---

## Step 3 — Implement AgentExecutor

`AgentExecutor` is the bridge between the A2A protocol and your sector agent logic. The `execute` method receives the incoming task and sends back events via `EventQueue`.

```python
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message, new_data_artifact


class PricesAgentExecutor(AgentExecutor):
    """A2A server executor for the Prices & Inflation sector agent."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Handle incoming A2A task. Fetch inflation data via MCP tools,
        run analysis, and return a structured artifact.
        """
        # 1. Extract user question from the incoming message
        user_text = ""
        for part in context.message.parts or []:
            if hasattr(part.root, "text"):
                user_text = part.root.text
                break

        # 2. Invoke your sector agent logic (LangGraph node, tool chain, etc.)
        #    This is where the sector agent calls its FastMCP tools.
        result_text, result_data = await self._run_analysis(user_text)

        # 3. Enqueue the response artifact
        await event_queue.enqueue_event(
            new_agent_text_message(result_text)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation. Raise if not supported."""
        raise NotImplementedError("Prices Agent does not support task cancellation.")

    async def _run_analysis(self, query: str) -> tuple[str, dict]:
        """
        Placeholder: connect your LangGraph agent or MCP tool chain here.
        In production this calls the sector's FastMCP tools.
        """
        # Replace with: await prices_langgraph_node(state={"query": query})
        return (
            f"CPI Headline: 5.1% YoY. Food CPI: 4.8% YoY. [Source: MOSPI via Prices Agent MCP]",
            {"cpi_headline": 5.1, "cpi_food": 4.8, "source": "MOSPI"},
        )
```

---

## Step 4 — Start the A2A Server

```python
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


def build_a2a_app():
    """Build the Starlette ASGI application for the Prices sector A2A server."""
    agent_card = build_prices_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=PricesAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=agent_card,
        request_handler=request_handler,
    ).build()


if __name__ == "__main__":
    app = build_a2a_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

The server will now serve:
- `GET /.well-known/agent.json` — AgentCard discovery endpoint
- `POST /` — A2A JSON-RPC endpoint (handles `message/send`, `message/stream`, `tasks/get`, etc.)

---

## Step 5 — Verify AgentCard Discovery

```bash
curl http://localhost:8001/.well-known/agent.json | python -m json.tool
```

Expected output: the AgentCard JSON with `name`, `skills`, and `capabilities`.

---

## Step 6 — Send a Task (Client Side)

```python
import asyncio
import httpx
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams, Message, Part, TextPart


async def query_prices_agent(query: str) -> str:
    """Query the Prices Agent via A2A and return the result text."""
    agent_url = "http://localhost:8001"

    async with httpx.AsyncClient() as http_client:
        # Discover the agent
        resolver = A2ACardResolver(httpx_client=http_client, base_url=agent_url)
        agent_card = await resolver.get_agent_card()
        print(f"Connected to: {agent_card.name}")

        # Create client and send task
        client = A2AClient(httpx_client=http_client, agent_card=agent_card)
        response = await client.send_message(
            SendMessageRequest(
                id="req-001",
                params=MessageSendParams(
                    message=Message(
                        role="user",
                        parts=[Part(root=TextPart(text=query))],
                        messageId="msg-001",
                    )
                ),
            )
        )

        # Extract text from artifact
        task = response.root.result.root.task
        for artifact in task.artifacts or []:
            for part in artifact.parts or []:
                if hasattr(part.root, "text"):
                    return part.root.text
        return "[No text result returned]"


if __name__ == "__main__":
    result = asyncio.run(query_prices_agent("What is the current food inflation?"))
    print(result)
```

---

## Step 7 — Streaming Task (Client Side)

```python
async def stream_prices_agent(query: str) -> None:
    """Stream a task from the Prices Agent, printing events as they arrive."""
    agent_url = "http://localhost:8001"

    async with httpx.AsyncClient() as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=agent_url)
        agent_card = await resolver.get_agent_card()

        if not agent_card.capabilities.streaming:
            raise ValueError("Agent does not support streaming.")

        client = A2AClient(httpx_client=http_client, agent_card=agent_card)

        async with client.send_message_streaming(
            SendMessageRequest(
                id="req-stream-001",
                params=MessageSendParams(
                    message=Message(
                        role="user",
                        parts=[Part(root=TextPart(text=query))],
                        messageId="msg-stream-001",
                    )
                ),
            )
        ) as stream:
            async for event in stream:
                result = event.root.result
                if hasattr(result.root, "status"):
                    print(f"[STATUS] {result.root.status.state}")
                    if result.root.final:
                        break
                elif hasattr(result.root, "artifact"):
                    for part in result.root.artifact.parts or []:
                        if hasattr(part.root, "text"):
                            print(f"[ARTIFACT] {part.root.text}")
```

---

## Macrograph-AI: Integration Pattern

In Macrograph-AI, every sector agent follows this integration pattern:

```
1. Sector FastMCP server runs as a separate MCP endpoint
2. Sector A2A server wraps the LangGraph agent node
3. AgentExecutor.execute() → calls LangGraph node → LangGraph node calls FastMCP tools
4. Final findings returned as A2A Artifact with strict citation

Request flow:
Orchestrator
  → A2A: message/send to Prices Agent
    → PricesAgentExecutor.execute()
      → prices_langgraph_node(state)
        → get_cpi_data() via FastMCP
        → LLM reasoning with Groq
      → Artifact: { text: "Food CPI 4.8%...", data: {...} }
  ← A2A: Artifact received by Orchestrator
```

---

## Full Project Structure for a Sector A2A Server

```
backend/<sector>_sector/
├── __init__.py
├── mcp_server.py          # FastMCP data retrieval tools
├── agent.py               # LangGraph node (domain reasoning)
├── a2a_server.py          # A2A AgentExecutor + server entrypoint
├── agent_card.json        # Static AgentCard (optional, also served dynamically)
├── models.py              # Pydantic data models
└── api/
    └── app.py             # FastAPI sub-app mounted on main gateway
```
