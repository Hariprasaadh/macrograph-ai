# Report Figures: Diagram Descriptions, Mermaid Sources and Rendered Images

This folder contains every diagram proposed for the final project report (VIT Chennai template: `docs/detailed/BCE497J PROJECT REPORT TEMPLATE_ UPDATED.docx`). There are **98 figures in 10 chapter files**. Each figure has a numbered caption, the place to use it, a plain-language description (so you can also redraw it in draw.io or PowerPoint), and Mermaid source. All 98 are rendered to PNG (300 dpi class, scale 3) and SVG in `png/` and `svg/`, in greyscale for black-and-white printing.

Facts in every figure were taken from the code as of **2026-10-12**. Measured numbers (test counts, line counts, the Brent scenario) were produced by running the repository. Figures marked planned or proposed describe future work and must not be presented as results.

## Contents

| Path | Purpose |
| :-- | :-- |
| `ch01-introduction.md` to `ch10-conclusion-and-appendix.md` | One file per chapter: caption, use, description, Mermaid source |
| `png/` | Rendered PNG per figure (insert these into Word) |
| `svg/` | Vector versions (best for print quality and for editing in draw.io or Inkscape) |
| `src/` | Plain `.mmd` source per figure (paste into mermaid.live to tweak) |
| `mermaid-config.json`, `puppeteer-config.json`, `render-diagrams.mjs`, `package.json` | Rendering toolchain |

## How to insert a figure into the Word report

1. Insert the PNG (or SVG) with *Insert > Pictures*; set text wrapping to *In line with text* and centre it.
2. Add the caption below the figure using *References > Insert Caption*, label `Figure`, and paste the caption text from the chapter file. The template requires captions in Times New Roman, 10 pt or larger.
3. Keep figures numbered per chapter (`Figure 3.2`). Because the template lists "List of Figures", build it with *References > Insert Table of Figures* after all captions exist.
4. Refer to each figure in the running text before it appears ("as shown in Figure 3.2"). An uncited figure is a common viva question.
5. Page limits: the template allows 60 to 100 pages. Roughly 40 to 55 of these figures will fit in a 100-page report with text; the table below shows suggested priority.

Page margins from the template: left 3.81 cm, right 2.54 cm, top and bottom 2.54 cm. That leaves **14.6 cm x 21 cm** of usable area on a portrait page and about 23 cm x 15.9 cm on a landscape page. The **Page** column says which orientation gives the most legible result and **Print size** is the resulting effective font size of the diagram labels. Figures at 7 pt or above are comfortable; those between 5 and 7 pt are legible but small (put them on a full page or landscape page, or use the SVG and enlarge labels in draw.io).

## Suggested priority (what to include if space is limited)

| Priority | Figures |
| :-- | :-- |
| Must include (examiners expect these) | 1.2, 3.1, 3.2, 3.3, 3.5, 3.8, 4.1, 5.1, 5.2, 6.1, 6.5, 6.6, 9.1, 9.2, 10.1 |
| Strongly recommended | 1.3, 1.4, 2.1, 2.3, 3.6, 3.7, 3.9, 4.2, 4.5, 4.8, 4.9, 5.3, 5.4, 5.5, 5.8, 5.10, 6.2, 7.5, 7.7, 7.11, 9.4, 9.10, 10.4 |
| Include in an extended report | all remaining figures |
| Real screenshots to add (Chapter 8) | Figures 8.9 to 8.18, see the checklist at the end of `ch08-frontend-and-api.md` |

## Rendering the diagrams again

Needed only if you edit a Mermaid block. Requires Node 18 or newer and a Chromium download by Puppeteer.

```powershell
cd docs/images
npm install                         # installs @mermaid-js/mermaid-cli 11.4.2 and Chromium
node render-diagrams.mjs            # all figures, PNG and SVG
node render-diagrams.mjs --only 6.1 # a single figure
node render-diagrams.mjs --no-svg   # PNG only, faster
```

The script reads every `<!-- fig: N slug -->` marker followed by a mermaid block in `ch*.md`, writes `src/fig-N-slug.mmd`, and renders `png/` and `svg/`. Do not rename the marker comments. If the `png/` or `svg/` folders get large for version control, they can be regenerated at any time and may be added to `.gitignore`.

## Style rules used for all figures

- Greyscale theme (`neutral`) and Times New Roman labels, to match the template and survive black-and-white printing.
- Rectangles are components or steps, diamonds are decisions, cylinders are stores, dashed arrows are optional or future paths, quotes on edges are labels.
- Chapter 7 and Chapter 9 label simulated or planned content explicitly; keep those labels when you edit.
- Quadrant charts (2.4, 10.3) and the journey scores (1.6) are the author's qualitative assessments, not measurements. Say so in the text.

## Items to verify before final submission

1. **Figure 6.6, 6.7, 6.8** use the output of the scenario engine on 2026-10-12. Re-run if the ontology or constants change. Figure 6.6 shows USD/INR falling after an oil shock, which is a consequence of an edge sign the code itself flags as under review; fix the sign and regenerate, or discuss it as a limitation.
2. **Figures 9.1, 9.2, 9.4** use measured counts (455 test functions, 551 executed cases: 550 passed and 1 failed; line counts by component). Re-measure after any code change.
3. **Figure 1.5** uses real commit dates from the repository history; rename phases to your own milestone names if needed.
4. **Figure 2.1** lists the titles of the seven papers in `base_papers/`; add authors and years from the papers when writing the APA references.
5. **Chapter 8 screenshots** are not generated; capture them from the running app.
6. **Figure 5.10** source names should be checked against each sector README before printing.
7. **Figures 7.15, 9.6 to 9.9, 10.4 and 10.5** describe proposed or planned work. Introduce them as such.

## Master figure list


### Chapter 1 Introduction  ([ch01-introduction.md](ch01-introduction.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 1.1 | Fragmented landscape of Indian macroeconomic data | `png/fig-1-1-fragmented-data-landscape.png` | portrait | 6.0 pt |
| 1.2 | Problem, objectives and solution mapping | `png/fig-1-2-problem-objective-solution.png` | landscape | 10.1 pt |
| 1.3 | Design principles of Macrograph-AI | `png/fig-1-3-design-principles.png` | landscape | 13.3 pt |
| 1.4 | Scope of the project (implemented versus not implemented) | `png/fig-1-4-project-scope.png` | portrait | 10.3 pt |
| 1.5 | Project development timeline | `png/fig-1-5-development-timeline.png` | landscape | 13.3 pt |
| 1.6 | Illustrative user journey | `png/fig-1-6-user-journey.png` | landscape | 12.8 pt |

### Chapter 2 Background and Literature Survey  ([ch02-background.md](ch02-background.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 2.1 | Taxonomy of related work | `png/fig-2-1-related-work-taxonomy.png` | landscape | 13.3 pt |
| 2.2 | Evolution of the approach: from single LLM to verified multi-agent system | `png/fig-2-2-approach-evolution.png` | portrait | 8.3 pt |
| 2.3 | Concept of A2A versus MCP | `png/fig-2-3-a2a-vs-mcp.png` | landscape | 13.2 pt |
| 2.4 | Comparison of system categories | `png/fig-2-4-category-comparison.png` | portrait | 14.4 pt |
| 2.5 | Research gap analysis | `png/fig-2-5-research-gap.png` | landscape | 11.3 pt |
| 2.6 | Technology selection map | `png/fig-2-6-technology-map.png` | portrait | 6.7 pt |

### Chapter 3 System Design and Architecture  ([ch03-system-design.md](ch03-system-design.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 3.1 | System context diagram | `png/fig-3-1-system-context.png` | landscape | 5.7 pt |
| 3.2 | Layered architecture | `png/fig-3-2-layered-architecture.png` | portrait | 8.2 pt |
| 3.3 | Runtime deployment view | `png/fig-3-3-deployment-view.png` | landscape | 6.5 pt |
| 3.4 | Package dependency rules | `png/fig-3-4-package-dependencies.png` | landscape | 8.4 pt |
| 3.5 | Use case diagram | `png/fig-3-5-use-cases.png` | portrait | 7.4 pt |
| 3.6 | Internal structure of a sector agent package | `png/fig-3-6-sector-package-structure.png` | portrait | 8.1 pt |
| 3.7 | Indicator ownership and declared A2A dependencies | `png/fig-3-7-ownership-dependencies.png` | landscape | 11.0 pt |
| 3.8 | Canonical data model | `png/fig-3-8-canonical-data-model.png` | portrait | 6.3 pt |
| 3.9 | Class diagram of the A2A message model | `png/fig-3-9-a2a-class-diagram.png` | portrait | 7.6 pt |
| 3.10 | Class diagram of knowledge-graph and scenario components | `png/fig-3-10-kg-class-diagram.png` | landscape | 10.1 pt |
| 3.11 | Configuration and API-key topology | `png/fig-3-11-configuration-topology.png` | landscape | 7.1 pt |

### Chapter 4 Protocol Design (A2A and MCP)  ([ch04-protocols.md](ch04-protocols.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 4.1 | A2A request handling with nested peer call | `png/fig-4-1-a2a-sequence.png` | landscape | 8.2 pt |
| 4.2 | A2AServer validation pipeline | `png/fig-4-2-a2a-server-pipeline.png` | portrait | 4.8 pt |
| 4.3 | Loop-protection safeguards | `png/fig-4-3-loop-protection.png` | portrait | 6.2 pt |
| 4.4 | Life cycle of an A2A request | `png/fig-4-4-request-lifecycle.png` | portrait | 10.9 pt |
| 4.5 | Query routing over Agent Cards | `png/fig-4-5-query-routing.png` | portrait | 6.0 pt |
| 4.6 | Peer indicator exchange (finance and fiscal example) | `png/fig-4-6-peer-exchange.png` | landscape | 6.5 pt |
| 4.7 | Conversation trace tree | `png/fig-4-7-trace-tree.png` | landscape | 9.9 pt |
| 4.8 | MCP tool invocation and data fallback chain | `png/fig-4-8-mcp-invocation.png` | landscape | 8.2 pt |
| 4.9 | Provenance chain from source to report | `png/fig-4-9-provenance-chain.png` | portrait | 9.0 pt |
| 4.10 | Agent Card structure | `png/fig-4-10-agent-card.png` | landscape | 8.3 pt |

### Chapter 5 Orchestration, Sector Agents and Data Layer  ([ch05-orchestration-and-data.md](ch05-orchestration-and-data.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 5.1 | LangGraph orchestrator state graph | `png/fig-5-1-orchestrator-graph.png` | portrait | 10.6 pt |
| 5.2 | End-to-end sequence for a cross-sector query | `png/fig-5-2-end-to-end-sequence.png` | landscape | 7.0 pt |
| 5.3 | Chat routing decision (direct versus orchestrated) | `png/fig-5-3-chat-routing.png` | landscape | 7.8 pt |
| 5.4 | Delegation, follow-up round and aggregation | `png/fig-5-4-delegate-aggregate.png` | portrait | 6.5 pt |
| 5.5 | Structure of the generated report | `png/fig-5-5-report-structure.png` | portrait | 9.2 pt |
| 5.6 | LLM availability and deterministic fallback ladder | `png/fig-5-6-offline-fallback.png` | landscape | 7.1 pt |
| 5.7 | Live baseline override for scenarios | `png/fig-5-7-live-baselines.png` | portrait | 10.8 pt |
| 5.8 | Generic sector data pipeline | `png/fig-5-8-sector-data-pipeline.png` | portrait | 9.9 pt |
| 5.9 | Canonical ingestion pipeline | `png/fig-5-9-ingestion-pipeline.png` | portrait | 9.4 pt |
| 5.10 | Data sources by sector | `png/fig-5-10-data-sources-by-sector.png` | portrait | 6.9 pt |
| 5.11 | Sector DuckDB tables | `png/fig-5-11-sector-tables.png` | portrait | 5.5 pt |
| 5.12 | Direct sector agent reasoning pipeline | `png/fig-5-12-direct-agent-pipeline.png` | portrait | 6.3 pt |
| 5.13 | Resilience pattern for external calls | `png/fig-5-13-resilience.png` | portrait | 7.9 pt |

### Chapter 6 Causal Knowledge Graph and Scenario Engine  ([ch06-knowledge-graph-causal.md](ch06-knowledge-graph-causal.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 6.1 | The causal knowledge graph (20 indicators, 12 edges) | `png/fig-6-1-knowledge-graph.png` | portrait | 6.1 pt |
| 6.2 | Five-tier causal evidence taxonomy | `png/fig-6-2-causal-taxonomy.png` | portrait | 10.7 pt |
| 6.3 | Anatomy of a causal edge and validation rules | `png/fig-6-3-edge-anatomy.png` | landscape | 7.9 pt |
| 6.4 | Path and downstream-impact queries | `png/fig-6-4-graph-queries.png` | portrait | 8.3 pt |
| 6.5 | Scenario propagation algorithm | `png/fig-6-5-scenario-algorithm.png` | portrait | 8.2 pt |
| 6.6 | Worked example: Brent +20 USD per barrel | `png/fig-6-6-worked-example.png` | portrait | 9.5 pt |
| 6.7 | Impact of the shock by transmission lag (chart) | `png/fig-6-7-impact-chart.png` | landscape | 14.4 pt |
| 6.8 | Scenario fan: confidence of the path decays with hops | `png/fig-6-8-confidence-decay.png` | landscape | 14.4 pt |
| 6.9 | Neo4j mirroring | `png/fig-6-9-neo4j-sync.png` | landscape | 10.4 pt |
| 6.10 | Canonical indicator id mapping | `png/fig-6-10-canonical-id-mapping.png` | landscape | 8.9 pt |
| 6.11 | Knowledge-graph enrichment node | `png/fig-6-11-enrichment-node.png` | portrait | 7.8 pt |

### Chapter 7 Research Lab, Daily Brief and Claim Verification  ([ch07-research-lab-and-verification.md](ch07-research-lab-and-verification.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 7.1 | Research lab architecture | `png/fig-7-1-research-lab-overview.png` | landscape | 8.0 pt |
| 7.2 | Shockwave trajectory construction | `png/fig-7-2-shockwave-trajectory.png` | portrait | 7.8 pt |
| 7.3 | Twin: base world versus shocked world with attribution | `png/fig-7-3-twin-attribution.png` | landscape | 7.9 pt |
| 7.4 | Anomaly radar classification | `png/fig-7-4-anomaly-radar.png` | portrait | 6.3 pt |
| 7.5 | Edge evidence audit | `png/fig-7-5-edge-audit.png` | portrait | 6.5 pt |
| 7.6 | Edge evidence states | `png/fig-7-6-edge-evidence-states.png` | portrait | 12.6 pt |
| 7.7 | Simulated MPC meeting | `png/fig-7-7-mpc-simulation.png` | portrait | 7.4 pt |
| 7.8 | MPC rule logic per persona | `png/fig-7-8-mpc-rules.png` | portrait | 5.2 pt |
| 7.9 | Consensus and model-card computation | `png/fig-7-9-consensus-model-card.png` | landscape | 8.8 pt |
| 7.10 | Daily early-warning brief pipeline | `png/fig-7-10-daily-brief.png` | portrait | 6.1 pt |
| 7.11 | Claim verification pipeline | `png/fig-7-11-claim-verification-pipeline.png` | landscape | 6.7 pt |
| 7.12 | Verification status outcomes | `png/fig-7-12-verification-statuses.png` | landscape | 9.9 pt |
| 7.13 | Claim type model | `png/fig-7-13-claim-class-diagram.png` | landscape | 13.3 pt |
| 7.14 | Content-addressed evidence identity | `png/fig-7-14-evidence-identity.png` | landscape | 12.4 pt |
| 7.15 | Proposed verification gate in the orchestrator (future work) | `png/fig-7-15-proposed-verification-gate.png` | portrait | 8.5 pt |

### Chapter 8 User Interface and API  ([ch08-frontend-and-api.md](ch08-frontend-and-api.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 8.1 | Frontend navigation state machine | `png/fig-8-1-ui-navigation.png` | portrait | 10.8 pt |
| 8.2 | Frontend component hierarchy | `png/fig-8-2-component-hierarchy.png` | portrait | 8.6 pt |
| 8.3 | Streaming chat protocol (SSE) | `png/fig-8-3-sse-protocol.png` | landscape | 9.8 pt |
| 8.4 | API surface map | `png/fig-8-4-api-map.png` | portrait | 6.0 pt |
| 8.5 | Dashboard data flow | `png/fig-8-5-dashboard-dataflow.png` | landscape | 10.6 pt |
| 8.6 | Authentication and session flow | `png/fig-8-6-auth-flow.png` | landscape | 9.2 pt |
| 8.7 | Causal Lab tab structure | `png/fig-8-7-causal-lab-tabs.png` | landscape | 9.9 pt |
| 8.8 | Dashboard tab map | `png/fig-8-8-dashboard-tabs.png` | landscape | 13.3 pt |

### Chapter 9 Testing, Results and Evaluation  ([ch09-testing-and-evaluation.md](ch09-testing-and-evaluation.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 9.1 | Test suite composition by area | `png/fig-9-1-test-composition.png` | landscape | 13.3 pt |
| 9.2 | Result of the full test run | `png/fig-9-2-test-results.png` | landscape | 16.0 pt |
| 9.3 | Test pyramid of the project | `png/fig-9-3-test-pyramid.png` | portrait | 14.7 pt |
| 9.4 | Source code size by component | `png/fig-9-4-code-size.png` | landscape | 14.4 pt |
| 9.5 | Quality gates and verification workflow | `png/fig-9-5-quality-gates.png` | portrait | 10.8 pt |
| 9.6 | Proposed evaluation harness (planned) | `png/fig-9-6-evaluation-harness.png` | portrait | 6.4 pt |
| 9.7 | Ablation design (planned) | `png/fig-9-7-ablation-design.png` | landscape | 11.9 pt |
| 9.8 | Planned MPC benchmark | `png/fig-9-8-mpc-benchmark.png` | portrait | 9.1 pt |
| 9.9 | Edge-audit evaluation plan | `png/fig-9-9-edge-audit-plan.png` | portrait | 9.6 pt |
| 9.10 | Limitations and risk map | `png/fig-9-10-limitations.png` | portrait | 9.7 pt |

### Chapter 10 and Appendices  ([ch10-conclusion-and-appendix.md](ch10-conclusion-and-appendix.md))

| Figure | Title | File | Page | Print size |
| :-- | :-- | :-- | :-- | :-- |
| 10.1 | Objectives achieved | `png/fig-10-1-objectives-achieved.png` | portrait | 11.3 pt |
| 10.2 | Contributions of the work | `png/fig-10-2-contributions.png` | landscape | 13.3 pt |
| 10.3 | Maturity of components | `png/fig-10-3-maturity.png` | portrait | 14.4 pt |
| 10.4 | Future-work roadmap | `png/fig-10-4-roadmap.png` | landscape | 13.3 pt |
| 10.5 | Target architecture with the verification gate | `png/fig-10-5-target-architecture.png` | landscape | 6.9 pt |
| A.1 | Repository structure | `png/fig-A-1-repository-structure.png` | portrait | 6.2 pt |
| A.2 | Worked end-to-end example (conceptual) | `png/fig-A-2-example-query.png` | portrait | 9.6 pt |
| A.3 | Error-code taxonomy | `png/fig-A-3-error-taxonomy.png` | landscape | 13.3 pt |

## Suggested chapter-to-figure mapping for the report

| Report chapter (template) | Figures |
| :-- | :-- |
| 1 Introduction (overview, problem statement, objectives, scope) | 1.1 to 1.6 |
| 2 Background (survey, gaps, technologies) | 2.1 to 2.6 |
| 3 Proposed system and design | 3.1 to 3.11 |
| 4 Protocols (A2A, MCP, provenance) | 4.1 to 4.10 |
| 5 Implementation (orchestrator, data layer, sectors) | 5.1 to 5.13 |
| 6 Knowledge graph and scenario engine | 6.1 to 6.11 |
| 7 Research lab, brief and verification (novel contributions) | 7.1 to 7.15 |
| 8 User interface and API | 8.1 to 8.18 |
| 9 Testing, results and evaluation | 9.1 to 9.10 |
| 10 Conclusion and future work, Appendices | 10.1 to 10.5, A.1 to A.3 |

## Suggested List of Tables (for the report)

Tables are easier to read than diagrams for dense facts. These tables already exist in the repository docs and can be copied into the report:

| Table | Source |
| :-- | :-- |
| Indicator ownership and A2A consumers | `README.md`, section "One owner per indicator" |
| Declared sector-to-sector A2A dependencies (7 edges) | `docs/a2a-architecture.md` section 6 |
| A2A error codes and meanings | `docs/a2a-architecture.md` section 8 |
| Loop-protection settings | `docs/a2a-architecture.md` section 9 |
| The 12 causal edges (type, lag, sign, confidence) | `backend/core/knowledge_graph/ontology.py` (listed in Chapter 6 text) |
| Brent +20 scenario results | Figure 6.6 data |
| API endpoint reference | `docs/api-specification-and-runtime-guide.md` section 4 |
| Test suite composition and result | Figures 9.1 and 9.2 data |
| Component maturity and review findings | `docs/status-and-roadmap.md` |
| Related-work comparison (to be written from the seven papers) | `base_papers/` |
