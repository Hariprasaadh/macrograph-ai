# A2A Protocol Reference — Overview, Key Concepts, and Macrograph Context

**Source:** https://a2a-protocol.org | https://github.com/a2aproject/A2A | https://github.com/a2aproject/a2a-python  
**SDK Package:** `a2a-sdk >= 1.1.0` | `pip install a2a-sdk`  
**Spec Version:** A2A v1.0 (2025/2026, now governed by the Agentic AI Foundation)

---

## What is A2A?

The **Agent2Agent (A2A) Protocol** is an open standard that enables independent AI agent systems to securely communicate, delegate tasks, and collaborate without exposing their internal state, memory, or tool implementations.

Key design goals:
- **Interoperability**: Agents built on different frameworks (LangGraph, CrewAI, Google ADK, AutoGen) can communicate without framework-specific adapters.
- **Opacity**: Agents never expose internal memory, tool chains, or business logic to peers. Only inputs and outputs cross the boundary.
- **Scalability**: Built on JSON-RPC 2.0 over HTTPS — compatible with enterprise security (mTLS, OAuth2, API keys).
- **Streaming**: Native support for long-running tasks via Server-Sent Events (SSE).

---

## A2A vs MCP — Critical Distinction

| Dimension | A2A | MCP (FastMCP) |
| :--- | :--- | :--- |
| **What it connects** | Agent ↔ Agent | Agent ↔ Tool/Data Source |
| **Purpose** | Reasoning delegation & collaboration | Data retrieval & tool invocation |
| **Who uses it** | Orchestrator ↔ Sector Agents | Sector Agents ↔ Government APIs, DuckDB, Qdrant |
| **Data direction** | Structured analytical findings | Raw indicator data, query results |
| **Protocol** | JSON-RPC 2.0 over HTTPS + SSE | FastMCP decorator tool API |

**In Macrograph-AI:**
- The Orchestrator uses **A2A** to delegate subtasks to sector agents and receive their analytical findings.
- Sector agents use **FastMCP** to fetch raw data from external sources (MOSPI, RBI DBIE, Agmarknet, etc.).

> **Critical Rule:** An agent must NEVER use A2A to fetch raw data, and must NEVER use FastMCP to share agent findings. These are two separate, non-interchangeable layers.

---

## Transport & Wire Format

A2A uses **JSON-RPC 2.0 over HTTP(S)**. Every request has this envelope:

```json
{
  "jsonrpc": "2.0",
  "id": "req-abc-123",
  "method": "message/send",
  "params": { ... }
}
```

Error responses use standard JSON-RPC error codes:
- `-32700` — Parse error (malformed JSON)
- `-32600` — Invalid request (missing required fields)
- `-32601` — Method not found
- `-32603` — Internal error
- `-32001` — Task not found (A2A specific)

---

## Core Data Model

### AgentCard
The public identity manifest of an agent. Served at `/.well-known/agent.json`. Other agents and the Orchestrator use this to discover capabilities and connection requirements.

```json
{
  "name": "Prices & Inflation Agent",
  "description": "Analyses CPI, WPI, core and food inflation using MOSPI data.",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "cpi-analysis",
      "name": "CPI Inflation Analysis",
      "description": "Analyses CPI headline and component inflation.",
      "tags": ["inflation", "cpi", "mospi"],
      "examples": ["What is the current headline CPI?", "Decompose food inflation."]
    }
  ],
  "authentication": {
    "schemes": ["Bearer"]
  }
}
```

### AgentSkill
A declared capability within the AgentCard. Agents can expose one or more skills with distinct IDs that the Orchestrator uses for routing.

### Task
The fundamental unit of work. A task is created by a client agent and processed by a server agent. Tasks are stateful and follow a strict state machine.

```
submitted → working → [ input-required → working ] → completed
                    ↘ failed
                    ↘ canceled
```

| State | Meaning |
| :--- | :--- |
| `submitted` | Task received and queued |
| `working` | Agent is actively processing |
| `input-required` | Agent needs more information from caller |
| `completed` | Task finished; artifacts are available |
| `failed` | Unrecoverable error during execution |
| `canceled` | Task was canceled via `tasks/cancel` |

### Message
A unit of communication within a task. Contains one or more `Part` objects.

### Part
The content unit inside a `Message` or `Artifact`. Types:
- `TextPart` — plain text content (`{"kind": "text", "text": "..."}`)
- `DataPart` — structured JSON payload (`{"kind": "data", "data": {...}}`)
- `FilePart` — binary file reference (`{"kind": "file", "file": {...}}`)

### Artifact
The output container attached to a completed task. An agent sends its findings as an Artifact containing one or more Parts.

```json
{
  "name": "inflation-analysis",
  "parts": [
    {
      "kind": "text",
      "text": "Food CPI is +4.8% YoY [Source: Prices Agent via MOSPI MCP]"
    },
    {
      "kind": "data",
      "data": {
        "cpi_food": 4.8,
        "cpi_headline": 5.1,
        "source": "MOSPI",
        "period": "2025-08"
      }
    }
  ]
}
```

---

## Protocol Methods (JSON-RPC Methods)

| Method | Direction | Purpose |
| :--- | :--- | :--- |
| `message/send` | Client → Server | Send a task and wait for synchronous response |
| `message/stream` | Client → Server | Send a task and receive SSE streaming response |
| `tasks/get` | Client → Server | Poll task status by `taskId` |
| `tasks/cancel` | Client → Server | Cancel an in-progress task |
| `tasks/resubscribe` | Client → Server | Resume a dropped SSE stream |
| `tasks/pushNotificationConfig/set` | Client → Server | Register webhook callback for push delivery |
| `tasks/pushNotificationConfig/get` | Client → Server | Retrieve registered push config |
| `agent/getAuthenticatedExtendedCard` | Client → Server | Fetch full AgentCard (requires auth) |

---

## Streaming — SSE Event Types

When using `message/stream`, the server sends a series of SSE events until the task reaches a terminal state.

| Event Type | When Sent | Contains |
| :--- | :--- | :--- |
| `TaskStatusUpdateEvent` | On status transitions | `taskId`, `status.state`, `final: bool` |
| `TaskArtifactUpdateEvent` | When partial artifacts are ready | `taskId`, `artifact` (partial or complete) |

**Critical rule:** Never close an SSE stream before receiving `TaskStatusUpdateEvent` with `final: true`. Closing early discards the final artifact.

---

## Authentication Schemes

| Scheme | Header | When to Use |
| :--- | :--- | :--- |
| `Bearer` | `Authorization: Bearer <token>` | JWT-based auth (OAuth2 / API gateway) |
| `ApiKey` | `X-API-Key: <key>` | Simple API key auth |
| `None` | — | Internal-only agents on trusted network |

Always check `AgentCard.authentication.schemes` before sending a task. Never assume unauthenticated access.

---

## Agent Discovery Flow

```
1. Agent registers its AgentCard at /.well-known/agent.json
2. Orchestrator reads AgentCard: GET http://agent-host/.well-known/agent.json
3. Orchestrator validates: capabilities, skills, auth requirements
4. Orchestrator constructs message/send or message/stream request
5. Orchestrator authenticates per AgentCard.authentication.schemes
6. Orchestrator sends task → receives Artifact → extracts parts
```

---

## SDK Quick Reference

```python
# Installation
pip install a2a-sdk

# Core server imports
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.utils import new_agent_text_message

# Core client imports
from a2a.client import A2AClient
import httpx
```

### Implement AgentExecutor
```python
class MyAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # context.message.parts[0].root.text  <- user text input
        result = await my_agent.invoke(context.message)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel not supported")
```

### Build AgentCard
```python
agent_card = AgentCard(
    name="My Sector Agent",
    description="...",
    url="http://localhost:8001",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    skills=[AgentSkill(id="my-skill", name="...", description="...")],
)
```

### Start A2A Server
```python
import uvicorn
app = A2AStarletteApplication(
    agent_card=agent_card,
    request_handler=DefaultRequestHandler(
        agent_executor=MyAgentExecutor(),
        task_store=InMemoryTaskStore(),
    ),
).build()
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Send Task (Client)
```python
async with httpx.AsyncClient() as http_client:
    client = A2AClient(httpx_client=http_client, url="http://localhost:8001")
    response = await client.send_message(SendMessageRequest(
        id="req-1",
        params=MessageSendParams(
            message=Message(
                role="user",
                parts=[Part(root=TextPart(text="Analyse food inflation"))],
                messageId="msg-1",
            )
        )
    ))
```

---

## Authoritative Sources

| Resource | URL |
| :--- | :--- |
| A2A Protocol Home | https://a2a-protocol.org |
| A2A Specification | https://a2a-protocol.org/latest/specification/ |
| Python SDK GitHub | https://github.com/a2aproject/a2a-python |
| Python SDK Tutorials | https://a2a-protocol.org/latest/tutorials/python/1-introduction/ |
| Python API Reference | https://a2a-protocol.org/latest/sdk/python/api/ |
| PyPI Package | https://pypi.org/project/a2a-sdk/ |
| A2A + MCP comparison | https://a2a-protocol.org/latest/topics/a2a-and-mcp/ |
| Life of a Task | https://a2a-protocol.org/latest/topics/life-of-a-task/ |
| Streaming & Async | https://a2a-protocol.org/latest/topics/streaming-and-async/ |
