# Lessons & Learned Patterns

Record corrections, edge cases, and architectural lessons to prevent repeated mistakes across sessions.

## Patterns & Corrections
<!-- Add learnings here following any correction or post-mortem -->
- `core.knowledge_graph.__init__` re-exports the singleton `neo4j_store`, which shadows the submodule of the same name; in tests use `importlib.import_module("core.knowledge_graph.neo4j_store")`. Same for `core.orchestrator.llm_client`.
- Importing statsmodels takes ~30s cold on this machine; it is slow, not hung. Run Python via `.venv\Scripts\Activate.ps1`.
- Tests that mock `llm_client.complete` hide import bugs inside the real client; keep a no-key regression test.
