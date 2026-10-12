# Status, Code Review Findings and Roadmap

Snapshot date: 2026-10-12 (branch `main`, HEAD `557e332`). Written from a direct read of the code, not from earlier documentation. Where earlier documents disagreed with the code, the code is treated as correct and the document was fixed.

Size: about 45.8k lines of Python and 11.3k lines of TypeScript; 456 test functions; git history spans 2026-07-16 to 2026-10-11.

## 1. Component maturity

| Component | State | Notes |
| :--- | :--- | :--- |
| A2A layer (`core/protocols/a2a`) | **Solid** | Typed envelopes, declared dependency edges, hop/depth/loop guards, correlation ids, trace store, source-provenance enforcement ("No Source, No Answer" at the protocol level). Native implementation; `a2a-sdk` unused. In-memory trace and duplicate detection only. |
| Orchestrator (`core/orchestrator`) | **Working** | Four nodes. Card-based routing with LLM fallback. Live observations override simulation baselines. No contradiction detection between agents. Synthesis is LLM prose that is not verified. |
| Sector agents (10) | **Uneven** | All exist and register. Prices, Fiscal, Real, Finance, Monetary have A2A handlers or peer support; others lag. Several modules exceed 400 lines. Curated seeds are tagged `cached`. |
| Knowledge graph | **Working, small** | 20 nodes, 12 edges, stable ids, schema validation, optional Neo4j. Edge statistics are seeded priors. |
| Scenario engine | **Prototype** | Heuristic, unit-blind, fixed default baselines, band is not an interval. Documentation previously called it VAR/IRF; that was wrong. |
| Research lab (`core/research`) | **Prototype with good labelling** | Trajectory, Twin, Radar, MPC, Edge Audit. Labels (`SIM`, `CACHED`, `heuristic`, `SEEDED`) are honest. Several statistics are underpowered. |
| Daily brief (`core/briefing`) | **Working** | Deterministic fallback, DuckDB history, optional cron. |
| Claim verification (`core/verification`) | **Library only** | Well designed, tested, not called by any code path. Prices integration was removed. |
| Dashboard and chat APIs | **Working** | Citations attached; missing-data tests exist. |
| Frontend | **Working, rule violations** | Builds with `tsc && vite build`; contains `any` and inline styles. No frontend tests. |
| RAG / Qdrant / PydanticAI | **Not implemented** | Documentary evidence is reported as unavailable. |

## 2. Verification of this review

Executed on 2026-10-12 with the repository `.venv`:

- `pytest --collect-only` with the default `testpaths`: **374 tests collected**. The other sector suites (fiscal, monetary, external, services, labour, capital markets, real) are **not in `testpaths`** and are therefore never run by a plain `pytest`.
- Full-suite result across all ten sector test sets: **550 passed, 1 failed** (11 min 55 s). Details in section 6.
- Static scans (grep): files over 400 lines, f-string SQL, bare `except ... pass`, missing `from __future__ import annotations`, TypeScript `any`, inline `style={{`.

## 3. Review findings (prioritised)

Severity: **P0** breaks a stated rule or invalidates a claim; **P1** correctness or robustness; **P2** hygiene.

### P0

1. **Verification layer is dead code, and documentation said otherwise.** `core/verification` has no caller. `prices_sector/agent.py` states the pipeline was removed. `docs/claim-verification.md` described it as live (now bannered). Either wire it into synthesis or stop advertising it.
2. **Seeded statistics presented as measured.** `ontology.py` assigns values such as `empirical_p_value=0.001` and `confidence_score=0.98`, and the schema rule "p-value may be None only for THEORY" pushes authors to type a number for every other edge. These feed trust scores and scenario deltas. This conflicts with "No source, no answer".
3. **Scenario engine is a heuristic with fixed constants and unit-blind arithmetic.** `delta = shock x prod(sign x 0.55 x confidence) x 0.15`; a +20 USD/bbl shock is mapped into percentage-point deltas on CPI. The "+/-25% band" is not statistical. `DEFAULT_BASELINES` embeds fixed numbers (for example repo 6.25, GDP growth 5.4) used whenever no live match exists; they are labelled `DEFAULT` but are still hard-coded numbers.
4. **Known wrong edge sign.** `trade_balance -> usd_inr` is `+`; `EDGE_NOTES` in `research/edge_audit.py` itself says the mechanism implies the opposite. A review note in the UI is not a fix.
5. **Silent failure paths contradict the "No Silent Failures" rule.**
   - `main.py` mounts optional sectors with `except (ImportError, AttributeError): pass`, so a broken sector disappears without a log line.
   - Sector DuckDB init failures are logged as warnings and the app starts anyway.
   - `research/edge_audit.audit_map` returns `{}` on any exception, which makes every edge silently read as `SEEDED`.
   - `core/sector_reasoning.py` swallows every exception around a key lookup (`except Exception: pass`), and that lookup imports `finance_sector.config` from `core`, a layering violation (core must not know sector packages; only `registry_bootstrap.py` may).

### P1

6. **Constants duplicated across modules.** `ATTENUATION`, `SCALE`, `BAND` are literals in `causal_engine.py` and mirrored in `core/research/__init__.py`, protected only by a test. Import one from the other (or a shared constants module) instead.
7. **Private-API and sentinel coupling to the LLM client.** `research/mpc.py` and `briefing/job.py` call `llm_client._get_api_key()` and compare responses with `llm_client._unavailable_notice()` strings. Expose a public `available` property and return a typed result (`LLMResult(text, ok)`).
8. **Granger audit is statistically weak.** Minimum overlap is 10 months, no stationarity check, no multiple-testing correction, `ssr_ftest` minimum over lags taken without adjustment (inflates false positives). Raise the minimum sample, difference to stationarity, correct the p-values.
9. **MPC simulator can leak and over-claim.** The evidence pack uses latest values, not the meeting-date vintage, so it cannot be evaluated historically; the six seats share three LLM calls (one per persona), so seats with the same persona vote identically: it is three voices, not six independent members. It is correctly labelled `SIMULATED`; keep that, and do not describe it as forecasting.
10. **Heuristic scores look like measurements.** `trust.score`, `consensus_quality`, `confidence_score` are products of fractions with arbitrary weights (0.4/0.3/0.3). They are labelled `heuristic`; calibrate them against verification outcomes or remove them.
11. **Unauthenticated, cost-bearing endpoints.** `/api/v1/brief/run`, `/api/v1/research/mpc/simulate`, `/api/v1/chat*` call paid LLM/search APIs with no auth or rate limit. Brief runs are debounced (15 minutes) but `force` bypasses it.
12. **Import-time side effects.** `main.py` initialises and seeds DuckDB stores at import. This hampers testing and multi-worker deployments (several workers write the same files). Move to an explicit startup hook that is guarded and fails loudly.
13. **Tests are partially excluded** (see section 2). Add every sector `tests/` directory to `testpaths`, or run them in CI.
14. **No evaluation of answer quality anywhere** (see `publication-plan.md`).

### P2

15. **Rule violations by letter.**
    - Over 400 lines (non-test): `labour_sector/parsers.py` (866), `labour_sector/client.py` (796), `api/dbie_sector_catalog.py` (705), `real_sector/client.py` (624), `agriculture_sector/agent.py` (610), `agriculture_sector/client.py` (569), `services_sector/agent.py` (548), `monetary_sector/client.py` (482), `capital_market_sector/client.py` (439).
    - Missing `from __future__ import annotations`: the A2A `agents/executor.py` files in six sectors, `demo_platform.py`, `prices_sector/config.py`, two test files.
    - `core/briefing/store.py` builds SQL with f-strings; the interpolated `_COLUMNS` is a module constant, so there is no injection path, but make the statements literals to match the rule.
    - Frontend: roughly 21 `any` occurrences and 23 inline `style={{` (concentrated in `CrossSectorStudio.tsx`, `Sidebar.tsx`, `LandingPage.tsx`, `lab/MiniLines.tsx`, `charts/SectorBreakdown.tsx`).
16. **Tracked files that should not be.** `backend/data/claim_audits.sqlite3` (binary audit data) and `frontend/vite.config.ts.timestamp-*.mjs` (Vite scratch file). Add to `.gitignore` and `git rm --cached`.
17. **Empty documentation directories** `docs/plan` and `docs/images`; either fill or remove.
18. **Broad `except Exception` with `# noqa: BLE001`** appears throughout `core/research` and `core/briefing`. Acceptable for "extras must not break the primary response", but each should log at warning level with context and surface a `degraded` flag in the payload so the UI can show it.
19. **Module-level caches** in `edge_audit.py` and `series_provider.py` use a 300-second TTL with `threading.Lock`; fine for one process, stale across workers.
20. **Default model naming.** The code defaults to `openai/gpt-oss-20b`/`120b` on Groq while older documents quoted Llama ids. Docs now match the code.

## 4. What is genuinely good (keep)

- Protocol-level provenance enforcement and declared dependency edges.
- Content-addressed evidence, Decimal-exact comparison, and "model prose is never rendered as fact" in `core/verification`.
- Labelled uncertainty everywhere in the lab payloads (`SIM`, `CACHED`, `heuristic`, `UNTESTABLE_*`).
- Stable relation ids and ontology validation (self-loops, unknown endpoints, duplicate ids).
- Offline deterministic fallbacks for synthesis, routing, brief and MPC.
- Regression tests for historical bugs recorded in `tasks/lessons.md`.

## 5. Roadmap

### Next two weeks (credibility)
- [ ] Wire `core/verification` into synthesis and at least Prices, Real and Monetary observations (publication contribution C1).
- [ ] Fix the `trade_balance -> usd_inr` sign; add a test that rejects an `EMPIRICAL` edge whose estimated sign contradicts the seeded sign.
- [ ] Replace silent `pass` handlers with logged, surfaced degradation (items 5, 18).
- [ ] Remove tracked binaries; extend `.gitignore`.
- [ ] Fix the failing monetary test (section 6), add all sector test dirs to `testpaths`; get a green full run in CI.
- [ ] Single source for `ATTENUATION`/`SCALE`/`BAND`.

### Next 4 to 8 weeks (research substance; see `publication-plan.md`)
- [ ] Estimated, not typed, edge statistics (stationarity, BH-corrected Granger, local projections, stability tests, long series).
- [ ] Replace the attenuation heuristic with local projections or a BVAR and back-test on named episodes; keep the heuristic as a baseline.
- [ ] Build `eval/` (question set, gold answers, baselines, ablations).
- [ ] Point-in-time data for the MPC benchmark; compare with actual RBI votes.
- [ ] Documentary evidence (RBI MPC minutes, Economic Survey) with passage-level attribution, or remove all RAG language permanently.

### Engineering hygiene
- [ ] Split the over-length modules (section 3, item 15).
- [ ] Remove `any` and inline styles in the frontend; add Vitest for the Causal Lab hooks.
- [ ] Authentication and rate limiting for cost-bearing endpoints.
- [ ] Replace import-time DuckDB initialisation with a startup hook.
- [ ] Persist the A2A trace (SQLite) for post-hoc analysis; it doubles as research data.

## 6. Test run record

Recorded from the full-suite run on 2026-10-12.

Command: `pytest -q backend/tests backend/finance_sector/tests backend/agriculture_sector/test_agriculture.py backend/fiscal_sector/tests backend/monetary_sector/tests backend/external_sector/tests backend/services_sector/tests backend/labour_sector/tests backend/capital_market_sector/tests backend/real_sector/tests`

Result: **550 passed, 1 failed, 3 warnings in 715 s.**

Failure: `backend/monetary_sector/tests/test_monetary_sector.py::TestStanceDerivation::test_agent_falls_back_to_stance_fetcher_when_rates_fail` asserts `repo_rate_pct == 5.0` (the stubbed stance fetcher value) but the agent returned `5.25`, which matches the value used by the neighbouring test. The agent appears to prefer another source (stored or cached rate) over the stubbed fallback, so either the test stub no longer exercises the fallback path or the agent's precedence changed. Not investigated further; treat as test/code drift in the Monetary sector.

Warning: statsmodels `FutureWarning` (`verbose` deprecated) from `CausalEconometricEngine.test_granger_causality`; drop the `verbose=False` argument when upgrading.

Frontend `npm run build` was not run in this review.

