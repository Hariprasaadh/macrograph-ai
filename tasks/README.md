# Phase 3 Team Task Index & Sprint Assignment

This directory contains standalone, prompt-ready task instruction documents for our team of 3 developers to execute **Phase 3 (8-Domain Decoupling & Live Feeds)** in parallel without merge conflicts.

---

## Team Assignment Matrix

| Developer | Role & Ownership | Scope / Assigned Sectors | Instruction Document |
| :--- | :--- | :--- | :--- |
| **Developer 1** | **Core Platform & Orchestrator Lead** | DuckDB Deduplication & Unique Upsert, Base Live Client with Retries, Central A2A Bootstrap, LangGraph Routing, Gateway Mounts | [`DEV1_CORE_PLATFORM.md`](DEV1_CORE_PLATFORM.md) |
| **Developer 2** | **Nominal Economy & Macro-Finance** | Prices & Inflation Sector (`prices_sector`), Monetary & Banking Sector (`monetary_sector`), Fiscal Sector (`fiscal_sector`) | [`DEV2_NOMINAL_AGENTS.md`](DEV2_NOMINAL_AGENTS.md) |
| **Developer 3** | **Structural & Real Economy** | Labour & Employment Sector (`labour_sector`), Agriculture & Rural Sector (`agriculture_sector`), External Sector (`external_sector`) | [`DEV3_STRUCTURAL_AGENTS.md`](DEV3_STRUCTURAL_AGENTS.md) |

---

## How Each Developer Should Use Their Document

Each markdown file is designed to be **prompt-ready**:
1. Open your assigned file (`DEV1_CORE_PLATFORM.md`, `DEV2_NOMINAL_AGENTS.md`, or `DEV3_STRUCTURAL_AGENTS.md`).
2. You can either follow the step-by-step instructions or paste the markdown directly into your AI coding assistant (Cursor, Gemini CLI, Claude, ChatGPT).
3. The file includes:
   - Exact file paths to create or edit.
   - Pydantic schemas, class names, and method signatures.
   - Data source URLs (MoSPI, RBI DBIE, Yahoo Finance, EPFO, CGA).
   - Test commands and Definition of Done (DoD).

---

## Git Workflow & Branching Strategy

```
main (protected)
  ├── feature/p3-core-orchestrator-routing   (Dev 1)
  ├── feature/p3-nominal-domain-agents       (Dev 2)
  └── feature/p3-structural-domain-agents     (Dev 3)
```

### Pull Request & Integration Sequence
1. **PR #1 (Dev 1, Day 1)**: Base error model and DuckDB unique constraint upsert $\rightarrow$ Merged into `main`.
2. **PR #2 (Dev 2, Day 4)**: Prices, Monetary, Fiscal domain packages $\rightarrow$ Merged into `main`.
3. **PR #3 (Dev 3, Day 4)**: Labour, Agriculture, External domain packages $\rightarrow$ Merged into `main`.
4. **PR #4 (Dev 1, Day 4-5)**: Central registry bootstrap, 8-sector LangGraph routing, gateway sub-app mounts, and full integration tests $\rightarrow$ Final merge into `main`.

---

## Verification Command
Before submitting a PR, every developer must ensure all tests pass:
```powershell
.venv\Scripts\pytest backend/tests -v
```
Target: $\ge 42$ passing tests, 0 failures.
