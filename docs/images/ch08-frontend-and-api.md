# Chapter 8: User Interface and API - Figures

Besides the diagrams, this chapter needs real screenshots. A capture checklist is at the end of this file (Figures 8.9 to 8.18). Take screenshots at 1440 x 900 in the dark theme, crop the browser chrome, and save as PNG into `docs/images/screenshots/`.

---

## Figure 8.1: Frontend navigation state machine

<!-- fig: 8.1 ui-navigation -->

- **Caption:** Figure 8.1: Top-level views of the web application and the transitions between them.
- **Use in:** 8.1 Frontend architecture.
- **Description:** An unauthenticated visitor sees the landing page. After Google sign-in (or restored session from local storage) the sidebar switches among four workspace views. Sign-out clears the stored profile and returns to the landing page.

```mermaid
stateDiagram-v2
    [*] --> Landing
    Landing --> AuthModal : Sign in
    AuthModal --> Dashboard : login success
    Landing --> Dashboard : stored session exists
    Dashboard --> Chat : sidebar Workspace
    Dashboard --> CausalLab : sidebar Graph
    Dashboard --> A2ARegistry : sidebar Registry
    Chat --> Dashboard
    Chat --> CausalLab
    Chat --> A2ARegistry
    CausalLab --> Dashboard
    CausalLab --> Chat
    CausalLab --> A2ARegistry
    A2ARegistry --> Dashboard
    A2ARegistry --> Chat
    A2ARegistry --> CausalLab
    Dashboard --> Landing : Sign out
    Chat --> Landing : Sign out
    CausalLab --> Landing : Sign out
    A2ARegistry --> Landing : Sign out
```

---

## Figure 8.2: Frontend component hierarchy

<!-- fig: 8.2 component-hierarchy -->

- **Caption:** Figure 8.2: React component hierarchy of the application.
- **Use in:** 8.1 Frontend architecture.
- **Description:** `App` owns session and view state. The dashboard is split into eight tabs, the chat workspace renders streaming markdown, tables and Mermaid, and the Causal Lab is a tab shell around the knowledge-graph view and the four research tabs.

```mermaid
flowchart LR
    APP["App<br/>session and view state"]
    APP --> LP["LandingPage"]
    APP --> GA["GoogleAuthModal"]
    APP --> SB["Sidebar"]
    APP --> DV["DashboardView<br/>tabs: All, Finance, Fiscal, External, Markets, Real and Labour, States, DBIE<br/>studio: ScenarioSimulator, CrossSectorStudio, AnomalyFeed, EarlyWarningBrief<br/>charts, EvidenceDrawer, CommandPalette"]
    APP --> CW["ChatWorkspace<br/>MarkdownMessage, ScrollableTable, MermaidDiagram,<br/>A2ATracePanel, DebateDag, ModelCardStrip"]
    APP --> CL["CausalLabView<br/>KnowledgeGraphView, ShockwaveTab, TwinTab, RadarTab, MpcTab"]
    APP --> AR["A2ARegistryView"]
```

---

## Figure 8.3: Streaming chat protocol (SSE)

<!-- fig: 8.3 sse-protocol -->

- **Caption:** Figure 8.3: Server-Sent Events protocol between the chat workspace and the gateway.
- **Use in:** 8.3 Chat interface.
- **Description:** The browser reads the response stream with `fetch` and an `AbortController` so a new question cancels the previous one. Event types are `step` (agent or tool progress, updated in place by `request_id`), `token` (report text chunks) and `done` (final payload).

```mermaid
sequenceDiagram
    participant B as ChatWorkspace
    participant S as POST /api/v1/chat/stream
    B->>S: JSON message and agent (AbortController signal)
    loop while agents run
        S-->>B: data type step, request_id, status running
        S-->>B: data type step, same request_id, status completed
    end
    loop report text
        S-->>B: data type token, text chunk
    end
    S-->>B: data type done, full_report, citations, a2a, consensus, model_card, causal_paths, scenario_result
    B->>B: render markdown, tables, Mermaid, trace panel, model card
    Note over B,S: User sends a new question: previous request aborted
```

---

## Figure 8.4: API surface map

<!-- fig: 8.4 api-map -->

- **Caption:** Figure 8.4: HTTP API surface of the gateway grouped by router.
- **Use in:** 8.2 Backend API design.
- **Description:** One box per router. Sector sub-apps are mounted under their own prefix and expose data endpoints for their own domain. The research and brief routers are loaded in a guarded block so a failure there cannot stop the gateway.

```mermaid
flowchart LR
    GW["FastAPI gateway :8000"]
    GW --> SYS["System<br/>GET /, GET /health"]
    GW --> ORC["Orchestrator<br/>POST /api/v1/analyze"]
    GW --> SIM["Econometrics<br/>POST /api/v1/simulate"]
    GW --> KGE["Knowledge graph<br/>GET /api/v1/kg/path, /kg/impacts"]
    GW --> CHT["Chat<br/>POST /api/v1/chat, /chat/stream"]
    GW --> DSH["Dashboard<br/>GET /api/v1/dashboard/overview"]
    GW --> RES["Research<br/>/api/v1/research/kg/graph, edges/audit,<br/>trajectory, compare, anomalies, mpc/simulate"]
    GW --> BRF["Brief<br/>/api/v1/brief/today, run, history"]
    GW --> A2A["A2A<br/>/a2a/registry, /a2a/v1/agents, capabilities,<br/>requests, traces"]
    GW --> SUB["Sector sub-apps<br/>/real-sector, /finance-sector, /fiscal-sector,<br/>/capital-markets, /labour-sector, /agriculture-sector,<br/>/external-sector, /prices-sector, /monetary-sector, /services-sector"]
```

---

## Figure 8.5: Dashboard data flow

<!-- fig: 8.5 dashboard-dataflow -->

- **Caption:** Figure 8.5: Data flow of the dashboard overview endpoint.
- **Use in:** 8.4 Dashboard.
- **Description:** The overview endpoint aggregates sector telemetry from DuckDB stores plus open datasets and the RBI DBIE explorer. Each indicator keeps its citation so the UI can open the evidence drawer.

```mermaid
flowchart TB
    UI["DashboardView"] -->|"GET /api/v1/dashboard/overview"| RT["dashboard router"]
    RT --> H["dashboard_helpers<br/>query_*_telemetry per sector"]
    H --> D1[("Sector DuckDB stores")]
    RT --> OD["open_data_helpers<br/>budget, states, employment, economy datasets"]
    RT --> DB["dbie_sector_catalog<br/>RBI DBIE tables"]
    D1 --> AG["aggregate payload with citations and freshness"]
    OD --> AG
    DB --> AG
    AG --> UI
    UI --> EVD["EvidenceDrawer shows source, table, period, calculation"]
```

---

## Figure 8.6: Authentication and session flow

<!-- fig: 8.6 auth-flow -->

- **Caption:** Figure 8.6: Google sign-in and local session handling.
- **Use in:** 8.5 Authentication.
- **Description:** The client id comes from `VITE_GOOGLE_CLIENT_ID` or from the sign-in modal. The decoded profile is stored in the browser's local storage; there is no server-side session, so the gateway endpoints themselves are not protected (listed as a limitation in Chapter 9).

```mermaid
sequenceDiagram
    actor U as User
    participant L as LandingPage
    participant M as GoogleAuthModal
    participant G as Google Identity Services
    participant A as App state
    U->>L: click Sign in
    L->>M: open modal
    M->>G: request credential (client id)
    G-->>M: signed JWT credential
    M->>M: decode profile (name, email, picture)
    M->>A: onLoginSuccess(profile)
    A->>A: save profile in localStorage
    A-->>U: Dashboard view
    U->>A: Sign out
    A->>A: remove profile
    A-->>U: Landing view
```

---

## Figure 8.7: Causal Lab tab structure

<!-- fig: 8.7 causal-lab-tabs -->

- **Caption:** Figure 8.7: The Causal Lab workspace and the backend endpoint behind each tab.
- **Use in:** 8.6 Causal Lab.
- **Description:** Five tabs share a data hook (`useResearchApi`) that calls the research endpoints; every response carries labels so the UI can show SIM, CACHED and heuristic badges.

```mermaid
flowchart LR
    LAB["CausalLabView"] --> T1["Path<br/>GET /research/kg/graph and /kg/path"]
    LAB --> T2["Shockwave<br/>POST /research/trajectory"]
    LAB --> T3["Twin<br/>POST /research/compare"]
    LAB --> T4["Radar<br/>GET /research/anomalies"]
    LAB --> T5["MPC<br/>POST /research/mpc/simulate"]
    T1 --> HK["useResearchApi hook"]
    T2 --> HK
    T3 --> HK
    T4 --> HK
    T5 --> HK
    HK --> BADGE["badges: SIM, CACHED, heuristic, SEEDED, EMPIRICAL"]
```

---

## Figure 8.8: Dashboard tab map

<!-- fig: 8.8 dashboard-tabs -->

- **Caption:** Figure 8.8: Dashboard tabs and the sectors that feed each of them.
- **Use in:** 8.4 Dashboard.
- **Description:** Eight tabs. The first combines cross-sector studio widgets; the last is a live explorer for RBI DBIE tables.

```mermaid
mindmap
  root((Dashboard))
    All Sectors Intelligence
      Executive cockpit
      Scenario simulator
      Cross-sector studio
      Anomaly feed
      Early-warning brief
    Finance and Banking
      Credit growth
      Asset quality gauges
      WALR and deposit spread
      Sectoral deployment
    Fiscal and Union Budget
      Budget summary
      Ministry allocations
      Monthly GST
    External and Forex
      USD INR
      Forex reserves
      Trade balance
    Capital Markets and Rates
      G-Sec yield
      India VIX
      Policy rate corridor
    Real Sector and Labour
      Core industries
      Services PMI
      PLFS unemployment
    State Finances and GSDP
      GSDP leaderboard
    RBI DBIE Live Explorer
      Table browser
```

---

## Screenshot checklist (Figures 8.9 to 8.18)

Capture each of the following from the running application. Use this table directly as the figure list. Filename pattern: `fig-8-N-name.png`.

| Figure | Screen to capture | Notes |
| :-- | :-- | :-- |
| 8.9 | Landing page | Hero and feature cards |
| 8.10 | Google sign-in modal | Hide any real client id |
| 8.11 | Dashboard, All Sectors tab | Show KPI cards and a chart |
| 8.12 | Dashboard, Finance tab | Gauges and spread chart |
| 8.13 | Evidence drawer open on one KPI | Shows source, table, period |
| 8.14 | Chat workspace mid-stream | Step cards visible |
| 8.15 | Chat final report with Mermaid causal diagram and tables | Scroll so diagram and indicator matrix are visible |
| 8.16 | A2A trace panel for one run | Request tree, timings |
| 8.17 | A2A registry view | Agent cards and dependency edges |
| 8.18 | Causal Lab: one screenshot each of Path, Shockwave, Twin, Radar, MPC (name them 8.18a to 8.18e) | MPC must show the SIMULATED label |
