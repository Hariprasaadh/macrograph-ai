# Macrograph-AI: Multi-Agent Indian Macroeconomic Intelligence Platform

Macrograph-AI is a collaborative multi-agent system that decomposes India's macroeconomy into **10 specialized sector agents**. These agents communicate via the **A2A protocol** (agent-to-agent reasoning) and retrieve data via **FastMCP servers** (agent-to-data), collaborating to uncover causal transmission chains, synthesize cross-sector intelligence, and deliver **strictly cited** economic insights.

---

## Architecture Overview

```
                         ┌─────────────────────────────────────────────────────────────┐
                         │                        USER QUERY                           │
                         └──────────────────────┬──────────────────────────────────────┘
                                                 │
                         ┌───────────────────────▼──────────────────────────────────────┐
                         │                    ORCHESTRATOR                              │
                         │  • Parses query, inspects Agent Cards                       │
                         │  • Decomposes into sector subtasks                          │
                         │  • Coordinates A2A collaboration                            │
                         │  • Synthesizes final cited report                           │
                         └────────────────────┬─────────────────────────────────────────┘
                                              │ A2A Protocol (agent ↔ agent collaboration)
              ┌───────────┬──────────┬────────┴──────┬───────────┬───────────┐
              ▼           ▼          ▼               ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ PRICES   │ │MONETARY  │ │ FISCAL   │ │EXTERNAL  │ │CAPITAL   │ │ FINANCE  │
        │  AGENT   │ │  AGENT   │ │  AGENT   │ │  AGENT   │ │ MARKET   │ │  AGENT   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │            │              │             │             │
        ┌────┴─────┐       │      ┌─────┴──────┐      │        ┌───┴──────────────┘
        │  AGRI    │       │      │  LABOUR    │       │        │ NSE/BSE MCP
        │  AGENT   │       │      │  AGENT     │       │
        └────┬─────┘       │      └────┬───────┘       │
             │             │           │                │
             └─────────────┴───────────┴────────────────┘
                                    │
                       MCP Servers (agent ↔ data)
             ┌──────────┬───────────┬──────────┬───────────┐
             ▼          ▼           ▼          ▼           ▼
          MOSPI       RBI DBIE   Agmarknet   IMD (IMD)   Qdrant
          API/DB      & Bulletins  & DAC&FW   Rainfall    (RAG)
```

---

## Layer 1: Communication Protocol — A2A (Agent ↔ Agent)

**A2A is strictly the reasoning and collaboration layer. No data is ever fetched through A2A.**

Agents use A2A to:
- **Request Analysis** — Ask a peer to evaluate a specific economic variable.
- **Delegate Subtasks** — Transfer a domain-specific analytical burden to the expert agent.
- **Share Findings** — Pass structured conclusions, indicator values, or causal chains to peers.
- **Challenge & Validate** — Dispute another agent's conclusion and demand supporting evidence.
- **Establish Causality** — Chain findings into cross-sector transmission logic (e.g., *"Agriculture confirms supply shock → Prices confirms food CPI spike → Monetary confirms policy unchanged"*).

> **Strict Rule:** If the Prices Agent computes the inflation rate, the Monetary Agent must **not** recompute it. It must accept the figure via A2A and analyze the policy response only. This enforces **single-source-of-truth** across agents.

---

## Layer 2: Data Protocol — FastMCP (Agent ↔ Data)

**MCP is strictly the data retrieval layer. Agents never fetch data from each other — only from FastMCP servers.**

```
Agent A  ←─── A2A ───→  Agent B
   │                         │
 FastMCP               FastMCP
   ↓                         ↓
RBI DBIE                 MOSPI DB
```

All MCP servers in this project are implemented using **[FastMCP](https://github.com/jlowin/fastmcp)** (`fastmcp` package). FastMCP provides a decorator-based API for defining tools, automatic schema generation from type annotations, and seamless mounting into the FastAPI gateway.

Every sector package exposes its own `FastMCP` instance in `<sector>/mcp_server.py`:

```python
# Example: prices_sector/mcp_server.py
from fastmcp import FastMCP

mcp_server = FastMCP("Prices & Inflation MCP Server")

@mcp_server.tool()
async def get_cpi_data(series_id: str, months: int = 12) -> CPIData:
    """Fetch CPI data from MOSPI for the given series and lookback period."""
    ...
```

All sector `FastMCP` instances are then registered on the central FastAPI gateway in `backend/main.py`. Agents call these tools via MCP — **never** by directly importing from another sector package.

---

## Layer 3: Agent Cards & Discovery

Every sector agent publishes an **Agent Card** that the Orchestrator reads to route tasks and assemble coalitions.

| Field | Description |
| :--- | :--- |
| **Identity & Domain** | Agent name, sector, and analytical scope |
| **Capabilities** | The specific questions the agent can answer |
| **Input/Output Schema** | Pydantic-validated A2A request/response formats |
| **MCP Data Sources** | Which MCP tools and endpoints the agent connects to |
| **Collaboration Partners** | Which other agents it typically coordinates with |

---

## The Orchestrator

The Orchestrator is the **central routing and synthesis engine**. It performs **no domain analysis itself** — its only job is coordination and citation-verified synthesis.

| Step | Responsibility |
| :--- | :--- |
| **1. Parse & Inspect** | Understand user query; read Agent Cards to identify relevant sector agents |
| **2. Decompose & Delegate** | Split query into atomic subtasks and route them to the correct agents |
| **3. Coordinate A2A** | Monitor and facilitate cross-agent communication; pass relevant findings between agents |
| **4. Resolve Conflicts** | If agents provide contradictory findings, mediate using cited evidence |
| **5. Synthesize & Cite** | Aggregate all agent reports into a final response. **Every claim must cite the Agent, MCP tool, and exact data point** |

---

## Interaction Modes

### Orchestrator Mode (Complex Multi-Sector Queries)
Used when the query spans multiple economic domains.

**Example:** *"How will a repo rate hike impact industrial credit growth and headline inflation?"*
→ Routes to: **Monetary → Financial → Industry → Prices**

### Direct Agent Mode (Domain-Specific Queries)
Used when the query is bounded to a single domain. Bypasses the Orchestrator.

**Example:** *"What is the current RBI liquidity surplus?"*
→ Routes directly to: **Monetary Agent**

---

## The 10 Sector Agents

| # | Agent | Module | Domain | Primary MCP Sources |
| :- | :--- | :--- | :--- | :--- |
| # | Agent | Module | Domain | Primary MCP Sources |
| :- | :--- | :--- | :--- | :--- |
| 1 | **Real Sector** | `real_sector/` | GDP, GVA, National Accounts | MoSPI e-Sankhyiki FastMCP (`https://mcp.mospi.gov.in/` - NAS, IIP) |
| 2 | **Agriculture** | `agriculture_sector/` | Crop production, MSP, Monsoon, Mandi prices | Agmarknet, DAC&FW, IMD |
| 3 | **Prices & Inflation** | `prices_sector/` | CPI, WPI, Core/Food/Fuel inflation | MoSPI e-Sankhyiki FastMCP (`https://mcp.mospi.gov.in/` - CPI, WPI) |
| 4 | **Monetary & Liquidity** | `monetary_sector/` | Repo rate, SDF, M1/M2/M3, RBI policy stance | RBI DBIE & Monthly Bulletins |
| 5 | **Finance & Banking** | `finance_sector/` | Bank credit growth, Sectoral deployment, Asset quality (GNPA/NNPA), Lending rates (WALR/MCLR), Deposits & CD ratio | RBI DBIE Tables (`r539`, `r330`, `r531`, `r689`) & FSR |
| 6 | **Capital Markets** | `capital_market_sector/` | NIFTY, SENSEX, India VIX, USD/INR, Corporate earnings, MF flows | Yahoo Finance MCP / NSE/BSE live feeds (`yfinance`) |
| 7 | **Fiscal & Public Finance** | `fiscal_sector/` | Fiscal deficit, GST, Capex, Government debt | CGA, CBDT, CBIC |
| 8 | **External Sector** | `external_sector/` | Trade balance, Forex reserves, BoP, Remittances | RBI BoP, DGCI&S |
| 9 | **Labour & Employment** | `labour_sector/` | Unemployment, LFPR, EPFO, Wages | MoSPI PLFS FastMCP, EPFO, ILO |
| 10 | **Services** | `services_sector/` | IT/ITeS, PMI Services, Services GVA | MoSPI e-Sankhyiki FastMCP, PMI surveys |

### Sector Ownership & Boundary Rules

To prevent duplicated logic and conflicting sources of truth across agents:

| Data Point | Owner Agent | Consumers via A2A |
| :--- | :--- | :--- |
| Food CPI, WPI, Core inflation | **Prices** | Monetary, Agriculture, Fiscal, Finance |
| Repo rate, Policy stance, CRR/SLR, M1/M3, LAF liquidity | **Monetary** | Finance, Capital Markets, Fiscal, External |
| SCB credit growth, Sectoral deployment, GNPA/NNPA, WALR/MCLR | **Finance** | Monetary, Capital Markets, Real Sector, Fiscal |
| NIFTY/SENSEX, Volatility (VIX), IPOs, Corporate earnings | **Capital Markets** | External, Monetary, Finance |
| Wheat/paddy production, Mandi prices, Monsoon departure | **Agriculture** | Prices, External, Real Sector |
| Fiscal deficit, GST revenue, Central Capex, Sovereign borrowing | **Fiscal** | Monetary, External, Finance |
| FII/FPI flows, Secondary market portfolio investment | **Capital Markets** | External, Monetary |
| PLFS unemployment, LFPR, Formal payroll (EPFO) | **Labour** | Real Sector, Fiscal, Finance |
| Forex reserves, BoP, Merchandise trade, USD/INR, ECBs | **External** | Monetary, Capital Markets, Fiscal |
| Services GVA, Services PMI, IT/ITeS export volume | **Services** | Real Sector, External, Labour |

---

### Sector-Specific Documentation

To maintain clean modularity, deep domain specifications, exact database table keys, indicator schemas, and tool contracts are documented in each sector's package directory:

- **Finance & Banking:** [backend/finance_sector/README.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/finance_sector/README.md)
- **Prices & Inflation:** [backend/prices_sector/README.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/prices_sector/README.md)
- **Capital Markets:** [backend/capital_market_sector/README.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/capital_market_sector/README.md)
- **Real Sector:** [backend/real_sector/README.md](file:///c:/Users/Dell/Documents/GitHub/macrograph-ai/backend/real_sector/README.md)

---

## Knowledge Layer — RAG (Qdrant Vector DB)

Economic analysis requires qualitative context beyond raw data. Agents query **Qdrant** via MCP when they need to ground quantitative findings in official policy language.

**Indexed Documents include:**
- Union Budget speeches & fiscal statements
- RBI MPC minutes & Governor press conferences
- Economic Survey (Annual)
- PLFS & NSSO survey reports
- RBI Annual Reports

---

## Causal Reasoning Example — A2A + MCP in Action

**User Query:** *"Why is food inflation rising, and how is the RBI responding?"*

```
Step 1: Orchestrator → Prices Agent (A2A task: "Analyze current food inflation drivers")
Step 2: Prices Agent → MOSPI MCP (data: Food CPI = +4.8% YoY)
Step 3: Prices Agent → Agriculture Agent (A2A: "Food CPI up 4.8%. Analyze supply-side constraints")
Step 4: Agriculture Agent → IMD MCP (data: Monsoon deficit 18% in key states)
         Agriculture Agent → Agmarknet MCP (data: Tomato +120%, Onion +60% MoM)
         Agriculture Agent → Prices Agent (A2A reply: "Supply shock confirmed — Kharif sowing down 8%")
Step 5: Prices Agent → Monetary Agent (A2A: "Food-led headline CPI elevated. What is policy stance?")
Step 6: Monetary Agent → RBI DBIE MCP (data: Repo rate 6.5%, stance "withdrawal of accommodation")
         Monetary Agent → Qdrant RAG (data: Governor statement: "Food volatility is transitory")
         Monetary Agent → Prices Agent (A2A reply: "Repo unchanged. RBI attributes spike to transitory supply shocks")
Step 7: Orchestrator synthesizes all findings → Final cited report
```

**Final Output (Strictly Cited):**
> Food inflation has risen to **4.8% YoY** [*Prices Agent* via *MOSPI MCP*], driven by a supply-side shock: a monsoon deficit of **18%** in key agricultural states caused Kharif sowing to fall by **8%**, triggering severe shortages in vegetables — tomatoes rose **+120%** and onions **+60%** month-on-month [*Agriculture Agent* via *IMD & Agmarknet MCP*].
>
> The RBI has maintained its **"withdrawal of accommodation"** stance with the repo rate unchanged at **6.5%**, characterizing food price volatility as transitory [*Monetary Agent* via *RBI DBIE MCP* and *Qdrant (Governor's press conference)*].

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Orchestration** | LangGraph (stateful multi-agent graph) |
| **Agent Framework** | A2A SDK (`a2a-sdk`) |
| **MCP Servers** | FastMCP (`fastmcp`) — decorator-based tool server, one per sector, mounted on the FastAPI gateway |
| **API Gateway** | FastAPI + Uvicorn |
| **Data Validation** | Pydantic v2 |
| **LLM Provider** | Groq (FAST: `llama-3.1-8b-instant`, REASONING: `llama-3.3-70b-versatile`) |
| **Knowledge Graph** | NetworkX (in-memory), Neo4j (persistent) |
| **Vector DB (RAG)** | Qdrant |
| **Analytical DB** | DuckDB |
| **Data Libraries** | Pandas, NumPy, Statsmodels, Scikit-learn, SciPy |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS |

---

## Core System Rules (Non-Negotiable)

1. **No Source, No Answer:** Do not generate any financial metric, percentage, rate, or trend without explicitly stating its source. No agent or the Orchestrator may output an economic claim without citing the **exact Agent**, the **MCP tool used**, the **official publication / table**, and the **specific data point or document**.
2. **Zero Hallucination & No Hardcoding:** Never hallucinate, estimate, or hardcode random/mock values as factual data. If an agent lacks a data point or a fetch fails, it must explicitly return a structured unavailable state. Inventing numbers or providing unverified guesses is strictly prohibited.
3. **Single Source of Truth:** Each economic indicator has exactly one owner agent. Peer agents must accept that agent's finding via A2A — they must never recompute or reinterpret another agent's primary domain data.
4. **A2A is for Reasoning, MCP is for Data:** These layers must never be conflated. Data flows up through MCP; intelligence and causal conclusions flow sideways through A2A.
5. **No Silent Failures:** If a data fetch fails, an MCP tool is unavailable, or an A2A peer is unresponsive, the agent must surface a structured error with the missing context rather than proceeding with incomplete or stale data.