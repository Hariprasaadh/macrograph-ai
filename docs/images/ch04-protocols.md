# Chapter 4: Protocol Design (A2A and MCP) - Figures

These figures explain how agents talk to each other and to data. They are derived from `backend/core/protocols/a2a`, `docs/a2a-architecture.md` and the sector MCP servers.

---

## Figure 4.1: A2A request handling with nested peer call

<!-- fig: 4.1 a2a-sequence -->

- **Caption:** Figure 4.1: Sequence of an A2A delegation in which a sector agent requests a peer indicator.
- **Use in:** 4.1 Agent-to-agent communication.
- **Description:** The orchestrator sends `sector_analysis` to the external-sector agent. While loading its own data, that agent asks the monetary agent for the repo rate. The server enforces guards on both hops and sources travel unchanged back to the orchestrator.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as A2AServer
    participant X as external_sector handler
    participant M as monetary_sector handler
    O->>S: A2ARequest sector_analysis (depth 0)
    S->>S: guards, dependency check, capability check, schema check
    S->>X: handler(request, context)
    X->>S: A2ARequest repo_rate (parent = first request, depth 1)
    S->>S: guards, edge external to monetary allowed
    S->>M: handler
    M-->>S: HandlerOutput (IndicatorSignal and SourceProvenance)
    S-->>X: A2AResponse (sources preserved)
    X-->>S: HandlerOutput
    S-->>O: A2AResponse (report, observations, sources)
```

---

## Figure 4.2: A2AServer validation pipeline

<!-- fig: 4.2 a2a-server-pipeline -->

- **Caption:** Figure 4.2: Validation pipeline applied by the A2A server to every request.
- **Use in:** 4.2 Protocol enforcement.
- **Description:** Each diamond is a guard that returns a structured failure response (never an exception across agents) with a stable error code. Only a request that passes all guards reaches the handler. A non-failed response without sources is rejected, which enforces "No Source, No Answer" at protocol level.

```mermaid
flowchart TB
    IN["A2ARequest received"] --> G1{"Receiver registered?"}
    G1 -->|"no"| F["Failed A2AResponse<br/>stable error code, see Figure A.3"]
    G1 -->|"yes"| G2{"Loop guard passed?"}
    G2 -->|"no"| F
    G2 -->|"yes"| G3{"Sector edge declared<br/>or sender unrestricted?"}
    G3 -->|"no"| F
    G3 -->|"yes"| G4{"Task supported<br/>and handler present?"}
    G4 -->|"no"| F
    G4 -->|"yes"| G5{"Parameters valid?"}
    G5 -->|"no"| F
    G5 -->|"yes"| H["Run handler with timeout"]
    H -->|"timeout or error"| F
    H -->|"output"| G6{"Valid result type<br/>and sources present?"}
    G6 -->|"no"| F
    G6 -->|"yes"| OK["A2AResponse: success or partial"]
```

---

## Figure 4.3: Loop-protection safeguards

<!-- fig: 4.3 loop-protection -->

- **Caption:** Figure 4.3: Loop and runaway-delegation protection in the A2A layer.
- **Use in:** 4.3 Safety and reliability.
- **Description:** Four checks run before any handler. Limits come from settings: depth 5, 25 requests per conversation, 90 s request timeout and 25 s peer timeout by default.

```mermaid
flowchart TB
    R["Incoming request<br/>conversation_id, depth, call_chain"] --> C1{"depth greater than<br/>A2A_MAX_DEPTH (5)?"}
    C1 -->|"yes"| X1["reject: MAX_DEPTH_EXCEEDED"]
    C1 -->|"no"| C2{"requests in conversation<br/>greater than A2A_MAX_HOPS (25)?"}
    C2 -->|"yes"| X2["reject: MAX_HOPS_EXCEEDED"]
    C2 -->|"no"| C3{"receiver already<br/>in call_chain?"}
    C3 -->|"yes"| X3["reject: CIRCULAR_DELEGATION"]
    C3 -->|"no"| C4{"same sender, parent, receiver,<br/>task and parameters seen?"}
    C4 -->|"yes"| X4["reject: DUPLICATE_REQUEST"]
    C4 -->|"no"| OKR["accept and record in trace"]
```

---

## Figure 4.4: Life cycle of an A2A request

<!-- fig: 4.4 request-lifecycle -->

- **Caption:** Figure 4.4: State diagram of an A2A request including retry of retryable failures.
- **Use in:** 4.3 Reliability.
- **Description:** Only `AGENT_TIMEOUT` and `TRANSPORT_ERROR` are retried (exponential backoff, same `request_id`). The orchestrator sends full analyses with zero retries because they are expensive.

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Validated : guards pass
    Created --> Failed : guard rejects
    Validated --> Running : handler starts
    Running --> Success : output with sources
    Running --> Partial : output with errors
    Running --> RetryWait : AGENT_TIMEOUT or TRANSPORT_ERROR
    RetryWait --> Running : retries left
    RetryWait --> Failed : retries exhausted
    Running --> Failed : other error
    Success --> [*]
    Partial --> [*]
    Failed --> [*]
```

---

## Figure 4.5: Query routing over Agent Cards

<!-- fig: 4.5 query-routing -->

- **Caption:** Figure 4.5: Capability-based routing of a user query to sector agents.
- **Use in:** 4.4 Agent discovery and routing.
- **Description:** The query is tokenised and matched against each card's capabilities, skill tags and keywords. A phrase advertised by several agents is divided by the number advertising it, so a shared word such as "rbi" does not pull in unrelated sectors. The LLM is only a fallback and its answer is intersected with registered agent ids.

```mermaid
flowchart TB
    Q["User query"] --> SC["Tokenise and stem, then score every Agent Card<br/>capabilities, skill tags, keywords<br/>a phrase shared by n agents counts 1 over n"]
    SC --> TH{"Agent at or above<br/>distinctive threshold?"}
    TH -->|"yes"| TOP["Select up to 5 best agents"]
    TH -->|"no"| LLM{"LLM routing enabled and key present?"}
    LLM -->|"yes"| ASK["Ask LLM for JSON array,<br/>intersect with registered agent ids"]
    LLM -->|"no"| DEF["Use A2A_DEFAULT_AGENTS"]
    ASK --> NE{"Any agent left?"}
    NE -->|"yes"| TOP
    NE -->|"no"| DEF
    TOP --> DEC["RoutingDecision: method and choices"]
    DEF --> DEC
```

---

## Figure 4.6: Peer indicator exchange (finance and fiscal example)

<!-- fig: 4.6 peer-exchange -->

- **Caption:** Figure 4.6: A sector agent obtaining peer indicators through A2A while preparing its own analysis.
- **Use in:** 4.5 Cross-sector collaboration.
- **Description:** The fiscal agent needs repo rate, CPI and bank credit growth. It never calls those sectors' code or databases. It asks through `gather_peer_context`, receives `IndicatorSignal` objects with provenance, and degrades to an "unavailable" line if a peer fails.

```mermaid
sequenceDiagram
    participant FI as fiscal_sector
    participant P as peers.gather_peer_context
    participant S as A2AServer
    participant MO as monetary_sector
    participant PR as prices_sector
    participant FN as finance_sector
    FI->>P: need repo_rate, cpi_headline, bank_credit_growth
    par concurrent peer tasks
        P->>S: repo_rate
        S->>MO: handler
        MO-->>S: IndicatorSignal and sources
    and
        P->>S: cpi_headline
        S->>PR: handler
        PR-->>S: IndicatorSignal and sources
    and
        P->>S: bank_credit_growth
        S->>FN: handler
        FN-->>S: IndicatorSignal and sources
    end
    S-->>P: three responses
    P-->>FI: peer context with provenance, failures as unavailable lines
    FI->>FI: reason over own data plus peer signals
```

---

## Figure 4.7: Conversation trace tree

<!-- fig: 4.7 trace-tree -->

- **Caption:** Figure 4.7: Example delegation tree reconstructed by the trace store for one conversation.
- **Use in:** 4.6 Traceability.
- **Description:** Every request has a parent, so the trace store can rebuild the call tree per `conversation_id` (`GET /a2a/v1/traces/{id}`). Node labels show task, status and an example duration; replace them with a screenshot of the A2A trace panel from your run for the final report.

```mermaid
flowchart TB
    C["conversation conv-xxxx"]
    C --> R1["req-1 orchestrator to external_sector<br/>sector_analysis, success, 412 ms"]
    C --> R2["req-2 orchestrator to prices_sector<br/>sector_analysis, success, 530 ms"]
    C --> R3["req-3 orchestrator to monetary_sector<br/>sector_analysis, partial, 610 ms"]
    R1 --> R4["req-4 external_sector to monetary_sector<br/>repo_rate, success, 90 ms"]
    R1 --> R5["req-5 external_sector to prices_sector<br/>cpi_headline, success, 85 ms"]
```

---

## Figure 4.8: MCP tool invocation and data fallback chain

<!-- fig: 4.8 mcp-invocation -->

- **Caption:** Figure 4.8: An agent retrieving data through its own FastMCP server, with the fallback order.
- **Use in:** 4.7 Agent-to-data layer.
- **Description:** The agent calls a typed MCP tool. The tool tries the live official source; on failure it serves the sector's cached DuckDB snapshot tagged `cached`; if neither exists it returns a structured `unavailable` result. It never fabricates a number.

```mermaid
sequenceDiagram
    participant A as Sector agent
    participant C as FastMCP client
    participant T as Sector MCP tool
    participant L as Live official source
    participant D as Sector DuckDB cache
    A->>C: call tool with typed parameters
    C->>T: MCP request
    T->>L: fetch with Tenacity retry
    alt live data available
        L-->>T: payload
        T->>D: upsert snapshot (parameterised SQL)
        T-->>C: observation, freshness live, citation
    else live source failed
        T->>D: read latest snapshot
        alt snapshot exists
            D-->>T: cached row
            T-->>C: observation, freshness cached, citation
        else no snapshot
            T-->>C: status unavailable, reason
        end
    end
    C-->>A: validated tool result
```

---

## Figure 4.9: Provenance chain from source to report

<!-- fig: 4.9 provenance-chain -->

- **Caption:** Figure 4.9: Propagation of provenance from the official source to the final report.
- **Use in:** 4.8 Provenance and citation.
- **Description:** A fact keeps its source authority, dataset, table, period and retrieval time at every stage. The final report shows a provenance table and a SHA-256-derived hash per observation, so each number can be traced back.

```mermaid
flowchart TB
    S["Official source<br/>RBI DBIE table, MoSPI dataset"] --> T["MCP tool result<br/>value, unit, period, citation"]
    T --> H["Handler output<br/>SourceProvenance list"]
    H --> R["A2AResponse<br/>sources preserved unchanged"]
    R --> AG["aggregate()<br/>observations, citations, a2a_sources"]
    AG --> H2["Provenance hash<br/>SHA-256 of indicator, period, value, unit, status"]
    AG --> REP["Report sections<br/>indicator matrix and source provenance table"]
    H2 --> REP
    REP --> UI["Evidence drawer in UI"]
```

---

## Figure 4.10: Agent Card structure

<!-- fig: 4.10 agent-card -->

- **Caption:** Figure 4.10: Fields of an Agent Card used for discovery, routing and validation.
- **Use in:** 4.4 Agent discovery.
- **Description:** The card is both documentation and configuration. `supported_tasks` is kept in sync with the registered handlers, so the card always matches what is executable.

```mermaid
flowchart LR
    subgraph CARD["AgentCard"]
        I["agent_id, name, description, version"]
        C["capabilities: routing tags"]
        SK["skills: name, description, tags"]
        ST["supported_tasks: sector_analysis, repo_rate, ..."]
        SC["input_schema A2ARequest<br/>output_schema A2AResponse"]
        MD["metadata: sector, keywords"]
        AU["url and auth_requirements"]
    end
    REG["AgentRegistry"] --> CARD
    CARD --> RT["route_query scoring"]
    CARD --> SV["A2AServer capability check"]
    CARD --> UIR["A2A registry view and /a2a/registry"]
    HR["register_handler()"] -->|"appends task"| ST
```
