# A2A Protocol Operations Reference

All A2A operations use **JSON-RPC 2.0 over HTTPS**. Every request targets `POST <agent-url>`.

---

## 1. `message/send` — Synchronous Task Submission

**Direction:** Client → Server  
**Use when:** Task is short-lived and a synchronous response is acceptable.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "messageId": "msg-abc-123",
      "parts": [
        {
          "kind": "text",
          "text": "What is the current food CPI and what is driving it?"
        }
      ]
    },
    "configuration": {
      "acceptedOutputModes": ["text", "data"]
    }
  }
}
```

### Response (Task Completed Synchronously)
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "task": {
      "id": "task-xyz-456",
      "contextId": "ctx-001",
      "status": {
        "state": "completed"
      },
      "artifacts": [
        {
          "name": "food-inflation-analysis",
          "parts": [
            {
              "kind": "text",
              "text": "Food CPI is +4.8% YoY [Source: MOSPI via Prices Agent MCP]."
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
      ]
    }
  }
}
```

---

## 2. `message/stream` — Streaming Task Submission (SSE)

**Direction:** Client → Server  
**Use when:** Task is long-running or the agent produces progressive output (streaming analysis).  
**Protocol:** Server responds with `Content-Type: text/event-stream` (Server-Sent Events).

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-2",
  "method": "message/stream",
  "params": {
    "message": {
      "role": "user",
      "messageId": "msg-def-456",
      "parts": [
        {
          "kind": "text",
          "text": "Run a full causal analysis: why is food inflation rising and how is RBI responding?"
        }
      ]
    }
  }
}
```

### SSE Stream Response
```
data: {"jsonrpc":"2.0","id":"req-2","result":{"kind":"status","taskId":"task-789","contextId":"ctx-001","status":{"state":"submitted"},"final":false}}

data: {"jsonrpc":"2.0","id":"req-2","result":{"kind":"status","taskId":"task-789","contextId":"ctx-001","status":{"state":"working"},"final":false}}

data: {"jsonrpc":"2.0","id":"req-2","result":{"kind":"artifact","taskId":"task-789","artifact":{"name":"partial-analysis","parts":[{"kind":"text","text":"Food CPI spike confirmed at +4.8% YoY..."}]},"final":false}}

data: {"jsonrpc":"2.0","id":"req-2","result":{"kind":"status","taskId":"task-789","contextId":"ctx-001","status":{"state":"completed"},"final":true}}
```

**Critical:** Only close the SSE stream after receiving `"final": true`.

---

## 3. `tasks/get` — Poll Task Status

**Direction:** Client → Server  
**Use when:** Polling for task completion after `message/send` returned an in-progress task ID.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-3",
  "method": "tasks/get",
  "params": {
    "id": "task-xyz-456"
  }
}
```

### Response
```json
{
  "jsonrpc": "2.0",
  "id": "req-3",
  "result": {
    "task": {
      "id": "task-xyz-456",
      "contextId": "ctx-001",
      "status": {
        "state": "completed"
      },
      "artifacts": [ ... ]
    }
  }
}
```

---

## 4. `tasks/cancel` — Cancel an In-Progress Task

**Direction:** Client → Server  
**Use when:** The task is taking too long or is no longer needed.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-4",
  "method": "tasks/cancel",
  "params": {
    "id": "task-xyz-456"
  }
}
```

### Response
```json
{
  "jsonrpc": "2.0",
  "id": "req-4",
  "result": {
    "task": {
      "id": "task-xyz-456",
      "status": { "state": "canceled" }
    }
  }
}
```

---

## 5. `tasks/resubscribe` — Resume Dropped SSE Stream

**Direction:** Client → Server  
**Use when:** An SSE stream connection was dropped before `final: true` was received.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-5",
  "method": "tasks/resubscribe",
  "params": {
    "id": "task-xyz-456"
  }
}
```
The server responds with a new SSE stream starting from where the previous one ended.

---

## 6. `tasks/pushNotificationConfig/set` — Register Webhook Callback

**Direction:** Client → Server  
**Use when:** You want the server agent to push final results to your webhook instead of keeping a connection open.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-6",
  "method": "tasks/pushNotificationConfig/set",
  "params": {
    "taskId": "task-xyz-456",
    "pushNotificationConfig": {
      "url": "https://my-orchestrator.internal/callbacks/a2a",
      "token": "verification-token-abc",
      "authentication": {
        "schemes": ["Bearer"]
      }
    }
  }
}
```

---

## 7. `agent/getAuthenticatedExtendedCard` — Fetch Full AgentCard

**Direction:** Client → Server  
**Use when:** Retrieving the authenticated (private) version of the AgentCard which may contain additional details not in the public `/.well-known/agent.json`.  
**Requires:** Valid authentication credentials.

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-7",
  "method": "agent/getAuthenticatedExtendedCard"
}
```

---

## Multi-Turn Conversations

For conversational tasks that require back-and-forth context (e.g., Orchestrator asks Agriculture Agent to refine its supply-side analysis after receiving new information from the Prices Agent):

1. Include `contextId` in all messages to thread the conversation.
2. When `status.state === "input-required"`, send a follow-up message with the same `contextId` and a new `messageId`.

```json
{
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "messageId": "msg-follow-up-002",
      "contextId": "ctx-001",
      "parts": [{ "kind": "text", "text": "Also compare Kharif vs Rabi production shortfall." }]
    }
  }
}
```

---

## Error Handling

| Scenario | JSON-RPC Error Code | Action |
| :--- | :--- | :--- |
| Malformed request body | `-32700` (Parse Error) | Log and reject; do not retry |
| Missing required field | `-32600` (Invalid Request) | Fix request schema; do not retry |
| Unknown method | `-32601` (Method Not Found) | Check AgentCard capabilities |
| Task not found | `-32001` (Task Not Found) | Task may have expired; submit new task |
| Internal server error | `-32603` (Internal Error) | Retry with exponential backoff |
| Auth failure | HTTP 401/403 | Check authentication scheme and credentials |
| Agent unavailable | HTTP 503 | Retry with backoff; check agent health endpoint |

---

## Python SDK — Sending Tasks

```python
import asyncio
import httpx
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
)

async def send_task_to_agent(agent_url: str, text: str) -> str:
    """Send a task to a remote A2A agent and return the result text."""
    async with httpx.AsyncClient() as http_client:
        # Discover AgentCard
        resolver = A2ACardResolver(httpx_client=http_client, base_url=agent_url)
        agent_card = await resolver.get_agent_card()

        # Verify capability
        if not agent_card.skills:
            raise ValueError(f"Agent at {agent_url} has no declared skills.")

        # Build and send request
        client = A2AClient(httpx_client=http_client, agent_card=agent_card)
        response = await client.send_message(
            SendMessageRequest(
                id="req-001",
                params=MessageSendParams(
                    message=Message(
                        role="user",
                        parts=[Part(root=TextPart(text=text))],
                        messageId="msg-001",
                    )
                ),
            )
        )

        # Extract artifact text
        task = response.root.result.root.task
        for artifact in task.artifacts or []:
            for part in artifact.parts or []:
                if hasattr(part.root, "text"):
                    return part.root.text
        return ""
```
