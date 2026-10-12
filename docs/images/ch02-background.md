# Chapter 2: Background and Literature Survey - Figures

Chapter 2 positions the work against prior art. The seven reference papers stored in `base_papers/` are used as anchors. Do not add claims about those papers beyond what you have read in them; the diagrams below group them by theme only.

---

## Figure 2.1: Taxonomy of related work

<!-- fig: 2.1 related-work-taxonomy -->

- **Caption:** Figure 2.1: Taxonomy of the literature reviewed for this project.
- **Use in:** 2.1 Overview of the literature.
- **Description:** Five themes lead to the project. The leaf titles are the files in `base_papers/`. Add year and authors from the papers themselves when you cite them in APA format.

```mermaid
mindmap
  root((Related work))
    LLM agents in economics and finance
      LLM-based Economic agents
      AI Economist Agent
      A Multi-LLM-Agent-Based Framework
      TradingAgents Multi-Agents LLM Financial Trading
    Retrieval for financial question answering
      Metadata driven RAG for financial Q and A
    Knowledge graphs and graph-guided retrieval
      Knowledge Graph
      Knowledge Graph-Guided Retrieval Augmented Generation
    Agent interoperability protocols
      A2A agent to agent protocol
      Model Context Protocol
    Trustworthy generation
      Attributed question answering
      Deterministic verification of numbers
```

---

## Figure 2.2: Evolution of the approach: from single LLM to verified multi-agent system

<!-- fig: 2.2 approach-evolution -->

- **Caption:** Figure 2.2: Progression of architectures for macroeconomic question answering and where Macrograph-AI sits.
- **Use in:** 2.3 Gaps in existing work.
- **Description:** Each stage adds one capability and removes one weakness. Macrograph-AI implements stages 3 and 4 fully and stage 5 partially (verification is a library that is not yet wired into the answer path).

```mermaid
flowchart TB
    S1["Stage 1<br/>Single LLM<br/>fluent but ungrounded"]
    S2["Stage 2<br/>LLM with tools or RAG<br/>grounded in retrieved text"]
    S3["Stage 3<br/>Multi-agent LLM<br/>specialised roles"]
    S4["Stage 4<br/>Ownership-constrained agents<br/>A2A plus MCP plus provenance"]
    S5["Stage 5<br/>Verified claims<br/>typed claims checked against evidence"]
    S1 -->|"adds retrieval"| S2
    S2 -->|"adds decomposition"| S3
    S3 -->|"adds data ownership and typed protocol"| S4
    S4 -->|"adds claim gate"| S5
    W1["Weakness: invented numbers"] -.-> S1
    W2["Weakness: no cross-domain reasoning"] -.-> S2
    W3["Weakness: duplicated or conflicting data"] -.-> S3
    W4["Weakness: unverified prose"] -.-> S4
```

---

## Figure 2.3: Concept of A2A versus MCP

<!-- fig: 2.3 a2a-vs-mcp -->

- **Caption:** Figure 2.3: Separation of the agent-to-agent reasoning channel (A2A) and the agent-to-data channel (MCP).
- **Use in:** 2.4 Protocol background.
- **Description:** Two agents exchange conclusions horizontally over A2A, and each fetches raw data vertically over MCP from its own sources. The crossed-out dotted arrow is the forbidden path: an agent fetching another agent's data.

```mermaid
flowchart TB
    subgraph AG1["Prices agent"]
        R1["Reasoning"]
    end
    subgraph AG2["Monetary agent"]
        R2["Reasoning"]
    end
    R1 <-->|"A2A: conclusions, indicator signals"| R2
    R1 -->|"MCP tool call"| D1[("MoSPI e-Sankhyiki<br/>CPI and WPI")]
    R2 -->|"MCP tool call"| D2[("RBI DBIE<br/>repo and liquidity")]
    R1 -.->|"forbidden: raw fetch of peer data"| D2
```

---

## Figure 2.4: Comparison of system categories

<!-- fig: 2.4 category-comparison -->

- **Caption:** Figure 2.4: Qualitative positioning of system categories by verifiability of numbers and breadth of cross-domain reasoning.
- **Use in:** 2.3 Gaps in existing work.
- **Description:** The coordinates are the author's qualitative judgement, not measurements. State this in the text. Do not present it as a result.

```mermaid
quadrantChart
    title Qualitative positioning (author's assessment)
    x-axis "Low verifiability of numbers" --> "High verifiability of numbers"
    y-axis "Narrow single-domain reasoning" --> "Broad cross-domain reasoning"
    quadrant-1 "Broad and verifiable"
    quadrant-2 "Broad but weakly verified"
    quadrant-3 "Narrow and weakly verified"
    quadrant-4 "Narrow but verifiable"
    "Plain chat LLM": [0.12, 0.35]
    "RAG over reports": [0.45, 0.30]
    "Dashboards": [0.85, 0.18]
    "Generic multi-agent LLM": [0.30, 0.75]
    "Macrograph-AI current": [0.62, 0.82]
    "Macrograph-AI target": [0.88, 0.85]
```

---

## Figure 2.5: Research gap analysis

<!-- fig: 2.5 research-gap -->

- **Caption:** Figure 2.5: Gaps identified in the literature and the corresponding contributions of this work.
- **Use in:** 2.5 Research gaps and motivation.
- **Description:** Maps each gap to the mechanism built to address it and to the evidence in the repository.

```mermaid
flowchart LR
    G1["Gap 1<br/>Agents duplicate or contradict data"]
    G2["Gap 2<br/>Causal graphs rarely carry evidence grades"]
    G3["Gap 3<br/>Generated numbers are not machine-checked"]
    G4["Gap 4<br/>Macro agent systems seldom for India"]
    C1["Single-owner rule plus<br/>declared A2A edges"]
    C2["Seeded versus empirical<br/>edge audit"]
    C3["Typed claim verification<br/>with content-addressed evidence"]
    C4["Ten India-specific sector agents<br/>over official sources"]
    E1["core/protocols/a2a/dependencies.py"]
    E2["core/research/edge_audit.py"]
    E3["core/verification/"]
    E4["backend/*_sector/"]
    G1 --> C1 --> E1
    G2 --> C2 --> E2
    G3 --> C3 --> E3
    G4 --> C4 --> E4
```

---

## Figure 2.6: Technology selection map

<!-- fig: 2.6 technology-map -->

- **Caption:** Figure 2.6: Technologies chosen for each layer and the reason for the choice.
- **Use in:** 2.6 Tools and technologies (or Chapter 3).
- **Description:** Technologies shown are those actually used in the code. PydanticAI and Qdrant are intentionally absent because they are not implemented.

```mermaid
flowchart TB
    subgraph FE["Presentation"]
        T1["React 18, TypeScript, Vite, Tailwind"]
        T2["GSAP motion, Mermaid, react-markdown"]
    end
    subgraph GW["Gateway"]
        T3["FastAPI and Uvicorn"]
        T4["Server-Sent Events"]
    end
    subgraph OR["Orchestration and protocols"]
        T5["LangGraph StateGraph"]
        T6["Native A2A layer, Pydantic v2"]
        T7["FastMCP tool servers"]
    end
    subgraph AN["Analysis"]
        T8["NetworkX, optional Neo4j"]
        T9["statsmodels, pandas, NumPy"]
    end
    subgraph ST["Storage"]
        T10["DuckDB"]
        T11["SQLite audits"]
    end
    subgraph LL["LLM"]
        T12["Groq: gpt-oss-20b and gpt-oss-120b"]
        T13["Offline deterministic fallback"]
    end
    FE --> GW --> OR --> AN
    OR --> ST
    OR --> LL
```
