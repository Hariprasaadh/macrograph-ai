# A2A AgentCard — Full Annotated Schema & Template

**Served at:** `GET /.well-known/agent.json`  
**Used for:** Agent discovery, capability negotiation, authentication setup  
**Required by:** Every A2A-compliant server agent

---

## Minimal AgentCard (No Auth, No Streaming)

```json
{
  "name": "Prices & Inflation Agent",
  "description": "Analyses CPI, WPI, and inflation components for India using MOSPI data.",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "cpi-analysis",
      "name": "CPI Inflation Analysis",
      "description": "Analyses headline and component CPI inflation data from MOSPI.",
      "tags": ["inflation", "cpi", "wpi", "mospi", "india"],
      "examples": [
        "What is the current headline CPI?",
        "Decompose food vs core inflation.",
        "Compare WPI and CPI trends for last 6 months."
      ]
    }
  ]
}
```

---

## Full AgentCard (Auth + Streaming + Multiple Skills)

```json
{
  "name": "Monetary & Liquidity Agent",
  "description": "Analyses RBI monetary policy, repo rate, liquidity conditions, and money supply metrics.",
  "url": "http://localhost:8003",
  "version": "1.0.0",
  "documentationUrl": "http://localhost:8003/docs",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text", "data"],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "repo-rate-analysis",
      "name": "Repo Rate & Policy Stance",
      "description": "Fetches and analyses the current RBI repo rate, SDF, and MSF bands. Reads MPC meeting statements from Qdrant.",
      "tags": ["monetary-policy", "repo-rate", "rbi", "mpc"],
      "inputModes": ["text"],
      "outputModes": ["text", "data"],
      "examples": [
        "What is the current repo rate?",
        "What stance did the RBI adopt in the last MPC meeting?",
        "Is RBI in an accommodative or restrictive cycle?"
      ]
    },
    {
      "id": "liquidity-analysis",
      "name": "System Liquidity & Money Supply",
      "description": "Analyses daily system liquidity (LAF), CRR, SLR, and M1/M2/M3 money supply trends.",
      "tags": ["liquidity", "laf", "money-supply", "m3"],
      "inputModes": ["text"],
      "outputModes": ["text", "data"],
      "examples": [
        "What is the current system liquidity surplus?",
        "Show M3 money supply growth trend.",
        "What is the current CRR and SLR?"
      ]
    }
  ],
  "authentication": {
    "schemes": ["Bearer"]
  }
}
```

---

## AgentCard Field Reference

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | Yes | Human-readable agent name |
| `description` | string | Yes | What the agent does — used by Orchestrator for routing |
| `url` | string | Yes | Base URL where the A2A server is reachable |
| `version` | string | Yes | Semantic version of the agent |
| `documentationUrl` | string | No | Link to agent-specific documentation |
| `defaultInputModes` | string[] | Yes | Accepted input types (`"text"`, `"data"`, `"file"`) |
| `defaultOutputModes` | string[] | Yes | Produced output types (`"text"`, `"data"`, `"file"`) |
| `capabilities.streaming` | bool | Yes | Whether agent supports SSE streaming via `message/stream` |
| `capabilities.pushNotifications` | bool | Yes | Whether agent supports webhook push delivery |
| `skills` | AgentSkill[] | Yes | One or more declared capability units |
| `authentication` | object | No | Auth requirements. Omit for internal/unauthenticated agents |
| `authentication.schemes` | string[] | No | Supported auth schemes: `"Bearer"`, `"ApiKey"`, `"None"` |

### AgentSkill Fields

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | string | Yes | Unique skill identifier used for routing |
| `name` | string | Yes | Human-readable skill name |
| `description` | string | Yes | What this skill analyses/produces |
| `tags` | string[] | No | Searchable tags for discovery |
| `inputModes` | string[] | No | Override input modes for this skill |
| `outputModes` | string[] | No | Override output modes for this skill |
| `examples` | string[] | No | Example queries this skill can answer |

---

## Macrograph-AI Sector AgentCard Templates

### prices_sector AgentCard
```json
{
  "name": "Prices & Inflation Agent",
  "description": "Owns and analyses all inflation indicators: CPI (headline, food, core, fuel, housing), WPI, and inflation expectations. Primary data from MOSPI and RBI DBIE.",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text", "data"],
  "capabilities": { "streaming": true, "pushNotifications": false },
  "skills": [
    {
      "id": "cpi-decomposition",
      "name": "CPI Decomposition",
      "description": "Decomposes CPI into food, fuel, core, and housing components with trend analysis.",
      "tags": ["cpi", "inflation", "mospi", "food-inflation"],
      "examples": ["What is the current CPI?", "Decompose headline CPI.", "Is food inflation rising?"]
    },
    {
      "id": "wpi-analysis",
      "name": "WPI Analysis",
      "description": "Analyses Wholesale Price Index across primary articles, fuel, and manufactured products.",
      "tags": ["wpi", "wholesale-prices", "producer-prices"],
      "examples": ["What is the latest WPI?", "How does WPI compare to CPI?"]
    }
  ]
}
```

### monetary_sector AgentCard
```json
{
  "name": "Monetary & Liquidity Agent",
  "description": "Owns RBI monetary policy, repo rate, SDF, MSF, CRR, SLR, liquidity, and M1/M2/M3 money supply. Also reads RBI MPC minutes from Qdrant.",
  "url": "http://localhost:8003",
  "version": "1.0.0",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text", "data"],
  "capabilities": { "streaming": true, "pushNotifications": false },
  "skills": [
    {
      "id": "rbi-policy-analysis",
      "name": "RBI Policy & Stance",
      "description": "Analyses current RBI policy stance, repo rate, and MPC decisions.",
      "tags": ["rbi", "monetary-policy", "repo-rate", "mpc"],
      "examples": ["What is the current repo rate?", "What is the RBI's current stance?"]
    },
    {
      "id": "liquidity-money-supply",
      "name": "Liquidity & Money Supply",
      "description": "Analyses system liquidity, CRR, SLR, and M1/M2/M3 trends.",
      "tags": ["liquidity", "money-supply", "laf", "m3"],
      "examples": ["What is system liquidity today?", "Show M3 growth."]
    }
  ]
}
```
