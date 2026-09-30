# PydanticAI Testing and Evaluation Reference

**Documentation:** https://ai.pydantic.dev/testing/

---

## 1. Principles of Agent Testing

Under the Macrograph-AI rules:
1. **No Live Network Calls in CI:** Tests must run quickly, offline, and deterministically without consuming Groq or OpenAI tokens.
2. **Behavior Verification:** Test that tools are invoked with expected parameters, outputs adhere to schemas, and dependency logic handles boundary states.
3. **PydanticAI Test Models:** Use native `TestModel` and `FunctionModel` via `agent.override()`.

---

## 2. Using `TestModel` for Rapid Unit Tests

`TestModel` generates minimal valid data satisfying the agent's `result_type`. By default, it will also call all available tools registered on the agent.

```python
from __future__ import annotations

import pytest
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

class IndicatorReport(BaseModel):
    indicator: str
    rate: float
    status: str

agent = Agent[None, IndicatorReport](
    'groq:llama-3.3-70b-versatile',
    result_type=IndicatorReport,
)

def test_agent_with_test_model():
    # Override model during test execution
    with agent.override(model=TestModel()):
        result = agent.run_sync("Analyze repo rate status")
        
        # Verify structure returned
        assert isinstance(result.data, IndicatorReport)
        assert isinstance(result.data.rate, float)
```

---

## 3. Using `FunctionModel` for Deterministic Mocking

When you want to test specific response logic, tool interaction branches, or validation failures, use `FunctionModel` to provide scripted responses:

```python
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart

def mock_llm_handler(messages, info):
    # Custom inspection of prompts or message counts
    return ModelResponse(parts=[TextPart('{"indicator": "CPI", "rate": 5.4, "status": "stable"}')])

def test_agent_deterministic_response():
    with agent.override(model=FunctionModel(mock_llm_handler)):
        result = agent.run_sync("What is CPI?")
        assert result.data.indicator == "CPI"
        assert result.data.rate == 5.4
```

---

## 4. Testing Dependency Injection with Mock Context

Test tools in isolation and through the agent with fake/in-memory dependencies:

```python
from dataclasses import dataclass
import duckdb
import pytest
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

@dataclass
class MockSectorDeps:
    db: duckdb.DuckDBPyConnection

@pytest.fixture
def in_memory_db():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE metrics (name VARCHAR, val DOUBLE);")
    conn.execute("INSERT INTO metrics VALUES ('repo_rate', 6.5);")
    yield conn
    conn.close()

def test_tool_execution(in_memory_db):
    deps = MockSectorDeps(db=in_memory_db)
    
    agent = Agent[MockSectorDeps, str](
        'groq:llama-3.3-70b-versatile',
        deps_type=MockSectorDeps,
    )

    @agent.tool
    def get_metric(ctx: RunContext[MockSectorDeps], name: str) -> float:
        row = ctx.deps.db.execute("SELECT val FROM metrics WHERE name = ?", [name]).fetchone()
        return row[0] if row else 0.0

    with agent.override(model=TestModel()):
        result = agent.run_sync("Get repo rate", deps=deps)
        assert result is not None
```

---

## 5. Capturing Messages with `capture_run_messages`

Inspect the conversation history to assert that specific tool calls occurred and correct prompt context was supplied:

```python
from pydantic_ai import capture_run_messages

def test_tool_call_sequence():
    with agent.override(model=TestModel()):
        with capture_run_messages() as messages:
            agent.run_sync("Query metric")
            
            # messages list contains all system prompts, user turns, and tool exchanges
            assert len(messages) > 0
            # Inspect first message (system prompt)
            assert any("Macrograph" in str(msg) for msg in messages)
```
