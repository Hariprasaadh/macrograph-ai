---
trigger: always_on
---

# Macrograph-AI: Core Engineering Rules

These rules apply to every agent and AI coding assistant working in this repository. They are **non-negotiable** and take precedence over any general defaults.

---

## 1. Architecture Integrity (CRITICAL)

- **Read `docs/high-level-overview.md` before implementing any feature. If you want to make some updates, ask the user first and only if they approve you can update it.** Architecture decisions are pre-decided. Do not deviate without explicit user instruction.
- **A2A is for agent-to-agent reasoning. FastMCP is for agent-to-data retrieval.** These are two separate, non-interchangeable layers. Never conflate them. All MCP servers in this project are implemented with the `fastmcp` package (`FastMCP` class). No other MCP implementation is permitted.
- **Each macroeconomic indicator has exactly one owner agent.** No agent may recompute or re-fetch a data point that belongs to another agent's domain. It must request that data via A2A.
- **No inter-sector imports.** A sector package must never directly import from another sector package (e.g., `from prices_sector.models import ...` inside `monetary_sector/`). Cross-sector communication is via A2A only.

---

## 2. Code Quality (HIGH — Enforced by code-reviewer agent)

### DRY (Don't Repeat Yourself)
- Before creating any function, utility, model, or query, search the codebase for an existing implementation.
- Domain logic must have a single canonical source. If two sector agents need the same transformation, it belongs in `core/`.
- Backend Pydantic schemas and frontend TypeScript interfaces must be kept in sync. Never allow them to diverge into separate sources of truth.

### KISS (Keep It Simple)
- Write the simplest code that correctly solves the problem.
- Prefer explicit, linear control flow over clever one-liners.
- If a junior engineer cannot understand the code's purpose in under 15 seconds, simplify it.

### YAGNI (You Aren't Gonna Need It)
- Do not add parameters, abstractions, configuration flags, or generalization layers that are not immediately required.
- Do not introduce microservices, event buses, or custom frameworks for problems that existing tools already solve.
- Do not pre-optimize without profiling data proving a bottleneck exists.

### Dead Code
- Never commit commented-out code blocks. Git history preserves removed code.
- Remove all unused imports, unused function parameters, and unreachable branches.
- Remove all `print()` debug statements and temporary scaffolding before committing.

---

## 3. Python Standards (HIGH)

- **Python 3.12.** Use `from __future__ import annotations` at the top of every module.
- **Pydantic v2.** Use `.model_validate()`. Never use `.dict()` (deprecated) — use `.model_dump()`. Always annotate fields with strict types.
- **Async-first.** All I/O-bound operations (HTTP calls, DB queries, LLM calls) must be `async`. Never use blocking `requests.get()`, `time.sleep()`, or synchronous disk reads inside `async def` functions.
  - Use `httpx.AsyncClient` for HTTP requests.
  - Use `asyncio.sleep()` for delays.
- **DuckDB safety.** All SQL queries must be parameterized with `?` placeholders. Never use f-strings or string concatenation to build SQL. This is a CRITICAL security rule.
- **Tenacity for resilience.** All calls to external APIs (Groq LLM, government data APIs, RBI, MOSPI) must be wrapped with `@retry(wait=wait_exponential(), stop=stop_after_attempt(3))`.
- **No bare exceptions.** Never use `except: pass` or `except Exception: pass`. Catch specific exception types. Log with structured context. Propagate or convert to a typed error.
- **No hardcoded secrets.** Every secret, API key, URL, and environment-specific value must come from `PlatformSettings` in `core/config.py`, loaded via `.env`.
- **Resource cleanup.** DuckDB connections, file handles, and `httpx.AsyncClient` sessions must be managed with `async with` or `try/finally`. No leaked connections.
- **File length.** No single Python module should exceed **400 lines**. Refactor into submodules when approaching this limit.
- **No emojis in code, comments, or log messages.**

---

## 4. FastAPI & FastMCP Standards (HIGH)

### FastAPI Routes
- Every FastAPI route must have:
  - A Pydantic response model annotation.
  - A docstring describing the endpoint's purpose.
  - An appropriate HTTP status code on success and a specific `HTTPException` on failure. Never use `500` as a generic catch-all.
- The CORS policy `allow_origins=["*"]` is only acceptable in development. Production deployments must restrict origins.

### FastMCP Servers (MCP Layer)
- **One `FastMCP` instance per sector.** Every sector package must define its MCP server in `<sector>/mcp_server.py` as:
  ```python
  from fastmcp import FastMCP
  mcp_server = FastMCP("<Sector Name> MCP Server")
  ```
- Every `@mcp_server.tool()` must have:
  - A clear docstring with a description of what the tool fetches and from which source.
  - Fully type-annotated parameters and return type (Pydantic model or primitive).
  - Explicit `timeout` configuration on any outbound HTTP call inside the tool.
  - Tenacity retry wrapping on all external API calls within the tool body.
- FastMCP servers must be registered in `backend/main.py`. No sector FastMCP server may be called or imported directly by another sector — only via the MCP protocol.
- **Never** use FastMCP as a workaround for cross-sector data sharing. That is the A2A protocol's job.

---

## 5. LangGraph & Orchestration Standards (HIGH)

- All LangGraph nodes must be typed using `OrchestratorState` from `core/orchestrator/state.py`.
- A sector agent node must only perform analysis within its domain. It must not attempt to analyze another sector's domain directly.
- The Orchestrator node must not perform domain analysis. It routes, coordinates, and synthesizes. Domain analysis belongs in sector nodes only.
- Agent nodes must handle `None` and missing state keys gracefully. Never assume a prior node has populated a particular state field without checking.

---

## 6. Testing Standards (HIGH)

- **All new business logic, FastMCP tools, and LangGraph nodes must have `pytest` tests in `backend/tests/`.**
- Tests must cover:
  - The happy path (valid, expected inputs)
  - Invalid or malformed inputs (Pydantic validation errors, missing required fields)
  - External failure modes (mocked API timeouts, DuckDB connection errors)
  - Boundary values (empty lists, zero values, max-length strings)
- Tests must be isolated: no live network calls, no shared state between test cases, no file system side effects.
- Mock all external API calls with `pytest-mock` or `httpx` transport mocking.
- Run all tests before committing: `pytest backend/tests/ -v`

---

## 7. Security Rules (CRITICAL)

- **No secrets in source code.** No API keys, passwords, tokens, or connection strings hardcoded anywhere.
- **No f-string SQL.** All DuckDB and database queries must use parameterized placeholders.
- **Prompt injection defense.** When formatting user-supplied text into LLM system prompts or A2A messages, sanitize and bound the input. Never pass raw user text directly into an agent system prompt without escaping.
- **No internal error details to clients.** FastAPI `HTTPException` messages must be user-friendly and must never expose stack traces, database errors, or internal infrastructure details.
- **Sensitive data must not appear in logs.** Never log API keys, user PII, or full LLM prompts at `INFO` level or above in production.

---

## 8. Frontend Standards (MEDIUM)

- **TypeScript strict mode.** No `any` types in production code. If a type is unknown, define a proper interface.
- **No direct state mutation.** Always use immutable update patterns with spread operators.
- **Complete hook dependency arrays.** `useEffect`, `useMemo`, `useCallback` must declare all dependencies accurately.
- **Cancel async operations on unmount.** Use `AbortController` for all `fetch` calls inside components to prevent state updates on unmounted components.
- **Tailwind only.** No inline styles. No raw CSS unless in global `index.css` for design tokens.

---

## 9. Git & Commit Standards (LOW)

- Commits must be atomic: one logical change per commit.
- Commit message format: `<type>(<scope>): <short description>` (e.g., `feat(monetary): add repo rate MCP tool`, `fix(orchestrator): handle missing sector state key`).
- Do not commit broken or untested code to `main`.
- Verify with `pytest backend/tests/ -v` and `npm run build` (frontend) before pushing.
