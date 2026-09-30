# PydanticAI Reference — Overview, Architecture, and Providers

**Source:** https://ai.pydantic.dev | https://github.com/pydantic/pydantic-ai  
**Package:** `pydantic-ai >= 0.0.24` | `pip install "pydantic-ai[groq,openai]"`  
**Compatibility:** Python 3.10+, Pydantic v2, FastAPI, LangGraph, DuckDB

---

## 1. What is PydanticAI?

PydanticAI is an agent framework from the Pydantic team designed for production software engineering rather than experimental notebooks. It applies the same static typing, strict schema validation, and developer ergonomics of Pydantic v2 to generative AI interactions.

### Core Philosophy
1. **Type-Driven Development:** Agents are generic types parameterized by their dependency container (`deps_type`) and output type (`result_type`).
2. **Model-Agnostic Core:** Write agent logic, tools, and prompts once. Switch providers (`groq:llama-3.3-70b-versatile`, `openai:gpt-4o`, `anthropic:claude-sonnet-4-6`) with a single string or model object.
3. **Structured Outputs by Construction:** Responses are parsed directly into Pydantic v2 `BaseModel` instances with automatic re-prompting on schema validation errors.
4. **First-Class Dependency Injection:** External services (database connections, HTTP clients, settings) are injected at runtime through type-safe `RunContext[Deps]`, avoiding global state and enabling clean unit testing.
5. **Deterministic Unit Testing:** Native `TestModel` and `FunctionModel` mocks allow testing full agent cycles, tool execution, and validation rules in CI without LLM network calls.

---

## 2. PydanticAI in Macrograph-AI

In the Macrograph-AI architecture:
- **A2A Protocol:** Inter-agent reasoning and task delegation across sector boundaries.
- **FastMCP:** Data retrieval tool servers exposing sector datasets.
- **PydanticAI:** Powers agent node reasoning, typed inference, structured analysis output, and tool coordination inside sector packages and worker tasks.

```
+-------------------------------------------------------------------+
|                     FastAPI Gateway / Main App                    |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Orchestrator Graph (LangGraph / State)              |
+-------------------------------------------------------------------+
             |                                        |
      (A2A Protocol)                           (A2A Protocol)
             v                                        v
+-----------------------------+        +-----------------------------+
|    Prices Sector Agent      |        |   Monetary Sector Agent     |
|  +-----------------------+  |        |  +-----------------------+  |
|  |     PydanticAI        |  |        |  |     PydanticAI        |  |
|  |  Agent[Deps, Output]  |  |        |  |  Agent[Deps, Output]  |  |
|  +-----------------------+  |        |  +-----------------------+  |
|      |               |      |        |      |               |      |
|      v               v      |        |      v               v      |
| DuckDB Deps     FastMCP     |        | DuckDB Deps     FastMCP     |
+-----------------------------+        +-----------------------------+
```

---

## 3. Supported Model Providers & Configuration

PydanticAI uses standard provider prefixes. When using Groq (the default for Macrograph-AI), configure the API key in environment variables:

```bash
export GROQ_API_KEY="gsk_..."
export OPENAI_API_KEY="sk-..."
```

### Supported Providers Reference

| Provider | Model Identifier Example | Extra Dependency |
| :--- | :--- | :--- |
| **Groq (Fast)** | `'groq:llama-3.1-8b-instant'` | `pydantic-ai[groq]` |
| **Groq (Reasoning)** | `'groq:llama-3.3-70b-versatile'` | `pydantic-ai[groq]` |
| **OpenAI** | `'openai:gpt-4o'`, `'openai:gpt-4o-mini'` | `pydantic-ai[openai]` |
| **Anthropic** | `'anthropic:claude-sonnet-4-6'` | `pydantic-ai[anthropic]` |
| **Google Gemini** | `'gemini-1.5-pro'` | `pydantic-ai[gemini]` |
| **Ollama (Local)** | `'ollama:llama3.2'` | None (OpenAI-compatible) |

### Programmatic Model Initialization

```python
from pydantic_ai.models.groq import GroqModel
from pydantic_ai import Agent

# Explicit model initialization with settings
model = GroqModel(
    'llama-3.3-70b-versatile',
    api_key='gsk_...',  # Optional if GROQ_API_KEY env var is set
)

agent = Agent(model=model)
```

---

## 4. Agent Anatomy & Execution Modes

An `Agent` instance encapsulates:
1. **Model:** The LLM provider and model name.
2. **System Prompts:** Static strings or dynamic `@agent.system_prompt` functions.
3. **Tools:** Functions decorated with `@agent.tool` or `@agent.tool_plain`.
4. **Dependencies (`deps_type`):** Dataclass or Pydantic model for injected resources.
5. **Output Schema (`result_type`):** Python type, `str`, or Pydantic `BaseModel`.

### Execution Methods

| Method | Return Type | Description |
| :--- | :--- | :--- |
| `await agent.run(prompt, deps=...)` | `RunResult[T]` | Asynchronous execution (standard in FastAPI/async apps) |
| `agent.run_sync(prompt, deps=...)` | `RunResult[T]` | Synchronous execution for scripts and blocking CLI |
| `async with agent.run_stream(...)` | `StreamedRunResult[T]` | Server-Sent Events (SSE) and live token streaming |
| `with agent.override(model=...)` | Context manager | Mock substitution during tests |
