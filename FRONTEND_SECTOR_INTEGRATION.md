# Frontend Integration Guide: Four Sector Agents

This guide covers making `external_sector`, `labour_sector`,
`capital_market_sector`, and `monetary_sector` selectable and usable from the
frontend, following the existing `finance_sector` pattern. It also gives a
backend-first validation sequence so each sector can be checked on its own
before exercising the UI.

No application code is changed by this guide.

## Implementation protocol: one approved step at a time

Use this guide as a staged implementation checklist, not as permission to make
all the changes at once. The existing `finance_sector` implementation is the
reference; inspect the current repository at each stage rather than assuming
that this guide or a sector README overrides actual code.

### Initial inspection (Step 1 — inspect only)

Before changing code, compare Finance with the four requested sectors. Inspect
Finance's models, client, parsers, database, MCP server, agent, executor, API,
tests, and any Finance-specific frontend integrations actually used. Compare
the corresponding sector files and inspect:

- `frontend/src/data/agents.ts`
- `frontend/src/types/index.ts`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/ChatWorkspace.tsx`
- `frontend/src/components/DashboardView.tsx`
- `frontend/src/App.tsx`
- `frontend/vite.config.ts`
- `backend/main.py`

Record how Finance is cataloged, enabled, selected, routed, streamed, cited,
and how it represents freshness, unavailable data, and isolated chat history.
Then report the comparison in this format and stop without modifying files:

```text
FINANCE PATTERN
→ External difference
→ Labour difference
→ Capital difference
→ Monetary difference
```

Do not run tests or start servers during this inspection.

### Approved implementation stages

Proceed to a stage only after the user explicitly says to continue. Make only
that stage's changes, review them, report the result, and stop for approval
before starting another stage.

| Stage | Scope | Preserve |
|---|---|---|
| 2 — Agent catalog | Enable only `external_sector`, `labour_sector`, `capital_market_sector`, and `monetary_sector` in `frontend/src/data/agents.ts`, using verified metadata. | Existing Finance, Orchestrator, and unfinished-sector metadata. |
| 3 — Sidebar | Make only those four sectors selectable using the established Finance pattern. | Finance/Orchestrator selection and disabled agents. |
| 4 — ChatWorkspace | Show the selected sector's verified title, description, mode, icon/accent, placeholder, welcome, and prompts; retain per-agent histories. | Existing Finance behavior, shared component architecture, and visual design. |
| 5 — Backend direct dispatch | Add direct backend dispatch for the four sectors using actual node names/result keys found in the code. | Finance dispatch, Orchestrator dispatch, and existing APIs. |
| 6 — Streaming | Adapt the four direct routes to Finance's `step`, `token`, `done` contract and the frontend's completion shape. | Finance streaming and truthful handling of missing/unavailable values. |
| 7 — Citations and freshness | Display each sector's actual citation and freshness metadata in the established Finance pattern. | Provenance integrity; never invent a source, URL, date, authority, value, or freshness. |
| 8 — Vite/API | Add only the proxy routes that are actually required for browser calls to the mounted sector APIs. | Existing `/api` and Finance proxy behavior. |
| 9 — Dashboard (optional) | Extend the dashboard only if sector dashboard integration is needed and supported by its existing architecture. | Finance dashboard behavior; do not invent metrics or redesign it. |

Do not implement Agriculture, Fiscal, Services, or Prices. Do not delete,
rename, disable, or unnecessarily alter Finance code or behavior. Prefer
additive changes and do not replace the established Finance pattern with a new
generic architecture.

### Required report after each stage

After each approved coding stage, inspect the changed files and review imports,
Finance behavior, duplication, and accidental file deletions. Then report:

1. What was inspected.
2. What was changed and which files were modified.
3. Why the change follows Finance's pattern.
4. Any potential issue noticed.
5. The exact, minimal terminal commands the user should run for this stage.

Do not run the tests, builds, package installation, or servers yourself. Give
the commands only, explain briefly what they validate, and stop for the user's
next instruction. A documentation or inspection-only step has no test command
unless a relevant check is genuinely needed.

Use the repository's `uv` environment for Python commands. Use only commands
relevant to the current stage; do not provide a large all-stage command list.
The backend-first validation section below lists each sector's independent
test and API checks; select only the checks relevant to the approved stage.

For a frontend change, the build command is:

```powershell
cd frontend
npm run build
```

Only when the user asks to run the backend, the documented startup command is:

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

## Current integration status

The four sector packages and their FastAPI sub-applications exist. The gateway
in [backend/main.py](./backend/main.py) already mounts them at these paths:

| Sector ID sent as `agent` | Gateway API prefix | Current data routes |
|---|---|---|
| `external_sector` | `/external-sector` | `/health`, `/metadata`, `/forex-reserves`, `/trade-balance` |
| `labour_sector` | `/labour-sector` | `/health`, `/metadata`, `/unemployment`, `/lfpr` |
| `capital_market_sector` | `/capital-markets` | `/health`, `/metadata`, `/nifty-snapshot`, `/gsec-yields` |
| `monetary_sector` | `/monetary-sector` | `/health`, `/metadata`, `/policy-rates`, `/money-supply` |

The gateway's `/api/v1/chat/stream` and `/api/v1/chat` routes currently call a
sector agent directly only for `finance_sector`; every other `agent` value goes
to the orchestrator. The frontend currently enables only Orchestrator and
Finance in the sidebar and chat header. The agent catalog already contains the
four requested IDs, but their statuses are not active.

The APIs available above are not the full set of datasets used by some agent
nodes. In particular, the sector nodes fetch additional series that currently
have no corresponding HTTP route: External exchange rates, Labour WPR,
Capital Markets VIX, and Monetary system liquidity/stance. Add those data API
routes only if users or the frontend need to inspect those datasets directly.
Direct chat can call the underlying clients without exposing every dataset as
an HTTP endpoint.

## What to edit

### 1. Enable the four entries in the agent catalog

Edit [frontend/src/data/agents.ts](./frontend/src/data/agents.ts):

- Change the status for the four implemented sector entries to the status the
  UI uses for selectable/live agents (`active`).
- Keep their IDs exactly aligned with the API request's `agent` values and
  backend sector package names:
  `external_sector`, `labour_sector`, `capital_market_sector`,
  `monetary_sector`.
- Check each entry's authority, domain, owned indicators, and source labels
  against that sector's current implementation rather than marking a source
  live simply because it is listed in a design README.

`SectorId` in [frontend/src/types/index.ts](./frontend/src/types/index.ts)
already includes these four IDs; no union change should be needed. `App.tsx`
already stores and passes a generic selected agent ID, so it should not need a
sector-specific branch.

### 2. Make the Sidebar selection status-driven

Edit [frontend/src/components/Sidebar.tsx](./frontend/src/components/Sidebar.tsx):

- Replace the hardcoded `isOrchestrator || isFinance` selectable condition so
  the four enabled catalog entries can be clicked into chat.
- Replace the fixed “2 Active” count with a count derived from the catalog
  (decide whether this includes the orchestrator and use the same rule
  consistently).
- Replace Finance-only labels, badges, and active-dot styling with values
  derived from the selected agent's metadata/status.
- Keep genuinely unimplemented agents disabled; do not enable every staged
  catalog entry as a side effect.

### 3. Generalize ChatWorkspace beyond Finance

Edit [frontend/src/components/ChatWorkspace.tsx](./frontend/src/components/ChatWorkspace.tsx):

- Replace `isFinance` / `isCurrentFinance` checks with selection-aware agent
  metadata, so the heading, short name, mode label, domain/data description,
  colors, and prompt placeholder reflect the selected sector.
- Expand the quick-mode controls (currently only Orchestrator and Finance) so
  users can return to Orchestrator or switch among all five directly usable
  agents. Alternatively, remove the duplicate quick switcher if sidebar
  selection is intended to be the only control.
- Add a short welcome message and sector-specific suggested questions for
  each of the four sectors. Keep each sector's conversation history isolated;
  the existing `messagesByAgent` structure already supports this.
- Preserve the existing stream parser's event contract: `step`, `token`, and
  `done`. Ensure every new sector reaches a `done` event even when its data
  source is unavailable or an agent call fails.
- Normalize the completion payload so it consistently supplies `full_report`,
  `agent_routed`, `citations`, and (when applicable) `observations`,
  `mermaid_diagram`, and `confidence_score`.
- Don't display absent numeric data as a valid value. The sector node summaries
  currently interpolate missing values as text such as `None`; handle
  unavailable/missing observations explicitly before presenting a report.

The frontend citation type accepts several optional citation names, but the
sector Pydantic citations use `source_authority`, `table_reference`,
`retrieval_url`, `observation_period`, and `freshness`. Map those fields into
the frontend citation display shape when creating the `done.citations` array;
do not omit provenance or substitute a fabricated source.

### 4. Route sector-specific chat in the backend gateway

Edit [backend/main.py](./backend/main.py):

- Import the four async agent nodes:
  `external_agent_node`, `labour_agent_node`, `capital_agent_node`, and
  `monetary_agent_node`.
- Add explicit dispatch branches keyed by the exact sector IDs. The direct
  branch should invoke that sector node with the query and use that node's
  corresponding result keys:
  - External: `external_sector_analysis`, `external_sector_data`,
    `external_sector_freshness`
  - Labour: `labour_sector_analysis`, `labour_sector_data`,
    `labour_sector_freshness`
  - Capital markets: `capital_market_sector_analysis`,
    `capital_market_sector_data`, `capital_market_sector_freshness`
  - Monetary: `monetary_sector_analysis`, `monetary_sector_data`,
    `monetary_sector_freshness`
- For streaming chat, emit sector-appropriate progress steps, stream the
  report as tokens, and finish with the normalized `done` payload described
  above. Construct citations from actual returned record citation metadata;
  the nodes' summarized `data` and `freshness` dictionaries alone are not a
  substitute for per-observation source citations.
- Keep the default/explicit `orchestrator` path unchanged.
- Add the same direct-dispatch behavior to `/api/v1/chat` if it remains a
  supported non-streaming endpoint. Otherwise document that the UI uses only
  `/api/v1/chat/stream`.
- Update the request model's description to enumerate the supported direct
  sector IDs.

The independent data routes already exist under mounted prefixes. Verify that
the sector routes are mounted in the running gateway; avoid duplicating or
renaming the existing paths just to support chat.

### 5. Add Vite proxy paths for direct data requests

Edit [frontend/vite.config.ts](./frontend/vite.config.ts) if the frontend will
call sector data routes from the browser during development. Add proxy entries
for `/external-sector`, `/labour-sector`, `/capital-markets`, and
`/monetary-sector`, targeting the same backend as the existing `/api` proxy.

The chat request itself uses `/api/v1/chat/stream` and is already covered by
the existing `/api` proxy. If production uses a reverse proxy rather than Vite,
configure these four mounted prefixes there as well.

### 6. Decide whether sector metrics belong on the dashboard

The current [frontend/src/components/DashboardView.tsx](./frontend/src/components/DashboardView.tsx)
and `DashboardOverview` type in
[frontend/src/types/index.ts](./frontend/src/types/index.ts) are Finance-only.
This is not a prerequisite for sector chat. If “work on the frontend” includes
sector KPI cards, separately extend the dashboard API response, its TS types,
loading/error/empty states, and the dashboard components for these sectors.
Do not treat the existing Finance dashboard as proof that the new sector APIs
are connected.

## Sector data to verify

Use these expected output families when checking that the API and the agent
node agree. Every returned observation should have a period, a value (or an
explicit unavailable/null state), units where applicable, and a real
source citation.

| Sector | API checks | Agent/report checks |
|---|---|---|
| External | Forex reserves and trade balance; both return `status`, `total_records`, and `records`. | Forex reserve total, USD/INR, trade balance; the current node also fetches exchange rates. Verify units (USD millions vs USD billions) and source/period metadata. |
| Labour | Unemployment and LFPR; both return `status`, `total_records`, and `records`. | UR, LFPR, and WPR; the current node fetches all three. WPR is currently not exposed by the sector HTTP API. |
| Capital markets | NIFTY snapshot and G-Sec yields; both return `status`, `total_records`, and `records`. | NIFTY close, India VIX, and 10-year G-Sec yield; the current node fetches VIX although the API does not expose a VIX route. |
| Monetary | Policy rates and money supply; both return `status`, `total_records`, and `records`. | Repo/SDF/MSF and M3 growth/stance; the current node also fetches system liquidity and stance, neither of which has a sector HTTP route. |

Freshness values are `live`, `cached`, or `unavailable`. A successful HTTP
response is not by itself a successful live-data validation: inspect the
records, their periods, freshness, and citations. If a provider is unavailable,
verify the failure/cache behavior and show an unavailable state rather than
reporting a fabricated or stale value as live.

## Backend-first validation reference

```powershell
uv run pytest backend\external_sector\tests\test_external_sector.py
uv run pytest backend\labour_sector\tests\test_labour_sector.py
uv run pytest backend\capital_market_sector\tests\test_capital_market_sector.py
uv run pytest backend\monetary_sector\tests\test_monetary_sector.py
```

These existing suites check representative models/database behavior and the
sector health route; they do **not** comprehensively validate every live
provider call or every data endpoint. Treat them as a unit-test baseline, not
an end-to-end data-quality sign-off. Add/update focused tests with mocked
client results for each endpoint and each agent node, including:

1. A valid record round-trips with exact numeric fields, period, units, and
   citation.
2. Empty, stale-cache, source-error, and unavailable outcomes are represented
   honestly and do not become numeric-looking report values.
3. HTTP data endpoints return the documented response model and status codes.
4. The agent node returns its documented `*_analysis`, `*_data`,
   `*_freshness`, and `*_errors` keys on success and partial failure.
5. The direct chat dispatcher selects the requested node (and only that node),
   with a test that ensures non-Finance sector IDs do not fall through to the
   orchestrator.

When backend startup is explicitly requested, start the unified backend from
the repository root:

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

In another PowerShell terminal, smoke-test each mounted sector API directly:

```powershell
$base = 'http://127.0.0.1:8000'
Invoke-RestMethod "$base/external-sector/health"
Invoke-RestMethod "$base/external-sector/forex-reserves?lookback_weeks=4"
Invoke-RestMethod "$base/external-sector/trade-balance?lookback_months=6"

Invoke-RestMethod "$base/labour-sector/health"
Invoke-RestMethod "$base/labour-sector/unemployment"
Invoke-RestMethod "$base/labour-sector/lfpr"

Invoke-RestMethod "$base/capital-markets/health"
Invoke-RestMethod "$base/capital-markets/nifty-snapshot"
Invoke-RestMethod "$base/capital-markets/gsec-yields"

Invoke-RestMethod "$base/monetary-sector/health"
Invoke-RestMethod "$base/monetary-sector/policy-rates?lookback_months=6"
Invoke-RestMethod "$base/monetary-sector/money-supply?lookback_months=6"
```

For each response, inspect that the health result names the correct sector;
each data result has the expected response structure; `total_records` equals
the number of returned records; and every observation has valid provenance and
the correct units/period. If a request returns 503, check whether that is the
expected unavailable-source behavior or an integration failure. Do not accept
empty/unavailable output as proof that a frontend data card is working.

Before connecting the UI, add individual agent-node tests using mocked
responses so tests do not rely on public network availability. Check each
node's output fields and validate citation construction. These four existing
test modules currently do not cover all the API routes or the complete agent
node contract.

## Frontend verification checklist

After the backend tests and smoke checks pass:

1. Start the frontend and backend; verify Vite proxies the API paths required
   by the UI.
2. Confirm each of the four entries is selectable from the sidebar and the
   selected sector is reflected in the chat header and input hint.
3. Send one sector-specific question per agent and confirm the request body
   uses the matching `agent` ID.
4. Confirm progress steps, streamed text, completion, citations, period, and
   freshness are correct for that sector; switch between agents and verify
   histories do not mix.
5. Verify an out-of-domain or unavailable-data request is clearly handled,
   without fake figures, incorrect attribution, or an accidental orchestrator
   response.
6. Run the frontend production type/build check:

   ```powershell
   cd frontend
   npm run build
   ```

Only after each sector passes its own tests, API smoke check, direct agent
dispatch check, and frontend chat check should it be presented as ready for
users. Cross-sector orchestrator routing is a separate integration: making a
sector directly selectable does not automatically register it with the
orchestrator or prove that orchestrated queries can reach it.
