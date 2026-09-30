# PydanticAI Structured Outputs, Validation, and Streaming

**Documentation:** https://ai.pydantic.dev/results/ | https://ai.pydantic.dev/message-history/

---

## 1. Type-Safe Structured Outputs

By passing a Pydantic v2 `BaseModel` to `result_type`, PydanticAI forces the LLM to output conforming JSON. The response is automatically parsed and validated into a Python object.

```python
from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

class EconomicIndicatorAnalysis(BaseModel):
    indicator_name: str = Field(description="Name of the economic indicator (e.g. CPI, Repo Rate)")
    observation_period: str = Field(description="Period formatted as YYYY-MM or YYYY-QX")
    current_value: float = Field(description="Numeric value observed")
    unit: str = Field(description="Unit of measurement (percent, index points, INR Crore)")
    trend: str = Field(description="Trend direction: 'increasing', 'decreasing', or 'stable'")
    citation_source: str = Field(description="Source institution and dataset cited")
    policy_implication: str = Field(description="One sentence assessment of policy implication")

macro_agent = Agent[None, EconomicIndicatorAnalysis](
    'groq:llama-3.3-70b-versatile',
    result_type=EconomicIndicatorAnalysis,
    system_prompt=(
        "You are an analytical assistant for Macrograph-AI. "
        "Analyze macroeconomic statements and extract structured indicators. "
        "Every indicator must strictly cite its institutional source."
    ),
)
```

---

## 2. Post-Extraction Validation (`@agent.result_validator`)

When schema validation is insufficient and custom domain rules must be enforced (e.g. boundary ranges, date consistency, or indicator cross-checks), use `@agent.result_validator`. Raising `ModelRetry` prompts the model to correct its structured response.

```python
from pydantic_ai import ModelRetry, RunContext

@macro_agent.result_validator
async def validate_macro_analysis(
    ctx: RunContext,
    result: EconomicIndicatorAnalysis,
) -> EconomicIndicatorAnalysis:
    # Rule 1: Citations must not be vague
    if len(result.citation_source.strip()) < 5:
        raise ModelRetry(
            "Citation source is too vague. Specify official body (e.g., 'MOSPI CPI Release' or 'RBI Bulletin')."
        )

    # Rule 2: Allowed trend values
    allowed_trends = {"increasing", "decreasing", "stable"}
    if result.trend.lower() not in allowed_trends:
        raise ModelRetry(
            f"Invalid trend '{result.trend}'. Must be one of: {allowed_trends}."
        )

    return result
```

---

## 3. Streaming Responses

PydanticAI supports streaming both plain text and partial structured objects. This enables high-responsiveness in FastAPI Server-Sent Events (SSE) and frontend visualizers.

### A. Streaming Plain Text

```python
import asyncio

async def stream_analysis():
    async with macro_agent.run_stream("Provide an executive summary of current CPI inflation.") as stream:
        async for chunk in stream.stream_text(debounce_by=0.05):
            print(chunk, end="", flush=True)

    # Retrieve complete usage and final result after stream finishes
    print(f"\nTotal tokens used: {stream.usage()}")
```

### B. Streaming Structured Output (Partial JSON Updates)

For models supporting incremental JSON generation, inspect progressive partial snapshots:

```python
async def stream_structured_indicator():
    async with macro_agent.run_stream("Analyze Repo Rate held at 6.50% by RBI MPC in Oct 2024.") as stream:
        async for partial in stream.stream_structured(debounce_by=0.1):
            # partial contains incomplete/growing EconomicIndicatorAnalysis fields
            print(f"Current snapshot: {partial}")

    final_result: EconomicIndicatorAnalysis = await stream.get_data()
    print("Final parsed model:", final_result.model_dump())
```

---

## 4. Message History & Multi-Turn Persistence

PydanticAI represents all interactions (system prompt, user messages, tool calls, tool returns, model responses) as typed messages.

### Capturing & Replaying Conversation State

```python
# Turn 1
result_1 = await macro_agent.run("What was India's headline CPI in July 2024?")
history = result_1.all_messages()

# Turn 2: Pass history to maintain memory
result_2 = await macro_agent.run(
    "How does that compare to the RBI upper tolerance band?",
    message_history=history,
)

# Combined history now includes both turns
full_history = result_2.all_messages()
```

### Serializing History to Database (JSON / DuckDB)

PydanticAI provides a type adapter for serializing message history to JSON:

```python
from pydantic_ai.messages import ModelMessagesTypeAdapter
import json

# Serialize to JSON string for database storage
json_data = ModelMessagesTypeAdapter.dump_json(full_history)

# Deserialize back into message list
restored_history = ModelMessagesTypeAdapter.validate_json(json_data)
```
