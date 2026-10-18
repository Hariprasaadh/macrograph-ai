# Research images: where each one goes in main.tex

Upload this whole folder to Overleaf next to `main.tex`. `main.tex` uses the 300 dpi `.png` files.

Figures 14 and 15 are placeholders: replace them with real screenshots under the same filename.

| File | Section in the paper | Label | Content |
| :-- | :-- | :-- | :-- |
| 01_system_architecture.png | I Introduction | fig:architecture | Layered architecture, A2A plane vs MCP plane |
| 02_ownership_dependencies.png | III-B | fig:deps | Seven declared sector-to-sector A2A edges |
| 03_a2a_request_pipeline.png | III-C | fig:a2apipeline | A2A server guards and validation |
| 04_orchestrator_pipeline.png | III-F | fig:orchestrator | Four-node LangGraph orchestrator |
| 05_provenance_chain.png | III-E | fig:provenance | Source to report provenance chain |
| 06_causal_knowledge_graph.png | IV-A | fig:kg | 20 indicators, 12 edges, tier colours |
| 07_brent_scenario_results.png | V-C | fig:brent | Brent +20 USD/bbl measured results |
| 08_edge_evidence_audit.png | IV-D | fig:audit | Edge audit: 0 of 12 edges testable |
| 09_claim_verification_pipeline.png | VII | fig:verify | Typed-claim verification pipeline |
| 10_research_lab_modules.png | VI | fig:lab | Research lab modules |
| 11_test_composition.png | VIII-B | fig:tests | 455 test functions by area |
| 12_proposed_verification_gate.png | X | fig:gate | Future architecture with verification gate |
| 13_planned_evaluation_design.png | VIII-C | fig:evalplan | Planned evaluation (not executed) |
| 14_screenshot_chat_workspace.png | VIII-A | fig:screen1 | PLACEHOLDER: chat workspace screenshot |
| 15_screenshot_causal_lab.png | VIII-A | fig:screen2 | PLACEHOLDER: Causal Lab twin tab screenshot |

Figures 07 (values), 08 (audit statuses) and 11 (test counts) come from running the code and the test suite on 2026-10-12. Re-generate them if the ontology or tests change.
