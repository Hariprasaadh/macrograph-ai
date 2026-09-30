# PydanticAI Tools & Dependency Injection Reference

**Documentation:** https://ai.pydantic.dev/tools/ | https://ai.pydantic.dev/dependencies/

---

## 1. Tool Declaration Patterns

Tools are Python callables exposed to the LLM during an agent's reasoning loop. PydanticAI automatically inspects function type signatures, parameter defaults, and docstrings to generate JSON schema definitions for the model provider.

### Tool Types

| Decorator | Parameters | When to Use |
| :--- | :--- | :--- |
| `@agent.tool` | `(ctx: RunContext[Deps], ...)` | Tool requires injected services (database, settings, HTTP client) |
| `@agent.tool_plain` | `(...)` | Pure function with no dependency requirement (math, date calculations) |

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from pydantic_ai import Agent, RunContext
import duckdb

@dataclass
class SectorDeps:
    db_conn: duckdb.DuckDBPyConnection
    base_year: int = 2012

agent = Agent[SectorDeps, str](
    'groq:llama-3.3-70b-versatile',
    deps_type=SectorDeps,
)

# 1. Plain tool: no dependencies needed
@agent.tool_plain
def calculate_growth_rate(current_value: float, previous_value: float) -> float:
    """Calculate percentage growth rate between two periods.

    Args:
        current_value: Latest observation value.
        previous_value: Base or previous period value.
    """
    if previous_value == 0:
        return 0.0
    return round(((current_value - previous_value) / previous_value) * 100, 2)

# 2. Context tool: accesses injected DuckDB connection
@agent.tool
async def query_cpi_index(
    ctx: RunContext[SectorDeps],
    category: str,
    year: int,
) -> dict[str, float]:
    """Retrieve CPI monthly numbers for a given category and year from DuckDB.

    Args:
        ctx: Injected runtime context containing DuckDB connection.
        category: Price basket category (e.g., 'headline', 'food', 'fuel').
        year: Calendar year of observation.
    """
    cursor = ctx.deps.db_conn.cursor()
    # DuckDB parameterized query (security rule: never use string concatenation)
    query = """
        SELECT month, index_value 
        FROM cpi_monthly 
        WHERE category = ? AND year = ?
        ORDER BY month ASC
    """
    result = cursor.execute(query, [category.lower(), year]).fetchall()
    return {f"month_{m}": val for m, val in result}
```

---

## 2. Dynamic System Prompts

Static system prompts are passed to `Agent(system_prompt=...)`. When prompts depend on runtime state or injected dependencies (e.g. current date, user permissions, active sector parameters), use `@agent.system_prompt`:

```python
from datetime import datetime

@agent.system_prompt
async def inject_sector_context(ctx: RunContext[SectorDeps]) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    return (
        f"You are the Macrograph-AI Prices Sector Specialist. "
        f"Current system date: {current_date}. "
        f"Base index year in use: {ctx.deps.base_year}. "
        f"All inflation numbers must cite specific index values and data sources."
    )
```

---

## 3. Self-Correction with `ModelRetry`

When an LLM provides invalid arguments, attempts an unsupported query, or yields an impossible domain value, raise `ModelRetry`. Instead of crashing the execution, PydanticAI intercepts `ModelRetry`, injects the error message back into the model's message history as feedback, and prompts the model to correct its call.

```python
from pydantic_ai import ModelRetry

VALID_CATEGORIES = {"headline", "food", "fuel", "core"}

@agent.tool
async def fetch_basket_weight(ctx: RunContext[SectorDeps], basket_name: str) -> float:
    """Fetch the percentage weight of a commodity basket in CPI.

    Args:
        ctx: Injected sector context.
        basket_name: Standard basket identifier.
    """
    normalized = basket_name.lower().strip()
    if normalized not in VALID_CATEGORIES:
        raise ModelRetry(
            f"'{basket_name}' is not a valid CPI basket. "
            f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}. "
            f"Please choose an allowed basket."
        )

    weights = {"headline": 100.0, "food": 45.86, "fuel": 6.84, "core": 47.30}
    return weights[normalized]
```

### Configuring Retry Limits

Control maximum retries to avoid runaway loops:

```python
agent = Agent(
    'groq:llama-3.3-70b-versatile',
    retries=3,  # Max retries for ModelRetry or validation errors (default: 1)
)
```

---

## 4. Best Practices for Tool Functions

1. **Detailed Docstrings:** The docstring is the tool's manual for the LLM. Describe:
   - What the tool does
   - Each parameter's format and constraints
   - Return value meaning
2. **Type Annotations:** Always annotate all parameters and return types. PydanticAI uses these for JSON schema generation.
3. **Async Tools:** When performing I/O (DuckDB query, HTTP requests, MCP calls), make tools `async def`. Never use blocking I/O in async contexts.
4. **Parameter Safety:** Use Pydantic models or validation checks on tool inputs. Never pass unchecked strings to SQL engines.
