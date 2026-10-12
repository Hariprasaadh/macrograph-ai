# Chapter 1: Introduction - Figures

Chapter 1 should motivate the problem, state the objectives and scope, and present the working principles. Every diagram below is accurate to the code as of 2026-10-12. Render notes, caption style and the insertion procedure are in [README.md](README.md).

---

## Figure 1.1: Fragmented landscape of Indian macroeconomic data

<!-- fig: 1.1 fragmented-data-landscape -->

- **Caption:** Figure 1.1: Official Indian macroeconomic data is published by many agencies in different formats and cadences.
- **Use in:** 1.1 Introduction / Motivation.
- **Description:** Left side shows the publishing agencies (MoSPI, RBI, CGA and Union Budget, GST Council, DGCI&S, NSE and market feeds, IMD and agriculture ministries, EPFO). The middle shows the formats an analyst meets (APIs, Excel and PDF bulletins, web tables, press releases). The right shows the manual steps and the resulting problems. The message: the cost of cross-sector questions is integration, not access.

```mermaid
flowchart TB
    subgraph SRC["Publishing agencies"]
        A1["MoSPI: CPI, WPI, GDP, IIP, PLFS"]
        A2["RBI DBIE: rates, credit, NPA, reserves"]
        A3["CGA, Union Budget, GST Council"]
        A4["DGCI&S, NSE, SEBI, IMD, EPFO"]
    end
    subgraph FMT["Formats"]
        F1["APIs and MCP endpoints"]
        F2["Excel and PDF bulletins"]
        F3["HTML tables and press releases"]
    end
    subgraph MAN["Manual analyst workflow"]
        M1["Locate each series"] --> M2["Clean and align periods and units"] --> M3["Reason across sectors"] --> M4["Write cited report"]
    end
    subgraph PRB["Resulting problems"]
        P1["Slow and error prone"]
        P2["Inconsistent definitions"]
        P3["Weak provenance"]
    end
    SRC --> FMT --> M1
    M2 --> P2
    M3 --> P1
    M4 --> P3
```

---

## Figure 1.2: Problem, objectives and solution mapping

<!-- fig: 1.2 problem-objective-solution -->

- **Caption:** Figure 1.2: Mapping of identified problems to project objectives and the implemented components.
- **Use in:** 1.3 Problem Statement and 1.4 Objectives.
- **Description:** A three-column traceability diagram. Each problem has one objective and each objective maps to concrete modules in the repository, so the examiner can check that every objective is delivered.

```mermaid
flowchart LR
    subgraph P["Problems"]
        P1["P1 Data scattered across agencies"]
        P2["P2 Cross-sector reasoning is manual"]
        P3["P3 LLM answers can hallucinate numbers"]
        P4["P4 Causal links are implicit"]
        P5["P5 Hard to audit where a number came from"]
    end
    subgraph O["Objectives"]
        O1["O1 Sector-wise data access"]
        O2["O2 Coordinated multi-agent reasoning"]
        O3["O3 Source-grounded answers"]
        O4["O4 Explicit causal model and scenarios"]
        O5["O5 Traceable provenance"]
    end
    subgraph S["Implemented components"]
        S1["10 FastMCP sector servers<br/>and DuckDB stores"]
        S2["A2A layer and<br/>LangGraph orchestrator"]
        S3["No-source-no-answer rule,<br/>structured unavailable status"]
        S4["Knowledge graph and<br/>scenario engine"]
        S5["SourceProvenance, SHA-256<br/>provenance hash, A2A trace"]
    end
    P1 --> O1 --> S1
    P2 --> O2 --> S2
    P3 --> O3 --> S3
    P4 --> O4 --> S4
    P5 --> O5 --> S5
```

---

## Figure 1.3: Design principles of Macrograph-AI

<!-- fig: 1.3 design-principles -->

- **Caption:** Figure 1.3: Core design principles that govern every module of the platform.
- **Use in:** 1.5 Scope / Design principles (or start of Chapter 3).
- **Description:** A mind map with the project at the centre and five branches: protocol separation, single ownership, evidence discipline, graceful degradation and honest labelling. Each leaf is a rule that is enforced in code or tests.

```mermaid
mindmap
  root((Macrograph-AI principles))
    Protocol separation
      A2A is agent to agent reasoning only
      FastMCP is agent to data only
      Sectors never import each other
    Single ownership
      One owner agent per indicator
      Peers receive values through declared A2A edges
      Never recompute another sector's indicator
    Evidence discipline
      No source no answer
      Structured unavailable status
      Value plus period plus source table
    Graceful degradation
      Offline deterministic synthesis without LLM key
      Partial results when an agent fails
      Cached snapshots tagged cached
    Honest labelling
      SIM for simulated values
      SEEDED versus EMPIRICAL edges
      heuristic scores are labelled
```

---

## Figure 1.4: Scope of the project (implemented versus not implemented)

<!-- fig: 1.4 project-scope -->

- **Caption:** Figure 1.4: Project scope: implemented capabilities, prototypes and items explicitly out of scope.
- **Use in:** 1.6 Scope of the Project.
- **Description:** Three groups. Green nodes are implemented and tested; amber nodes are prototypes whose limits are documented; grey nodes are out of scope or future work. Stating the grey group openly avoids over-claiming in the viva.

```mermaid
flowchart TB
    IMP["IMPLEMENTED<br/>10 sector agents with MCP servers<br/>native A2A layer with guards and trace<br/>LangGraph orchestrator, 4 nodes<br/>knowledge graph, 20 nodes and 12 edges<br/>dashboard, streaming chat, A2A registry view"]
    PRO["PROTOTYPE WITH DOCUMENTED LIMITS<br/>heuristic scenario engine<br/>research lab: trajectory, twin, radar, MPC<br/>edge evidence audit<br/>daily early-warning brief<br/>claim verification library, not yet wired"]
    OUT["OUT OF SCOPE OR FUTURE WORK<br/>document RAG over RBI and Budget texts<br/>estimated causal edge statistics<br/>formal evaluation benchmark<br/>authentication on cost-bearing endpoints<br/>investment advice or forecasting guarantees"]
    IMP ~~~ PRO ~~~ OUT
```

---

## Figure 1.5: Project development timeline

<!-- fig: 1.5 development-timeline -->

- **Caption:** Figure 1.5: Development timeline derived from the repository history (16 July to 11 October 2026).
- **Use in:** 1.7 Project plan / Methodology of work.
- **Description:** A Gantt chart built from commit dates. Replace the phase names with your own milestone names if your guide expects different wording; the dates are real commit dates.

```mermaid
gantt
    title Development phases from repository history
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section Foundation
    Design document and literature papers       :done, a1, 2026-07-16, 2026-07-25
    First sector agents and A2A prototype        :done, a2, 2026-07-25, 2026-08-07
    FastMCP, SSE and DuckDB modernisation        :done, a3, 2026-08-23, 2026-08-24
    Canonical data layer and knowledge graph     :done, a4, 2026-08-23, 2026-08-24
    section Platform
    Refactor, docs and landing page              :done, b1, 2026-09-09, 2026-09-30
    Finance E2E and chat interface               :done, b2, 2026-10-02, 2026-10-03
    Monetary, external, capital, labour sectors  :done, b3, 2026-10-03, 2026-10-05
    section Completion
    Real, agriculture, prices, services, fiscal  :done, c1, 2026-10-04, 2026-10-07
    Orchestrator A2A and dashboard charts        :done, c2, 2026-10-09, 2026-10-10
    KG hardening and research lab                :done, c3, 2026-10-10, 2026-10-11
    Verification and sector fixes                :done, c4, 2026-10-11, 2026-10-12
```

---

## Figure 1.6: Illustrative user journey

<!-- fig: 1.6 user-journey -->

- **Caption:** Figure 1.6: Typical analyst journey with Macrograph-AI.
- **Use in:** 1.1 or Chapter 3 (user perspective).
- **Description:** Satisfaction scores (1 to 5) are illustrative, not measured; either remove the numbers or replace them after a user study.

```mermaid
journey
    title Analyst journey (illustrative scores)
    section Orientation
      Sign in and open dashboard: 4: Analyst
      Scan cross-sector telemetry with citations: 5: Analyst
    section Investigation
      Ask a cross-sector question in the workspace: 5: Analyst, Orchestrator
      Watch agents being called step by step: 4: Analyst
      Inspect causal paths and Mermaid diagram: 5: Analyst
    section Verification
      Open evidence drawer for a number: 5: Analyst
      Check unavailable agents list: 4: Analyst
    section Exploration
      Run a crude oil shock in the Causal Lab: 4: Analyst
      Read the daily early-warning brief: 4: Analyst
```
