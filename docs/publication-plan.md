# Publication Plan: from platform to paper

Assessment date: 2026-10-12. Written as an internal senior-review document. It is deliberately critical: reviewers will be.

## 1. Honest novelty assessment

| Element | Prior art | Publishable on its own? |
| :--- | :--- | :--- |
| Sector-decomposed LLM agents for macro/finance | EconAgent, AI Economist, TradingAgents, FinRobot-style systems (see `base_papers/`) | No. Decomposition is an engineering choice. |
| A2A for reasoning plus MCP for data | Both are public protocols with many demos | No. Systems/demo track at best. |
| LangGraph orchestrator with a cited report | Common pattern | No. |
| Knowledge graph plus GraphRAG | Large literature (see `base_papers/Knowledge Graph-Guided RAG.pdf`) | No, unless the graph is evidence-graded and evaluated. |
| Single-owner-per-indicator, enforced by protocol | Rarely stated as a constraint, never measured | Possible as a design principle if its effect is measured (contradiction rate). |
| Claim-level verification: typed claims, content-addressed evidence, Decimal recomputation, "model prose is never rendered as fact" | Related to fact-checking and attributed QA, but the deterministic typed-claim renderer for economic statistics is uncommon | **Yes, if generalised and evaluated.** Strongest asset. |
| Edge Evidence Audit: every causal edge labelled SEEDED vs EMPIRICAL by testing on live series | Causal discovery and Granger tests are classic; labelling a curated LLM-facing graph by evidence class and propagating it into answers is not common | **Yes, if edges are estimated properly.** |
| Anomaly radar classifying shocks as PROPAGATING / ISOLATED against graph neighbours | Anomaly detection is classic; graph-conditioned classification of macro anomalies is a reasonable contribution | Moderate, needs ground-truth episodes. |
| Simulated six-seat MPC, rule baseline vs LLM personas | LLM central-bank simulations exist; evaluating against actual RBI MPC votes (public minutes, ~60 meetings since 2016) is a clean test | **Yes, as an evaluation of LLM persona simulation vs a rule baseline.** |
| Graph-attenuation scenario engine (`0.55 x confidence` per hop, scale 0.15) | None. It is a heuristic | **No.** Reviewers will call it unfounded. Must be replaced or reframed. |

Conclusion: the platform as it stands is a well-engineered system with a few promising components but **no research claim that is supported by evidence**. There is no evaluation anywhere in the repository: no benchmark, no baseline, no ablation, no metric. A paper needs exactly those. The good news is that the verification layer, the evidence-class audit and the MPC simulator are each close to an evaluable contribution.

## 2. Recommended thesis

> **Verifiable multi-agent macro analysis: enforcing data ownership and claim-level verification in LLM agent systems, with an evidence-graded causal graph.**

One-sentence claim to defend: *an ownership-constrained multi-agent system whose every numeric and causal statement is verified against retrieved evidence, and whose causal edges carry an empirical evidence grade, produces fewer unsupported statements than single-LLM, RAG and unverified multi-agent baselines, at acceptable latency and coverage cost.*

Do not try to publish "a platform". Publish the three mechanisms and the evidence that they work.

### Contributions to claim (in order of strength)

1. **C1 Claim verification as a system-wide gate.** Generalise `core/verification` beyond Prices: claim types for observation, change, direction, ranking, cross-indicator comparison, and **causal claim bound to a KG edge and its evidence class**. The orchestrator's LLM synthesis proposes structured claims; only verified claims are rendered; the rest are withheld or hedged.
2. **C2 Evidence-graded causal graph.** Replace hand-typed `empirical_p_value`/`confidence_score` with estimated values (see 4.2). Each edge exposes `evidence_class`, sample size, lag, sign stability, and a stability test across sub-periods. Answers cite the grade and hedge SEEDED edges.
3. **C3 Ownership-enforced agents.** Formalise the single-owner rule and the declared dependency edges as constraints; measure cross-agent contradiction and duplicate-fetch rates with the constraint on and off.
4. **C4 Institutional-behaviour benchmark.** Simulated MPC vs actual RBI decisions and dissent, comparing the rule baseline, single-LLM, and multi-persona LLM (the repository already outputs `rule_baseline` next to the LLM result, which is the right shape for an ablation).
5. **C5 Released benchmark and artifact** (see 5). A public Indian-macro verification benchmark is itself citable and is the best hedge against a negative result.

## 3. What reviewers will attack, and the fix

| Weakness in the current code | Where | Fix before submission |
| :--- | :--- | :--- |
| Edge p-values and confidence scores are typed constants (for example `empirical_p_value=0.001`, `confidence_score=0.95`) | `core/knowledge_graph/ontology.py`; schema forbids `None` p-value except for THEORY | Make estimated statistics the only source; store `n`, estimator, sample window, data vintage; keep `confidence` as a documented function of those, not a free parameter |
| Scenario engine constants `0.55` and `0.15`, unit-blind deltas (a USD/bbl shock mapped into a % YoY target) | `core/econometrics/causal_engine.py` | Replace with local projections or a (B)VAR impulse response on standardised or log-difference series with bootstrap intervals; keep the old model only as a named baseline |
| `DEFAULT_BASELINES` are fixed numbers used when no live match exists | same file | Baselines come from the latest sourced observation or the run is refused with an unavailable status |
| The reported "+/-25% band" is not a confidence interval | `causal_engine.py`, `trajectory.py` notes admit this | Remove or replace with bootstrap/posterior intervals |
| Trust, consensus and "confidence" scores are ad-hoc products of fractions | `research/model_card.py`, `consensus.py`, `graph.py` | Either calibrate against verification outcomes (reliability diagram) or drop |
| Known wrong edge sign: `trade_balance -> usd_inr` is `+` but the mechanism implies `-` | `EDGE_NOTES` in `research/edge_audit.py` admits it | Fix the ontology edge; add a test that signs agree with estimated sign when `EMPIRICAL` |
| Verification layer is orphaned and its documentation claimed otherwise | `docs/claim-verification.md`; `prices_sector/agent.py` says it was removed | Wire it into synthesis (C1) or the headline contribution disappears |
| No evaluation harness | repository-wide | Build `eval/` (see 5) |
| Single country, single LLM family, small graph (20 nodes, 12 edges) | ontology | State as scope; add robustness across two or three LLMs; grow the graph with literature-sourced edges, each with a citation |
| Many Granger tests on short series (the audit needs only 10 monthly overlaps) | `research/edge_audit.py` | Multiple-testing correction (Benjamini-Hochberg), stationarity checks (ADF/differencing), minimum sample of at least 40, report untestable edges as such |

## 4. Technical work packages

### 4.1 Verification generalisation (C1)
- Extend `core/verification/models.py` claim union: `ComparisonClaim`, `RankingClaim`, `TrendClaim`, `CausalClaim(edge_id, direction, hedge_level)`.
- Evidence builder for every sector's `PriceObservation`-style record. A sector-neutral `Observation` model already exists in `core/data/schema.py` (`CanonicalObservation` with `provenance_hash`); unify on it.
- Synthesis contract: the LLM returns JSON claims plus a template id; the renderer produces prose. Anything outside the schema is dropped, as in `render_report`.
- Persist audits (already append-only SQLite) and expose `GET /api/v1/audit/{id}`.
- Metrics: claim precision/recall against gold, unsupported-claim rate, withheld-claim rate (the cost side), latency overhead.

### 4.2 Evidence-graded graph (C2)
- Pipeline: pull series through each owner sector, difference to stationarity (ADF/KPSS), test pairwise Granger at lags 1 to 6 with Benjamini-Hochberg control, estimate sign and magnitude by local projection, test stability on rolling or split samples.
- Edge record: `evidence_class` in {THEORY, ASSOCIATION, GRANGER, LP_STABLE, STRUCTURAL}, `n`, `p_adj`, `sign_est`, `sign_agrees_with_prior`, `window`, `vintage`. The existing five-tier enum maps onto this; keep it, but derive it from tests instead of hand assignment.
- Report the fraction of seeded edges the data supports, and which fail. A "30% of expert-seeded edges do not survive testing" finding is itself interesting.
- Data constraint to confront early: the series available through `core/research/series_provider.py` are short (often 10 to 14 points). Obtain long monthly histories (RBI DBIE, MoSPI back series) or restrict the claim to edges with enough data.

### 4.3 Scenario engine (supporting contribution)
- Local projections or BVAR on a core set (Brent, CPI, WPI, repo, credit growth, IIP, USD/INR).
- Back-test on named episodes: 2022 oil/Ukraine shock, 2022-23 repo cycle, 2013 taper tantrum, 2016 demonetisation, 2020 COVID. Metric: sign accuracy, peak-timing error, RMSE vs a no-change and an AR baseline. Keep the attenuation heuristic as an explicit weak baseline.

### 4.4 MPC benchmark (C4)
- Ground truth: RBI MPC resolutions and minutes (decision, vote split, dissenters) from 2016 onward.
- Inputs: only data available before each meeting date (point-in-time vintages are required to avoid look-ahead; the current evidence pack takes the latest values, which would leak).
- Arms: majority-class (always HOLD), Taylor-rule baseline, current `rule_baseline`, single-LLM, three-persona LLM. Metrics: decision accuracy, direction accuracy at turning points, dissent correlation.
- Note the rule baseline currently hardcodes thresholds (2%, 4%, 6%); that is defensible as the inflation-targeting band, but state it as such.

### 4.5 Ownership ablation (C3)
- Arm A: ownership enforced (current). Arm B: agents may fetch any indicator. Arm C: single agent with all tools.
- Metrics: duplicated fetches, contradictory values for the same indicator within one answer, tool-call count, latency, and verified-claim rate.

## 5. Evaluation design

Create `eval/` with: a question set (target 200 to 300), gold answers computed directly from official series (not from model output), a grader, and a runner producing a results table.

| Question type | Count | Gold from | Primary metric |
| :--- | :-: | :--- | :--- |
| Point lookup ("CPI YoY for March 2025") | 60 | official series | exact match to displayed precision |
| Change / direction | 50 | recomputed from series | numeric correctness |
| Cross-sector synthesis | 50 | rubric over cited indicators | claim-level precision, citation validity |
| Causal / scenario | 40 | edge evidence class, back-test | hedge-appropriateness, sign accuracy |
| Unanswerable (data absent or future period) | 40 | none | correct abstention rate |

Systems compared: (1) single LLM, no tools; (2) single LLM with web search; (3) RAG over the same documents; (4) multi-agent without verification (current production path); (5) multi-agent with verification (proposed); plus ablations: no ownership, no evidence grading. Report mean and 95% bootstrap intervals over at least 3 seeds, and at least two LLM backends. Report cost and latency.

Most important headline numbers: **unsupported numeric claim rate**, **abstention correctness**, **verified-claim coverage**.

## 6. Reproducibility checklist (do before any submission)

- Freeze data vintages: snapshot every source used in the eval (DuckDB file hash recorded in results). Live endpoints change.
- Fixed prompts, model ids, temperature and seeds stored with each run (`audit_*` records already carry evidence snapshots; extend with prompt and model).
- One command to reproduce tables: `make eval` or `python -m eval.run --suite all`.
- Release code, benchmark and frozen data under a licence compatible with the sources (MoSPI/RBI terms must be checked per dataset).
- Remove binaries from version control (`backend/data/claim_audits.sqlite3`, the Vite timestamp file) and keep audit samples as JSON in `eval/`.
- Ethics/limitations: no investment advice, simulated MPC is a model not a forecast, LLM provider data handling.

## 7. Venue strategy

| Venue type | Fit | Notes |
| :--- | :--- | :--- |
| Workshop on LLMs in finance or NLP-for-finance (for example the ICAIF, FinNLP or NeurIPS/ICLR finance-AI workshop family) | Good first target | Accepts a focused C1+C2 paper with a modest benchmark; 4 to 8 pages |
| Applied-AI journal (for example Expert Systems with Applications, Decision Support Systems) | Good for the full system plus evaluation | Expect a long review cycle; needs a thorough related-work section and the ablations |
| Computational economics venue (for example Computational Economics, Journal of Economic Dynamics and Control special issues) | Only if the scenario engine becomes a credible econometric model with back-tests | Economists will scrutinise identification |
| Systems/demo track | Fallback for the platform itself | Lowest bar, lowest impact |

Check each venue's current call and page limit before committing; confirm deadlines yourself.

## 8. Suggested timeline (8 to 12 weeks)

| Weeks | Deliverable |
| :-: | :--- |
| 1-2 | Freeze scope. Wire verification into synthesis; remove binaries from the repo; fix ontology sign and constants issue list (section 3). |
| 3-4 | Evidence-graded graph pipeline (4.2); long series ingestion; multiple-testing and stationarity handling. |
| 5-6 | `eval/` harness, question set, gold answers, baselines 1 to 5. |
| 7-8 | Ablations (ownership, grading), MPC benchmark with point-in-time data. |
| 9 | Scenario back-tests (4.3) if time allows; otherwise reframe as future work. |
| 10-12 | Write: related work (use `base_papers/`), method, results, limitations; internal review; submit. |

## 9. What is already a strength and should be showcased

- Content-addressed evidence IDs where retrieval time does not change identity but revisions do (`core/verification/evidence.py`).
- Decimal arithmetic compared at displayed precision, no hidden float tolerance (`numeric.py`).
- Quote attribution requiring complete source sentences and refusing to certify causation (`qualitative.py`).
- A2A guards: declared dependency edges, loop and hop limits, correlation ids and a trace store.
- Honest labelling already present in the UI payloads (`SIM`, `CACHED`, `heuristic`, `SEEDED`, `UNTESTABLE_N`). Keep this culture; it is what reviewers reward.
