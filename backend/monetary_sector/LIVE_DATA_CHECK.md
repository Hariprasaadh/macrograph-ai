# Monetary Sector — Live Data Check Runbook

How to prove, from a terminal, that the monetary sector pulls **live MCP data**
instead of serving DuckDB cache. Monetary sector only.

All commands are PowerShell. **Every check below is one self-contained block:
paste the whole block, it sets up its own environment and runs.** No shared
setup step, no variables to define first. (The C: drive on this machine is
full, so each block redirects `uvx`/`npx`/temp to D: — without that, every MCP
spawn fails and all fetchers silently fall back to cache.)

## 1. Eco-Policy MCP — live RBI policy rates (standard SDK stdio)

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:UV_CACHE_DIR = "D:\uv-cache"; $env:TEMP = "D:\Temp"; $env:TMP = "D:\Temp"; $env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "import asyncio; from monetary_sector.client import _call_eco_policy_tool; p = asyncio.run(_call_eco_policy_tool()); print(p['data']); print(p['provenance'])"
```
```

Expected: `policy_repo_rate: 5.25`, `stance: Neutral`,
`rates_effective_from: 2026-08-05`, provenance with `as_of` + `reference`.

## 2. DBIE CDN — official RBIH tables over plain HTTP (finance pattern)

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "import asyncio, httpx; print(asyncio.run(httpx.AsyncClient(timeout=30.0, follow_redirects=True).get('https://dbie.rbihub.in/data/money-stock-measures.json')).json().keys())"
```

Expected: `dict_keys(['reportTitle', 'units', 'columns', 'data'])`. No `uvx`/`npx`
involved — plain HTTPS like the finance sector, so a full C: drive cannot
break it. (The old `npx dbie-mcp` stdio bridge was removed for exactly this
reason.)

## 3. Tavily direct API — real-time MPC news (finance pattern, no subprocess)

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "import asyncio; from monetary_sector import client; print([(i['title'][:70], i['url'][:70]) for i in asyncio.run(client.fetch_mpc_news_via_tavily_mcp('RBI repo rate MPC meeting'))][:3])"
```

Expected: 3 current MPC news results (repo 5.25%, neutral stance). Plain HTTPS
like the finance sector — no `npx`, so disk/process state cannot break it.

## 4. Sector fetchers — freshness proof

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:UV_CACHE_DIR = "D:\uv-cache"; $env:npm_config_cache = "D:\npm-cache"; $env:TEMP = "D:\Temp"; $env:TMP = "D:\Temp"; $env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "
import asyncio
from monetary_sector import client
async def main():
    rates = await client.fetch_policy_rates(lookback_months=1)
    print('RATES:', rates[0].period, rates[0].repo_rate_pct, rates[0].citation.freshness.value, '|', rates[0].citation.table_reference)
    ms = await client.fetch_money_supply(lookback_months=1)
    print('M3:', ms[0].period, ms[0].m3_cr, ms[0].citation.freshness.value, '|', ms[0].citation.table_reference)
    liq = await client.fetch_system_liquidity(lookback_months=1)
    print('LIQ:', liq[0].period, liq[0].citation.freshness.value, '|', liq[0].citation.table_reference)
    news = await client.fetch_mpc_news_via_tavily_mcp('RBI MPC repo rate decision')
    print('NEWS:', len(news))
asyncio.run(main())
"
```

Expected: `RATES: ... live | eco-policy:rbi_get_policy_rates`,
`M3/LIQ: ... upstream_snapshot | /banking/...`, `NEWS: 5`.
`live` = Eco-Policy MCP, `upstream_snapshot` = DBIE MCP, `cached` = DuckDB
fallback (means the MCP spawn above it failed — see troubleshooting).

## 5. Explicit live-data agent run

Any of `live`, `real-time`, `fresh`, `up to date` in the query forces the
cache to be bypassed — MCP failure raises instead of serving cached rows:

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:UV_CACHE_DIR = "D:\uv-cache"; $env:npm_config_cache = "D:\npm-cache"; $env:TEMP = "D:\Temp"; $env:TMP = "D:\Temp"; $env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "
import asyncio
from monetary_sector.agent import monetary_agent_node
out = asyncio.run(monetary_agent_node({'query': 'Fetch LIVE data: current repo rate, corridor width and MPC stance with latest news'}))
print('WORDS:', len(out['monetary_sector_analysis'].split()))
print('ERRORS:', out['monetary_sector_errors'])
print('FORCE_LIVE:', out['monetary_sector_force_live'])
print('FRESHNESS:', out['monetary_sector_freshness'])
print('NEWS:', len(out['monetary_sector_news']))
"
```

Expected: `ERRORS: []`, `FORCE_LIVE: True`,
`FRESHNESS: {'policy_rates': 'live', 'monetary_stance': 'live'}`,
`NEWS: 5`, 600+ word analysis.

## 6. Fetch audit log — what served what, over time

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "
from monetary_sector import database as db
with db.get_connection() as con:
    for row in con.execute('SELECT tool_name, status, rows_written, logged_at FROM fetch_log ORDER BY id DESC LIMIT 12').fetchall():
        print(row)
"
```

`status` is `live` (Eco-Policy), `upstream_snapshot` (DBIE), or
`cache_fallback` (MCP failed). Repeated `cache_fallback` rows mean the
transport is broken — go back to checks 1–3.

## 7. Gateway end-to-end (optional, two terminals)

Terminal 1 — start the API:

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:UV_CACHE_DIR = "D:\uv-cache"; $env:npm_config_cache = "D:\npm-cache"; $env:TEMP = "D:\Temp"; $env:TMP = "D:\Temp"
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -m uvicorn main:app --port 8011
```

Terminal 2 — stream one monetary answer and inspect the final event:

```powershell
$body = @{ message = 'Fetch LIVE data: current repo rate and MPC stance'; agent = 'monetary_sector' } | ConvertTo-Json
(Invoke-WebRequest -Uri 'http://127.0.0.1:8011/api/v1/chat/stream' -Method Post -ContentType 'application/json' -Body $body -UseBasicParsing -TimeoutSec 300).Content -split "`n" | Where-Object { $_ -match '"type": "done"' }
```

Expected: `"status"` completed/partial, `"freshness"` with `live` entries,
`"errors": []`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Everything returns `cached` | D: redirect lines missing (C: full breaks `uvx`/`npx`), or first-run package download timed out — rerun; cold downloads can take minutes once, then reuse the D: cache |
| `& $py ...` errors / `$py` empty | Old pattern — this file no longer uses `$py`; each block above carries the full python path, paste the whole block |
| `uvx` says package not found / hangs | No network to PyPI, or D: cache dirs missing — recreate `D:\uv-cache`, `D:\npm-cache`, `D:\Temp` |
| Tavily returns auth error | `TVLY_KEY_1` missing from `backend/.env` and the fallback dev key revoked — set a valid key; code uses env first |
| Finstack tools return old numbers | Known: finstack serves stale snapshots (repo 6.25 labelled Feb 2025, indicative Q1-2025 yields). Deliberately **not** wired into monetary records. Finstack also needs `uvx --with mcp<2 finstack-mcp` (plain `uvx finstack-mcp` crashes on an `mcp` 2.x incompatibility) |
| `MonetaryDataUnavailableError` on a forced-live query | Correct behavior: live MCP sources failed and the request refused to serve cache. Check 1–3 to find which source is down |

## MCP source map (monetary sector)
| Data | Primary | Fallback | Citation table_reference |
|---|---|---|---|
| Policy rates + stance | Eco-Policy `rbi_get_policy_rates` (LIVE) | DBIE `/banking/select-economic-indicators`, then cache | `eco-policy:rbi_get_policy_rates` |
| Money supply (M1/M2/M3) | DBIE CDN `money-stock-measures.json` (HTTP) | cache | `/banking/money-stock-measures` |
| System liquidity | DBIE CDN `liquidity-operations.json` (HTTP) | cache | `/banking/liquidity-operations` |
| MPC news | Tavily direct search API (gated: stance/recency queries) | omitted (never breaks answers) | item `url` + `source: Tavily AI Search` |

## 8. Clear cache — prove live-or-unavailable (no stale safety net)

Deletes cached rows (the `fetch_log` audit is preserved). Afterwards, working
MCP servers repopulate live; dead ones raise instead of serving stale rows —
exactly what a fresh system with no cache exhibits.

Via the sector API (backend running):

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/monetary-sector/cache' -Method Delete
```

Expected: `{"status":"cache_cleared","cleared_tables":{...},"total_rows_deleted":N,...}`.

Via chat (any client): send `clear the cache` to the monetary agent. It
replies with per-table deleted counts and fetches nothing else.

Then prove unavailability reporting with MCP servers blocked (or to simulate,
stop network access) and an explicit live request:

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "
import asyncio
from monetary_sector import client
try:
    await client.fetch_money_supply(lookback_months=1, force_live=True)
    print('served: MCP is reachable')
except Exception as exc:
    print('UNAVAILABLE AS DESIGNED:', type(exc).__name__, str(exc)[:160])
"
```

Expected when MCP is down: `UNAVAILABLE AS DESIGNED: MonetaryDataUnavailableError:
get_money_supply unavailable: live MCP sources failed and the DuckDB cache is
bypassed ...`. Without `force_live`, the same situation reports the cached
rows it has, or the same error when the cache is empty.

## 9. Prompt routing (MCP registry) — which functions a query retrieves

`backend/monetary_sector/mcp_registry.py` is the single registry mapping
prompts to necessary functions. Verify routing without any network:

```powershell
cd "D:\PROJECT-1 CLG\macrograph-ai\backend"
$env:PYTHONIOENCODING = 'utf-8'
& "D:\PROJECT-1 CLG\macrograph-ai\.venv\Scripts\python.exe" -c "
from monetary_sector import mcp_registry as r
print('repo query ->', sorted(r.match_services('What is the repo rate?')))
print('stance query ->', sorted(r.match_services('Explain the MPC stance')))
print('expanded ->', sorted(r.expand_dependencies({'monetary_stance'})))
print('news?', r.wants_news('Latest MPC news please', {'policy_rates'}))
print('force?', r.wants_force_live('Fetch LIVE data now'))
print('clear?', r.wants_cache_clear('clear the cache'))
print('servers:', {k: (v['wired'], v['role'][:40]) for k, v in r.UPSTREAM_MCP_SERVERS.items()})
"
```

Expected: `{'policy_rates'}`, `{'monetary_stance'}`,
`{'monetary_stance', 'policy_rates'}` (stance auto-adds its dependency, so it
is derived from one rates pull instead of fetched twice), `True/True/True`,
and the four upstream servers with wiring verdicts. The agent logs the chosen
route per query (`monetary services selected=... via=...`).
