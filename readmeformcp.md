Skip to content
cyanheads
imf-mcp-server
Repository navigation
Code
Issues
1
 (1)
Pull requests
Agents
Actions
Projects
Security and quality
Insights
cyanheads
imf-mcp-server
Public
Go to file
t
T
cyanheads
cyanheads
docs(changelog): state what callers see from #57 and narrow the recov…
73fadb4
 · 
last week
Name		
.claude-plugin
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
.codex-plugin
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
.github
chore: sync docs and packaging metadata from mcp-ts-core scaffold
3 weeks ago
.vscode
chore: scaffold from @cyanheads/mcp-ts-core
4 months ago
changelog
docs(changelog): state what callers see from #57 and narrow the recov…
last week
docs
docs(design): note the canvas-off prefix in the query workflow's plac…
last week
framework-skills
chore: sync scripts, skills, and agent protocol from mcp-ts-core 0.13.10
last week
scripts
build(docker): install production dependencies in a cross-platform de…
last week
src
docs(imf_query_dataset): name the status-less null value in the paddi…
last week
tests
feat(imf_query_dataset): key validation, last_n_observations, canvas-…
last week
.dockerignore
chore: scaffold from @cyanheads/mcp-ts-core
4 months ago
.env.example
fix: adopt mcp-ts-core 0.13 canvas_id validation and error metadata
3 weeks ago
.gitattributes
chore(deps): adopt @cyanheads/mcp-ts-core 0.10.14 — supply-chain guar…
3 months ago
.gitignore
chore: sync devcheck/packaging scripts and skills to mcp-ts-core 0.11.1
2 months ago
.mcpbignore
chore: sync scripts, skills, and agent protocol from mcp-ts-core 0.13.10
last week
AGENTS.md
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
CHANGELOG.md
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
CITATION.cff
docs: add CITATION.cff
3 months ago
CLAUDE.md
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
Dockerfile
build(docker): install production dependencies in a cross-platform de…
last week
LICENSE
chore(deps): adopt @cyanheads/mcp-ts-core 0.10.14 — supply-chain guar…
3 months ago
README.md
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
biome.json
chore: scaffold from @cyanheads/mcp-ts-core
4 months ago
bun.lock
chore(deps): @cyanheads/mcp-ts-core ^0.13.6 → ^0.13.10, dev-dep refresh
last week
bunfig.toml
chore(deps): adopt @cyanheads/mcp-ts-core 0.10.14 — supply-chain guar…
3 months ago
devcheck.config.json
chore(deps): @cyanheads/mcp-ts-core ^0.13.6 → ^0.13.10, dev-dep refresh
last week
manifest.json
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
package.json
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
server.json
chore(release): 0.4.3 — key validation, latest-N queries, bounded can…
last week
tsconfig.build.json
chore: sync tooling and skills with mcp-ts-core 0.12.3
2 months ago
tsconfig.json
chore: sync tooling and skills with mcp-ts-core 0.12.3
2 months ago
vitest.config.ts
fix: validate the resource payload and drop the ctx casts
2 months ago
Repository files navigation
README
Code of conduct
Contributing
Apache-2.0 license
Security
@cyanheads/imf-mcp-server
Query IMF SDMX 3.0 macroeconomic data — hundreds of dataflows across 190 countries, WEO projections, BOP, CPI, exchange rates, and national accounts via MCP. STDIO or Streamable HTTP.

6 Tools • 1 Resource
Version License Docker MCP SDK npm TypeScript Bun

Install in Claude Desktop Install in Cursor Install in VS Code

Framework

Public Hosted Server: https://imf.caseyjhand.com/mcp

Overview
IMF SDMX 3.0 macroeconomic data — hundreds of dataflows spanning WEO projections, balance of payments, CPI, exchange rates, and national accounts across 190 countries. Browse the dataflow catalog, resolve dimension codes, and query time series from any MCP client, with large multi-country results staged to DataCanvas for SQL analysis. Runs as a stdio process, a local Streamable HTTP server, or the public hosted endpoint above.

Tools
Tool	Description
imf_list_databases	List IMF SDMX dataflows available on the portal, a page at a time, with an optional filter matching every word across ID, name, and description
imf_get_database	Fetch a dataflow's dimensions and page either its codelists or the codes with published data — resolves human terms to SDMX codes before querying
imf_query_dataset	Query a dataflow by dimension key over a time range; large result sets spill to DataCanvas when it is enabled, or return a bounded prefix with retrieval guidance
imf_dataframe_describe	List DataCanvas tables and columns staged by a prior imf_query_dataset call
imf_dataframe_query	Run a read-only SQL SELECT across staged DataCanvas tables for multi-country comparisons and aggregations
imf_dataframe_drop	Remove one staged table or view without affecting other tables on the canvas; disabled by default
Resources
Resource	Description
imf://database/{dataflow_id}	Bounded discovery metadata for one IMF SDMX dataflow — dimensions, codelist previews, key_format, and continuation guidance
Continuation beyond the resource's bounded codelist preview runs through imf_get_database.

Capability reference
imf_list_databases tool
filter splits on spaces and commas and keeps a dataflow when every word appears, case-insensitively, in its ID, name, or description ("WEO outlook" finds WEO and the regional outlooks built on it), matched against the full text — not the shortened preview this tool returns
Vintage (historical snapshot) dataflows such as WEO_2025_OCT_VINTAGE are excluded by default; set include_vintages=true to include them
Paged: limit (default 50, max 200) and offset; total_count reports total matches, returned_count the page size, and a notice names the next offset while matches remain
Descriptions are cut to 200 characters here — imf_get_database and the imf://database/{dataflow_id} resource return the full text
imf_get_database tool
Resolves human-readable terms to SDMX dimension codes (e.g. "United States" → USA) and returns each dimension's DSD concept-scheme label
Country codes are ISO 3-letter (USA, GBR, DEU), not ISO 2-letter (US, GB, DE)
key_format names the exact dot-separated dimension order imf_query_dataset requires
Codelist previews are capped at 50 entries by default; set dimension_id to page one dimension with limit/offset (max 200), and codelist_filter applies before paging
codelist_filter keeps codes whose ID or name contains every word given, in any order — "GDP constant prices" finds NGDP_RPCH and its constant-price siblings in WEO
Set available_only=true to page codes the dataflow actually publishes, with series count and time coverage, instead of the full codelist
A codelist_filter that matches nothing is reported distinctly from a codelist that could not be resolved — the two need opposite next steps
imf_query_dataset tool
Dot-separated key in DSD keyPosition order; + combines codes at one position, * matches every code there — every position needs a code or *, a blank segment is rejected
Codes are trimmed and matched case-insensitively (usa.ngdp_rpch.a queries USA.NGDP_RPCH.A), as is dataflow_id; a code missing from its dimension's codelist fails before the query as invalid_key_code, naming the nearest valid codes (US → USA), and a * inside a + list fails as wildcard_in_code_list
start_period/end_period accept YYYY, YYYY-SN, YYYY-QN, YYYY-MM, or a calendar-valid YYYY-MM-DD; each bound covers its whole period (end_period: 2023 includes 2023-M12)
last_n_observations (1–10,000) keeps each series' last N observations — 1 returns every series' latest value without downloading its history. "Latest" is per series, and a WEO series ends in projection years (2031); with a period bound, the last N inside the range
Returns time_period, value, status, and series attributes (unit, scale, decimals); a key resolving to multiple series carries one series_metadata entry per series, since attributes can differ between them
unit/scale are upstream codes (PT, USD, XDC, IX, NUM); a null unit means the dataflow publishes none. value is already in base units, and scale is the power of ten the IMF publishes the series in — "9" renders published in units of 10^9, "0" renders published in units
A response is held to 100,000 serialized characters. With DataCanvas, larger multi-country or long-range results spill to it (output_mode: "canvas" forces staging); staged reports storage, truncated reports only whether observations is an incomplete preview — a staged result can still be untruncated
Without DataCanvas, a larger result returns its earliest observations with truncated: true, full series_metadata, and retrieval_guidance naming the last time_period returned and how to narrow: a narrower key, start_period/end_period, last_n_observations, or CANVAS_PROVIDER_TYPE=duckdb. A key whose series_metadata alone overflows fails as response_too_large
no_data errors carry availability context naming codes that do have coverage; a key with data entirely outside the requested range fails as no_data_in_range and reports the range that does
imf_dataframe_describe tool
Lists every table staged on a canvas, with row count and column schema (name + DuckDB type)
Requires canvas_id from a prior imf_query_dataset call that returned staged: true
Call before imf_dataframe_query to confirm table and column names
Listed only with CANVAS_PROVIDER_TYPE=duckdb, like the other dataframe tools; without it the landing page shows it disabled with that hint
imf_dataframe_query tool
One read-only SQL SELECT per call; a leading WITH … SELECT common table expression is accepted, DML and DDL are rejected
Results are capped first by the canvas row limit (default 10,000), then by a 100,000-character serialized response budget — row_count always equals the returned rows, and truncated: true means either cap trimmed the result
Page past a cap with a stable ORDER BY plus LIMIT/OFFSET; response_too_large means even one row didn't fit and asks for fewer columns or aggregation
Listed only with CANVAS_PROVIDER_TYPE=duckdb
imf_dataframe_drop tool
Removes one named table or view from a canvas without affecting the others; requires the exact name from imf_dataframe_describe
Idempotent — a repeated or absent drop returns dropped: false rather than an error
Disabled by default; set IMF_ENABLE_DATAFRAME_DROP=true alongside CANVAS_PROVIDER_TYPE=duckdb to register it in tools/list
imf://database/{dataflow_id} resource
Bounded discovery metadata for one dataflow — every dimension with up to 50 codelist entries, counts, key_format, name, description
dataflow_id comes from imf_list_databases
Carries continuation metadata pointing to imf_get_database (with dimension_id/limit/offset) for a codelist beyond the preview
Features
Built on @cyanheads/mcp-ts-core: stdio and Streamable HTTP transports, pluggable auth (none / jwt / oauth), swappable storage (in-memory, filesystem, Supabase, Cloudflare KV/R2/D1), structured logging with optional OpenTelemetry tracing.

IMF-specific:

Keyless access — no API key required; the IMF SDMX 3.0 portal is fully public
Type-safe SDMX 3.0 compact JSON client with dimension/codelist parsing and DSD validation
Key dimension count validated against the DSD before each query to catch format mismatches early
Dataflow catalog and full availability constraints cached in-session to minimize round trips on multi-step workflows
DuckDB-backed DataCanvas spill for large multi-country or long time-range observations
Agent-friendly output:

Codelist entries carry both the machine code and human-readable label — agents can present meaningful names without a follow-up lookup
key_format field in every dataflow response explicitly states the dimension order, removing guesswork for key construction
Observations include each dataflow's own status flags (e.g. T, C, NA) so agents can communicate data quality caveats; a missing value flagged only as not available is dropped as padding
Canvas placement is explicit — staged distinguishes storage from truncated preview completeness, and staged results carry canvas_id, table_name, and retrieval guidance
Getting started
Public Hosted Instance
A public instance is available at https://imf.caseyjhand.com/mcp — no installation required. Point any MCP client at it via Streamable HTTP:

{
  "mcpServers": {
    "imf-mcp-server": {
      "type": "streamable-http",
      "url": "https://imf.caseyjhand.com/mcp"
    }
  }
}
Self-Hosted / Local
No API key required. Add the following to your MCP client configuration file.

{
  "mcpServers": {
    "imf-mcp-server": {
      "type": "stdio",
      "command": "bunx",
      "args": ["@cyanheads/imf-mcp-server@latest"],
      "env": {
        "MCP_TRANSPORT_TYPE": "stdio",
        "MCP_LOG_LEVEL": "info"
      }
    }
  }
}
Or with npx (no Bun required):

{
  "mcpServers": {
    "imf-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@cyanheads/imf-mcp-server@latest"],
      "env": {
        "MCP_TRANSPORT_TYPE": "stdio",
        "MCP_LOG_LEVEL": "info"
      }
    }
  }
}
Or with Docker:

{
  "mcpServers": {
    "imf-mcp-server": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MCP_TRANSPORT_TYPE=stdio",
        "ghcr.io/cyanheads/imf-mcp-server:latest"
      ]
    }
  }
}
To enable SQL analytics over large result sets, add CANVAS_PROVIDER_TYPE=duckdb to the env block. Add IMF_ENABLE_DATAFRAME_DROP=true only when agents should be able to remove staged tables.

For Streamable HTTP, set the transport and start the server:

MCP_TRANSPORT_TYPE=http MCP_HTTP_PORT=3010 bun run start:http
# Server listens at http://localhost:3010/mcp
Prerequisites
Bun v1.4.0 or higher (or Node.js v24+).
No API key required.
Installation
Clone the repository:
git clone https://github.com/cyanheads/imf-mcp-server.git
Navigate into the directory:
cd imf-mcp-server
Install dependencies:
bun install
Configure environment:
cp .env.example .env
# edit .env as needed — no required vars for basic use
Configuration
Variable	Description	Default
CANVAS_PROVIDER_TYPE	Set to duckdb to enable DataCanvas spill for large result sets and register the dataframe tools. Unset, an over-budget query returns its earliest observations with truncated: true.	—
IMF_ENABLE_DATAFRAME_DROP	Advertise and enable destructive table-level DataCanvas cleanup.	false
IMF_BASE_URL	IMF SDMX 3.0 base URL. Override for testing or proxied environments.	https://api.imf.org/external/sdmx/3.0
IMF_REQUEST_TIMEOUT_MS	Per-request timeout in milliseconds.	30000
MCP_TRANSPORT_TYPE	Transport: stdio or http.	stdio
MCP_HTTP_PORT	Port for HTTP server.	3010
MCP_SESSION_MODE	HTTP session handling: stateful, stateless, or auto (the schema default, which resolves to stateful). This server declares stateless in src/index.ts, so a deployment that sets nothing still gets it; setting this to a meaningful value overrides the declaration.	stateless
MCP_AUTH_MODE	Auth mode: none, jwt, or oauth.	none
MCP_LOG_LEVEL	Log level (RFC 5424).	info
OTEL_ENABLED	Enable OpenTelemetry instrumentation.	false
See .env.example for the full list of optional overrides.

Running the server
Local development
Build and run:

bun run rebuild

bun run start:stdio
# or
bun run start:http
Run checks and tests:

bun run devcheck   # Lint, format, typecheck, security
bun run test       # Vitest test suite
bun run lint:mcp   # Validate MCP definitions against spec
Docker
docker build -t imf-mcp-server .
docker run --rm -p 3010:3010 imf-mcp-server
The Dockerfile defaults to HTTP transport, stateless session mode, and logs to /var/log/imf-mcp-server. OpenTelemetry peer dependencies are installed by default — build with --build-arg OTEL_ENABLED=false to omit them.

Project structure
Directory	Purpose
src/index.ts	createApp() entry point — registers tools/resources and inits services.
src/config/server-config.ts	Server-specific env var parsing and validation with Zod.
src/mcp-server/tools/definitions/	Tool definitions (*.tool.ts).
src/mcp-server/resources/definitions/	Resource definitions (*.resource.ts).
src/services/canvas/	DataCanvas accessor — wraps the framework canvas instance.
src/services/imf-sdmx/	IMF SDMX 3.0 API client — dataflow catalog, DSD fetching, data queries.
tests/	Unit and integration tests mirroring src/.
docs/	Design notes and directory tree.
Development guide
See CLAUDE.md/AGENTS.md for development guidelines and architectural rules. The short version:

Handlers throw, framework catches — no try/catch in tool logic
Use ctx.log for request-scoped logging, ctx.state for tenant-scoped storage
Register new tools and resources via the barrels in src/mcp-server/*/definitions/index.ts
Wrap external API calls: validate raw → normalize to domain type → return output schema; never fabricate missing fields
Data source
Data is sourced from the International Monetary Fund SDMX 3.0 portal under the IMF Copyright and Terms of Use. The IMF's terms permit redistribution of statistical data with attribution. Each data-returning tool response includes a source field with the required attribution: Source: International Monetary Fund, <dataflow name>, https://data.imf.org/.

Contributing
Issues are welcome. Run checks and tests before submitting:

bun run devcheck
bun run test
License
Apache-2.0 — see LICENSE for details.

About
Query IMF SDMX 3.0 macroeconomic data — hundreds of dataflows across 190 countries, WEO projections, BOP, CPI, exchange rates, and national accounts via MCP. STDIO or Streamable HTTP.

www.npmjs.com/package/@cyanheads/imf-mcp-server
Topics
Resources
Readme
Apache-2.0 license
Code of conduct
Code of conduct
Contributing
Contributing
Security policy
Security policy

Cite this repository
Activity
Stars
1 star
Watchers
0 watching
Forks
1 fork
Report repository
Releases
23
 (23)
v0.4.3: Key validation, latest-N queries, bounded canvas-off output
Latest
last week
+ 22 releases
Packages
1
 (1)
imf-mcp-server
Contributors
1
 (1)
@cyanheads
cyanheadsCasey Hand
Languages
TypeScript
99.2%
Dockerfile
0.8%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
nso-india
esankhyiki-mcp
Repository navigation
Code
Issues
6
 (6)
Pull requests
7
 (7)
Agents
Actions
Projects
Security and quality
Insights
nso-india
esankhyiki-mcp
Public
Go to file
t
T
drmhaske13
drmhaske13
Merge pull request #70 from nso-india/feat/add-nss74
0f06887
 · 
yesterday
Name		
.github/workflows
chore(ai-review): deterministic consistency tests + scoped LLM review (…
5 months ago
definitions
add NSS74 dataset
2 days ago
mospi
add NSS74 dataset
2 days ago
observability
refactor: clean up telemetry middleware (#20)
7 months ago
scripts
Fix health check failures for NSS77 and NAS.
3 months ago
swagger
add NSS74 dataset
2 days ago
tests
add NSS74 dataset
2 days ago
.env.example
v2.0.0: 19 datasets, indicator definitions, stateless HTTP (#13)
7 months ago
.gitignore
v2.0.0: 19 datasets, indicator definitions, stateless HTTP (#13)
7 months ago
CHANGELOG.md
add NSS74 dataset
2 days ago
CONTRIBUTING.md
add NSS74 dataset
2 days ago
Dockerfile
fix: use json_response=True to fix ChatGPT Accept header rejection
7 months ago
LICENSE
Public tech, public code.
8 months ago
README.md
add NSS74 dataset
2 days ago
docker-compose.yml
Sunlight is the best disinfectant.
8 months ago
mospi_server.py
add NSS74 dataset
2 days ago
pyproject.toml
v2.0.0: 19 datasets, indicator definitions, stateless HTTP (#13)
7 months ago
requirements.txt
fix(security): harden server and dependencies per security review (#39)
5 months ago
Repository files navigation
README
Contributing
MIT license
MoSPI MCP Server
License: MIT Python 3.11+ FastMCP MCP Server Tests

MCP (Model Context Protocol) server for accessing India's Ministry of Statistics and Programme Implementation (MoSPI) data APIs. Built with FastMCP 3.3.

Table of Contents
Overview
Datasets
MCP Tools
Quick Start
Installation
Running the Server
Connecting from an MCP Client
Deployment
Docker
Docker Compose
FastMCP Cloud
Architecture
Configuration
Contributing
Resources
License
About DIID
Acknowledgments
Overview
This server provides AI-ready access to official Indian government statistics through the Model Context Protocol (MCP). It acts as a bridge between AI assistants (Claude, ChatGPT, Cursor, etc.) and MoSPI's open data APIs, enabling natural language queries for economic, demographic, and social indicators.

Key Features:

Following statistical datasets covering employment, unemployment, inflation, industrial and services production, GDP and national accounts, energy and renewable energy, higher and school education, gender, health and nutrition, disability, housing and sanitation, household consumption and expenditure, time use, agriculture and livestock, land holdings, debt and investment, AYUSH, environment and climate, banking and financial statistics, economic census, unincorporated enterprises, telecom and digital connectivity.
Sequential 4-tool workflow designed for LLM consumption
Swagger-driven parameter validation
Full OpenTelemetry integration for observability
Production-ready Docker deployment
Note: Some NSS rounds include sub-parts (NSS77A, NSS79C, NSS76C, NSS80E), which are shown as separate entries in the README for user understanding. On the server, however, these sub-parts are accessible through their respective parent NSS round dataset (NSS77, NSS79, NSS76, NSS80) itself, rather than as independent datasets.
Dataset Reference
Sr. No.	Dataset	Full Name	Use For
1	PLFS	Periodic Labour Force Survey	Employment, unemployment, labour force participation, worker population ratio, wages, employment by industry and occupation
2	CPI	Consumer Price Index	Retail inflation, cost of living, inflation by commodity group, state-wise and rural/urban price indices
3	IIP	Index of Industrial Production	Industrial growth, manufacturing output, mining, electricity generation, sector-wise production indices
4	ASI	Annual Survey of Industries	Factory performance, industrial employment, wages, fixed capital, output, value added, productivity
5	NAS	National Accounts Statistics	GDP, GVA, national income, sector-wise economic growth, savings, capital formation
6	WPI	Wholesale Price Index	Wholesale inflation, producer prices, commodity price indices, inflation trends
7	ENERGY	Energy Statistics	Energy production, consumption, installed capacity, fuel mix, energy intensity, renewable energy statistics
8	AISHE	All India Survey on Higher Education	Universities, colleges, enrolment, teachers, Gross Enrolment Ratio (GER), Gender Parity Index (GPI), higher education infrastructure
9	ASUSE	Annual Survey of Unincorporated Sector Enterprises	Unincorporated enterprises, MSMEs, employment, output, value added, informal sector statistics
10	GENDER	Gender Statistics	Gender indicators, women empowerment, sex ratio, labour participation, education, health, crimes against women
11	NFHS	National Family Health Survey	Fertility, family planning, maternal and child health, nutrition, infant mortality, health indicators
12	ENVSTATS	Environment Statistics	Climate, biodiversity, forests, air and water quality, environmental resources, pollution indicators
13	RBI	RBI Statistics	Banking, money supply, foreign exchange reserves, exchange rates, balance of payments, external sector, financial indicators
14	NSS77	NSS 77th Round – Land and Livestock Holdings	Agricultural households, land holdings, livestock ownership, crop insurance, farming assets
15	NSS77A	All India Debt and Investment Survey (AIDIS) – NSS 77th Round	Household assets, liabilities, debt, investment, borrowing patterns, wealth distribution
16	NSS78	NSS 78th Round – Multiple Indicator Survey	Drinking water, sanitation, housing amenities, migration, digital connectivity, household living conditions
17	CPIALRL	Consumer Price Index for Agricultural and Rural Labourers	Rural inflation, agricultural labourer cost of living, rural wage index, inflation trends
18	HCES	Household Consumption Expenditure Survey	Household consumption, expenditure patterns, poverty estimation, inequality, consumer behaviour
19	TUS	Time Use Survey	Time allocation, unpaid care work, paid work, household activities, gender time-use patterns
20	EC	Economic Census	Establishments, enterprises, employment, ownership, economic activity, district-wise business statistics
21	NSS79	NSS 79th Round – Survey on AYUSH	AYUSH awareness, AYUSH utilisation, treatment preferences, expenditure on AYUSH services
22	NSS79C	Comprehensive Annual Modular Survey (CAMS) – NSS 79th Round	Education, health expenditure, financial inclusion, digital literacy, household living conditions
23	UDISE	UDISE+ (Unified District Information System for Education Plus)	Schools, enrolment, dropout, teachers, PTR, GER, NER, GPI, CWSN, ICT facilities, school infrastructure
24	MNRE	Renewable Energy Statistics (Ministry of New and Renewable Energy)	Installed renewable energy capacity, solar, wind, hydro, bioenergy, state-wise renewable energy generation
25	NSS76	NSS 76th Round – Drinking Water, Sanitation, Hygiene and Housing Conditions	Drinking water sources, water treatment, sanitation, housing characteristics, toilets, flood experience
26	NSS76C	Persons with Disabilities in India – NSS 76th Round	Disability prevalence, education, employment, accessibility, assistive devices, care arrangements
27	NSS75E	NSS 75th Round – Social Consumption on Education	Literacy, educational attainment, school attendance, education expenditure, internet and computer access, GER/NAR
28	NSS80	NSS 80th Round – Comprehensive Modular Survey: Telecom (CMST)	Mobile phone ownership, internet usage, telecom access, digital services, online banking, cyber security awareness
29	NSS80E	NSS 80th Round – Comprehensive Modular Survey: Education (CMSE)	School enrolment, education expenditure, tuition fees, private coaching, scholarships, sources of education funding
30	NSS73	NSS 73rd Round – Unincorporated Non-Agricultural Enterprises	Enterprise type, enterprise ownership, hired workers, annual emoluments, GVA per worker, employment type, working hours, activity category, sector-wise and state-wise enterprise statistics
31	NSS74	NSS 74th Round – Services Sector Enterprises	Service sector enterprises, registration status, establishments by activity, ICT use, workers per establishment, value per establishment, structural ratios
32	ISP	Index of Service Production	Services sector growth, monthly services output, sub-sector indices
MCP Tools
The server exposes 4 tools that follow a sequential workflow:

list_datasets  ΓåÆ  get_indicators  ΓåÆ  get_metadata  ΓåÆ  get_data
Step	Tool	Description
1	list_datasets()	Overview of all datasets. Start here to find the right dataset.
2	get_indicators(dataset)	List available indicators for the chosen dataset.
3	get_metadata(dataset, ...)	Get valid filter values (states, years, categories) and API parameters.
4	get_data(dataset, filters)	Fetch data using filter key-value pairs from metadata.
Important: Tools must be called in order. Skipping get_metadata will result in invalid filter codes.

Quick Start
If you want to connect your AI agent of choice with the MCP server, you can directly connect it with MOSPI's MCP server. Video Guides to connect ChatGPT or Claude to MCP are available here -

 Guide.to.Connect.MCP.with.ChatGPT.mp4 
 Guide.to.Connect.MCP.with.Claude.mp4 
To get more information, visit - https://www.datainnovation.mospi.gov.in/mospi-mcp

The instructions below are for self-hosting the MCP server.

Installation
# Clone the repository
git clone https://github.com/nso-india/esankhyiki-mcp.git
cd esankhyiki-mcp

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
Running the Server
# HTTP transport (remote access)
python mospi_server.py

# OR using FastMCP CLI
fastmcp run mospi_server.py:mcp --transport http --port 8000

# stdio transport (local MCP clients)
fastmcp run mospi_server.py:mcp
Server runs at http://localhost:8000/mcp

Connecting from CLI Tools
Server URL: https://mcp.mospi.gov.in/

Claude Code
claude mcp add esankhyiki-mcp --transport http https://mcp.mospi.gov.in/
Verify with claude mcp list.

Cursor / Windsurf
Add to .cursor/mcp.json or .windsurf/mcp.json:

{
  "mcpServers": {
    "esankhyiki-mcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.mospi.gov.in/"]
    }
  }
}
Antigravity
Add to your Antigravity MCP settings:

{
  "mcpServers": {
    "mospi_api": {
      "serverUrl": "https://mcp.mospi.gov.in/"
    }
  }
}
Verify Connection
curl -s -X POST https://mcp.mospi.gov.in/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
A successful response returns serverInfo with "name": "MoSPI Data Server".

Local Server
If running locally:

claude mcp add esankhyiki-mcp --transport http http://localhost:8000/mcp
Or with the FastMCP Python client:

import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        overview = await client.call_tool("list_datasets", {})
        print(overview)

asyncio.run(main())
Deployment
Docker
# Build the image
docker build -t mospi-mcp .

# Run the container
docker run -d -p 8000:8000 --name mospi-server mospi-mcp
Docker Compose
Includes Jaeger for distributed tracing visualization:

docker-compose up -d
Services:

MoSPI Server: http://localhost:8000/mcp
Jaeger UI: http://localhost:16686
FastMCP Cloud
Push code to GitHub
Sign in to FastMCP Cloud
Create project with entrypoint mospi_server.py:mcp
Architecture
mospi-mcp-api/
Γö£ΓöÇΓöÇ mospi_server.py          # FastMCP server - tools, validation, routing
Γö£ΓöÇΓöÇ mospi/
Γöé   ΓööΓöÇΓöÇ client.py            # MoSPI API client - HTTP requests to api.mospi.gov.in
Γö£ΓöÇΓöÇ swagger/                 # Swagger YAML specs per dataset (source of truth for params)
Γöé   ΓööΓöÇΓöÇ swagger_user_*.yaml
Γö£ΓöÇΓöÇ observability/
Γöé   ΓööΓöÇΓöÇ telemetry.py         # OpenTelemetry middleware for tracing
Γö£ΓöÇΓöÇ tests/                   # Pytest suite (covering all datasets)
Γö£ΓöÇΓöÇ Dockerfile               # Production container with OTEL instrumentation
Γö£ΓöÇΓöÇ docker-compose.yml       # Full stack with Jaeger
ΓööΓöÇΓöÇ requirements.txt
Design Principles
Principle	Implementation
Swagger as Source of Truth	API parameters validated against YAML specs in swagger/, not hardcoded
Auto-routing	CPI routes to Group/Item endpoint based on filters; IIP routes to Annual/Monthly
Validation First	All filters validated before API calls with clear error messages
LLM-Optimized	Tool docstrings document parameters, return values, and workflow sequence
Testing
pip install -r tests/requirements-test.txt
pytest tests/ -v -p no:anyio
Runs in-process against the MCP server (no running server needed). Covers all datasets across all 4 tools. See CONTRIBUTING.md for details.

Configuration
Environment variables for OpenTelemetry:

Variable	Description	Default
OTEL_SERVICE_NAME	Service name in traces	mospi-mcp-server
OTEL_EXPORTER_OTLP_ENDPOINT	OTLP collector endpoint	http://localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL	Protocol (grpc or http/protobuf)	grpc
OTEL_TRACES_EXPORTER	Exporter type (otlp, console, none)	otlp
See .env.example for full configuration options.

Contributing
We welcome contributions! Please see CONTRIBUTING.md for guidelines on:

Adding new datasets
Project structure
Development setup
Code style
Resources
MoSPI Open APIs - Official API documentation and e-Sankhyiki portal
FastMCP Documentation - MCP framework docs
Model Context Protocol - MCP specification
License
This project is licensed under the MIT License - see the LICENSE file for details.

DIID
The Data Innovation Lab aims to promote innovation and the use of Information Technology in official statistics, including modernizing survey methods. It seeks to address the current challenges faced by the National Statistical System (NSS). The lab will serve as a platform for testing and developing new ideas through proof-of-concept projects. It will foster collaboration with a wide range of participants such as entrepreneurs, researchers, start-ups, academic institutions, and renowned national and international organizations. By creating an open and dynamic environment, the lab will support the advancement of statistical systems and help improve the quality and efficiency of data collection and analysis.

Know more: https://www.datainnovation.mospi.gov.in/home

Acknowledgments
Made in partnership with Bharat Digital in pursuit of modernising and humanising how governments use technology in service of the public.

About
This repository consists of Source Code for Model Context Protocol (MCP) Pilot Project being undertaken by Ministry of Statistics and Programme Implementation and source code for the same is being shared under MIT License.

Resources
Readme
MIT license
Contributing
Contributing
Activity
Stars
145 stars
Watchers
5 watching
Forks
28 forks
Report repository
Releases
4
 (4)
v2.2.0
Latest
6 months ago
+ 3 releases
Packages
1
 (1)
esankhyiki-mcp
Contributors
9
 (9)
@SatvikBajpai
@AnshuML
@drmhaske13
@mayankthekumawat
@harshnisar
@cursoragent
@abhinavsingha
@Saswatsusmoy
@nso-india
Languages
Python
99.4%
Dockerfile
0.6%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
Reserve-Bank-Innovation-Hub
dbie.rbihub.in
Repository navigation
Code
Issues
Pull requests
Agents
Actions
Projects
Security and quality
Insights
Reserve-Bank-Innovation-Hub
dbie.rbihub.in
Public
Go to file
t
T
Geetika-Shukla
Geetika-Shukla
Merge pull request #41 from Reserve-Bank-Innovation-Hub/one-lakh-story
cc489dd
 · 
yesterday
Name		
.github/workflows
Data API service, its deployment, and the site served from releases
3 weeks ago
data
Merge pull request #40 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
dbie-backend/data-api
Data API: build the image with Go 1.25
3 weeks ago
docs
What ₹1 lakh could buy: the story renamed, every chapter pinned, the …
yesterday
infra/terraform
CloudFront: cache policy of our own for the data API
3 weeks ago
mcp
mcp README: workspace install, clone registration, serve-your-own-data
3 months ago
public
Merge pull request #40 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
scripts
db:check reads a report row's cells whole, line breaks and all
2 weeks ago
src
Merge pull request #41 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
.env.common.example
Scrape DBIE over plain HTTP; Postgres as the system of record
3 weeks ago
.env.development
Add enni analytics: collector, hit endpoint, /enni dashboard
3 months ago
.gitignore
What ₹1 lakh bought: a new story on one sum carried from 2001 to 2026
yesterday
.seriseirc
Charts: fictoan colour tokens, one hue table and layered schemes
2 weeks ago
CLAUDE.md
Scrape of 28-09-2026: daily to monthly datasets and reports
2 weeks ago
LICENSE
Flatten to a single-manifest repo; MIT license; open-source README (#4)
4 months ago
README.md
Document the architecture and add agent context
3 weeks ago
amplify.yml
Data API service, its deployment, and the site served from releases
3 weeks ago
next.config.js
Data API service, its deployment, and the site served from releases
3 weeks ago
package.json
The women who stayed: a new agriculture story, at /stories/the-women-…
yesterday
pnpm-lock.yaml
The women who stayed: a new agriculture story, at /stories/the-women-…
yesterday
pnpm-workspace.yaml
Fold mcp into the pnpm workspace; harden the publish workflow
3 months ago
tsconfig.json
Upgrade to Next 16, React 19 and fictoan-react 2.0.0-beta.19 (#19)
3 months ago
Repository files navigation
README
MIT license
dbie.rbihub.in
A modern, fully static web platform for exploring economic data from the Reserve Bank of India's Database on Indian Economy (DBIE)—plus the scraping and processing pipeline that keeps its data fresh. 335 tables and series across prices, growth, markets, banking, external sector, government finance and payments, each with a searchable page, AG Grid table and (where it fits) a Plotly chart—and an MCP server so AI assistants can use the data too.

Built by the Reserve Bank Innovation Hub. MIT licensed. Start with docs/architecture.md for how it all fits together.

Quickstart
pnpm install

# get the site's data (the current release, built from the database's source files)
pnpm data:pull

pnpm dev            # run the site at localhost:3000
pnpm build          # static production build (SSG)
Scraping DBIE yourself
pnpm data:fetch       # restore the latest scrape's raw files from the S3 archive into data/ (no credentials needed)
pnpm scrape           # scrape all 252 SDMX series from DBIE over plain HTTP (~10 min; resumable)
pnpm data:ingest      # file the scraped CSVs into data/sdmx/ under readable names
pnpm scrape:report    # review what changed against the previous scrape's CSVs
pnpm scrape:catalogue # refresh the Statistics + Publications table catalogue (data/reports-catalogue.json)
pnpm scrape:reports   # export report tables (Statistics + Publications menus) to data/reports/ via the BusinessObjects REST layer
pnpm scrape:codelists # fetch the SDMX dimension code → label lists (data/sdmx-codelists/)
pnpm db:load          # load everything into the project's Postgres, the system of record (docs/database.md)
pnpm data:archive     # archive the scrape's raw files to S3 under their date
pnpm data:release     # build + verify the site bundle and publish it as a release
See docs/scraper.md for filters (single sector/series), resume behaviour, and how the gateway is driven without a browser, and docs/dbie-portal-anatomy.md for how the DBIE portal works under the hood.

How it works
DBIE ──scrape──▶ data/ (raw files; not in git) ──pnpm db:load──▶ Postgres (system of record)
                   │                                                  ▲ MCP server, analysts
                   ├──pnpm data:archive──▶ s3://dbie-common-scrapes/scrapes/<date>/
                   └──pnpm data:release──▶ processors → verified JSON → s3://dbie-common-site-data/releases/<version>/
                                                                              │ pnpm data:pull (Amplify build)
                                                                              ▼
                                                              next build → every page pre-rendered (SSG)
The database is the system of record for everything scraped (1,033 tables plus a catalogue and code lists); git holds code and small metadata only, and every scrape's raw files are archived to S3 under their date.
The data API (dbie-backend/data-api) serves every table, its rows and CSV, the catalogue and the code lists from the database, read-only (docs/data-api.md).
Pages are pre-rendered at build time from a data release in public/data/: no API, no database in the request path.
All interactivity (Plotly charts, AG Grid, search) is client-side.
The processors are self-checking (hard-coded known cells) and their outputs are verified byte-exact against committed oracles before a release is published.
Repository layout
Path	What
src/, public/, next.config.js	The Next.js app (TypeScript)
scripts/	DBIE scraper + ingest tooling (plain HTTP; gateway client and cipher in scripts/lib/; browser probes in scripts/recon/)
data/sdmx/, data/reports/	Scraped SDMX series (CSV) and report exports (CSV + xlsx); not in git: pnpm data:fetch restores them from the S3 archive
data/sources/, data/publications/	Manually downloaded report files (the DBIE Reports path needs a rationed guest SAP session; see docs)
data/processors/	Source files → the JSON the site renders (pnpm data:build, verified by pnpm data:verify)
data/catalogue.json, data/sdmx-tree.json, data/scrape-manifest.json	Table index + scrape state
data/sdmx-codelists/	DBIE code lists (dimension code → label) per SDMX dataset
infra/terraform/	The database, bastion, buckets and release role in the common-projects account (docs/database.md)
data/coverage-report.md	What the scrape covers vs the DBIE Reports catalogue
mcp/	@reserve-bank-innovation-hub/dbie-mcp — MCP server over the site's data
scripts/db/	Loaders for the project's Postgres database (schemas, SDMX and report tables, catalogue, checks; docs/database.md)
dbie-backend/data-api/	Read-only Go API over the database: every table, rows, CSV, catalogue, code lists (docs/data-api.md)
docs/	architecture.md (the map), database.md, data-api.md, scraper.md, dbie-portal-anatomy.md
Data refresh
pnpm scrape and pnpm scrape:reports — refresh the raw files in data/ (SDMX over plain HTTP; the report tables through the BusinessObjects REST layer); pnpm scrape:report reviews what changed.
pnpm db:load — load into Postgres; every table is verified against its file.
pnpm data:archive — archive the raw files to S3 under the scrape date.
pnpm data:release — run the processors, verify against the oracles, publish the site bundle as a release; then rebuild the site (Amplify picks up the current release with pnpm data:pull).
Commit the code and metadata changes (catalogues, code lists, oracles); the raw files stay out of git.
The release-data workflow does step 4 from an archived scrape, on demand or when the processors change on main; every site branch's build downloads the current release.

AI access (MCP)
AI assistants can search and fetch every table via the bundled MCP server — see mcp/README.md:

claude mcp add dbie -- npx -y @reserve-bank-innovation-hub/dbie-mcp
Contributing
Issues and PRs welcome. The pipeline is deliberately boring: plain Node scripts, no framework, one workspace (pnpm install covers the app and the MCP package). If you add a dataset, add its processor under data/processors/ and verify its output against a known-good snapshot (see data/processors/README.md for the parity gotchas when porting spreadsheet parsers).

License
MIT

About
No description, website, or topics provided.
Resources
Readme
MIT license
Activity
Custom properties
Stars
0 stars
Watchers
1 watching
Forks
0 forks
Report repository
Releases
1tag
Packages
No packages published
Contributors
5
 (5)
@sujan-s
@nareshvelu96
@Geetika-Shukla
@vishes-jena-rbihub
@Swati-072
Languages
TypeScript
66.1%
JavaScript
26.9%
CSS
5.3%
Go
0.9%
HCL
0.7%
Shell
0.1%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
Reserve-Bank-Innovation-Hub
dbie.rbihub.in
Repository navigation
Code
Issues
Pull requests
Agents
Actions
Projects
Security and quality
Insights
Reserve-Bank-Innovation-Hub
dbie.rbihub.in
Public
Go to file
t
T
Geetika-Shukla
Geetika-Shukla
Merge pull request #41 from Reserve-Bank-Innovation-Hub/one-lakh-story
cc489dd
 · 
yesterday
Name		
.github/workflows
Data API service, its deployment, and the site served from releases
3 weeks ago
data
Merge pull request #40 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
dbie-backend/data-api
Data API: build the image with Go 1.25
3 weeks ago
docs
What ₹1 lakh could buy: the story renamed, every chapter pinned, the …
yesterday
infra/terraform
CloudFront: cache policy of our own for the data API
3 weeks ago
mcp
mcp README: workspace install, clone registration, serve-your-own-data
3 months ago
public
Merge pull request #40 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
scripts
db:check reads a report row's cells whole, line breaks and all
2 weeks ago
src
Merge pull request #41 from Reserve-Bank-Innovation-Hub/one-lakh-story
yesterday
.env.common.example
Scrape DBIE over plain HTTP; Postgres as the system of record
3 weeks ago
.env.development
Add enni analytics: collector, hit endpoint, /enni dashboard
3 months ago
.gitignore
What ₹1 lakh bought: a new story on one sum carried from 2001 to 2026
yesterday
.seriseirc
Charts: fictoan colour tokens, one hue table and layered schemes
2 weeks ago
CLAUDE.md
Scrape of 28-09-2026: daily to monthly datasets and reports
2 weeks ago
LICENSE
Flatten to a single-manifest repo; MIT license; open-source README (#4)
4 months ago
README.md
Document the architecture and add agent context
3 weeks ago
amplify.yml
Data API service, its deployment, and the site served from releases
3 weeks ago
next.config.js
Data API service, its deployment, and the site served from releases
3 weeks ago
package.json
The women who stayed: a new agriculture story, at /stories/the-women-…
yesterday
pnpm-lock.yaml
The women who stayed: a new agriculture story, at /stories/the-women-…
yesterday
pnpm-workspace.yaml
Fold mcp into the pnpm workspace; harden the publish workflow
3 months ago
tsconfig.json
Upgrade to Next 16, React 19 and fictoan-react 2.0.0-beta.19 (#19)
3 months ago
Repository files navigation
README
MIT license
dbie.rbihub.in
A modern, fully static web platform for exploring economic data from the Reserve Bank of India's Database on Indian Economy (DBIE)—plus the scraping and processing pipeline that keeps its data fresh. 335 tables and series across prices, growth, markets, banking, external sector, government finance and payments, each with a searchable page, AG Grid table and (where it fits) a Plotly chart—and an MCP server so AI assistants can use the data too.

Built by the Reserve Bank Innovation Hub. MIT licensed. Start with docs/architecture.md for how it all fits together.

Quickstart
pnpm install

# get the site's data (the current release, built from the database's source files)
pnpm data:pull

pnpm dev            # run the site at localhost:3000
pnpm build          # static production build (SSG)
Scraping DBIE yourself
pnpm data:fetch       # restore the latest scrape's raw files from the S3 archive into data/ (no credentials needed)
pnpm scrape           # scrape all 252 SDMX series from DBIE over plain HTTP (~10 min; resumable)
pnpm data:ingest      # file the scraped CSVs into data/sdmx/ under readable names
pnpm scrape:report    # review what changed against the previous scrape's CSVs
pnpm scrape:catalogue # refresh the Statistics + Publications table catalogue (data/reports-catalogue.json)
pnpm scrape:reports   # export report tables (Statistics + Publications menus) to data/reports/ via the BusinessObjects REST layer
pnpm scrape:codelists # fetch the SDMX dimension code → label lists (data/sdmx-codelists/)
pnpm db:load          # load everything into the project's Postgres, the system of record (docs/database.md)
pnpm data:archive     # archive the scrape's raw files to S3 under their date
pnpm data:release     # build + verify the site bundle and publish it as a release
See docs/scraper.md for filters (single sector/series), resume behaviour, and how the gateway is driven without a browser, and docs/dbie-portal-anatomy.md for how the DBIE portal works under the hood.

How it works
DBIE ──scrape──▶ data/ (raw files; not in git) ──pnpm db:load──▶ Postgres (system of record)
                   │                                                  ▲ MCP server, analysts
                   ├──pnpm data:archive──▶ s3://dbie-common-scrapes/scrapes/<date>/
                   └──pnpm data:release──▶ processors → verified JSON → s3://dbie-common-site-data/releases/<version>/
                                                                              │ pnpm data:pull (Amplify build)
                                                                              ▼
                                                              next build → every page pre-rendered (SSG)
The database is the system of record for everything scraped (1,033 tables plus a catalogue and code lists); git holds code and small metadata only, and every scrape's raw files are archived to S3 under their date.
The data API (dbie-backend/data-api) serves every table, its rows and CSV, the catalogue and the code lists from the database, read-only (docs/data-api.md).
Pages are pre-rendered at build time from a data release in public/data/: no API, no database in the request path.
All interactivity (Plotly charts, AG Grid, search) is client-side.
The processors are self-checking (hard-coded known cells) and their outputs are verified byte-exact against committed oracles before a release is published.
Repository layout
Path	What
src/, public/, next.config.js	The Next.js app (TypeScript)
scripts/	DBIE scraper + ingest tooling (plain HTTP; gateway client and cipher in scripts/lib/; browser probes in scripts/recon/)
data/sdmx/, data/reports/	Scraped SDMX series (CSV) and report exports (CSV + xlsx); not in git: pnpm data:fetch restores them from the S3 archive
data/sources/, data/publications/	Manually downloaded report files (the DBIE Reports path needs a rationed guest SAP session; see docs)
data/processors/	Source files → the JSON the site renders (pnpm data:build, verified by pnpm data:verify)
data/catalogue.json, data/sdmx-tree.json, data/scrape-manifest.json	Table index + scrape state
data/sdmx-codelists/	DBIE code lists (dimension code → label) per SDMX dataset
infra/terraform/	The database, bastion, buckets and release role in the common-projects account (docs/database.md)
data/coverage-report.md	What the scrape covers vs the DBIE Reports catalogue
mcp/	@reserve-bank-innovation-hub/dbie-mcp — MCP server over the site's data
scripts/db/	Loaders for the project's Postgres database (schemas, SDMX and report tables, catalogue, checks; docs/database.md)
dbie-backend/data-api/	Read-only Go API over the database: every table, rows, CSV, catalogue, code lists (docs/data-api.md)
docs/	architecture.md (the map), database.md, data-api.md, scraper.md, dbie-portal-anatomy.md
Data refresh
pnpm scrape and pnpm scrape:reports — refresh the raw files in data/ (SDMX over plain HTTP; the report tables through the BusinessObjects REST layer); pnpm scrape:report reviews what changed.
pnpm db:load — load into Postgres; every table is verified against its file.
pnpm data:archive — archive the raw files to S3 under the scrape date.
pnpm data:release — run the processors, verify against the oracles, publish the site bundle as a release; then rebuild the site (Amplify picks up the current release with pnpm data:pull).
Commit the code and metadata changes (catalogues, code lists, oracles); the raw files stay out of git.
The release-data workflow does step 4 from an archived scrape, on demand or when the processors change on main; every site branch's build downloads the current release.

AI access (MCP)
AI assistants can search and fetch every table via the bundled MCP server — see mcp/README.md:

claude mcp add dbie -- npx -y @reserve-bank-innovation-hub/dbie-mcp
Contributing
Issues and PRs welcome. The pipeline is deliberately boring: plain Node scripts, no framework, one workspace (pnpm install covers the app and the MCP package). If you add a dataset, add its processor under data/processors/ and verify its output against a known-good snapshot (see data/processors/README.md for the parity gotchas when porting spreadsheet parsers).

License
MIT

About
No description, website, or topics provided.
Resources
Readme
MIT license
Activity
Custom properties
Stars
0 stars
Watchers
1 watching
Forks
0 forks
Report repository
Releases
1tag
Packages
No packages published
Contributors
5
 (5)
@sujan-s
@nareshvelu96
@Geetika-Shukla
@vishes-jena-rbihub
@Swati-072
Languages
TypeScript
66.1%
JavaScript
26.9%
CSS
5.3%
Go
0.9%
HCL
0.7%
Shell
0.1%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
Alex2Yang97
yahoo-finance-mcp
Repository navigation
Code
Issues
4
 (4)
Pull requests
7
 (7)
Agents
Actions
Projects
Security and quality
Insights
Alex2Yang97
yahoo-finance-mcp
Public
Go to file
t
T
haiiibin
haiiibin
fix: normalize US class-share tickers (BRK.B -> BRK-B) so they don't …
b9c1765
 · 
3 weeks ago
Name		
assets
fix video
last year
tests
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
.gitignore
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
.pre-commit-config.yaml
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
.python-version
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
Dockerfile
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
LESSONS.md
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
LICENSE
Initial commit
last year
README.md
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
README.zh.md
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
pyproject.toml
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
server.py
fix: normalize US class-share tickers (BRK.B -> BRK-B) so they don't …
3 weeks ago
smithery.yaml
fix
last year
uv.lock
chore: upgrade to mcp@v2 and yFinance@v116 (#22)
2 months ago
Repository files navigation
README
MIT license
Yahoo Finance MCP Server
English | 中文
This is a Model Context Protocol (MCP) server that provides comprehensive financial data from Yahoo Finance. It allows you to retrieve detailed information about stocks, including historical prices, company information, financial statements, options data, and market news.

GitHub last commit

Demo


MCP Tools
The server exposes the following tools through the Model Context Protocol:

Stock Information
Tool	Description
get_historical_stock_prices	Get historical OHLCV data for a stock with customizable period and interval
get_stock_info	Get comprehensive stock data including price, metrics, and company details
get_yahoo_finance_news	Get latest news articles for a stock
get_stock_actions	Get stock dividends and splits history
Financial Statements
Tool	Description
get_financial_statement	Get income statement, balance sheet, or cash flow statement (annual/quarterly)
get_holder_info	Get major holders, institutional holders, mutual funds, or insider transactions
Options Data
Tool	Description
get_option_expiration_dates	Get available options expiration dates
get_option_chain	Get options chain for a specific expiration date and type (calls/puts)
Analyst Information
Tool	Description
get_recommendations	Get analyst recommendations or upgrades/downgrades history
Real-World Use Cases
With this MCP server, you can use Claude to:

Stock Analysis
Price Analysis: "Show me the historical stock prices for NOW over the last 6 months with daily intervals."
Financial Health: "Get the quarterly balance sheet for Intuit."
Performance Metrics: "What are the key financial metrics for Intuit from the stock info?"
Trend Analysis: "Compare the quarterly income statements of ServiceNow and Intuit."
Cash Flow Analysis: "Show me the annual cash flow statement for ServiceNow."
Market Research
News Analysis: "Get the latest news articles about Intuit."
Institutional Activity: "Show me the institutional holders of NOW stock."
Insider Trading: "What are the recent insider transactions for ServiceNow?"
Options Analysis: "Get the options chain for INTU with expiration date 2026-01-30 for calls."
Analyst Coverage: "What are the analyst recommendations for Intuit over the last 3 months?"
Investment Research
"Create a comprehensive analysis of Intuit's financial health using their latest quarterly financial statements."
"Compare the dividend history and stock splits of Coca-Cola and PepsiCo."
"Analyze the institutional ownership changes in ServiceNow over the past year."
"Generate a report on the options market activity for Intuit stock with expiration in 30 days."
"Summarize the latest analyst upgrades and downgrades in the tech sector over the last 6 months."
Requirements
Python 3.14.6 or higher
Dependencies as listed in pyproject.toml, including:
mcp
yfinance
pandas
pydantic
and other packages for data processing
Setup
Recommended: run with uvx
Run the server directly from the repository without creating a local virtual environment:

uvx --from git+https://github.com/Alex2Yang97/yahoo-finance-mcp yahoo-finance-mcp
Local development
Clone this repository:

git clone https://github.com/Alex2Yang97/yahoo-finance-mcp.git
cd yahoo-finance-mcp
Create and activate a virtual environment and install dependencies:

uv sync
Usage
Quick Start
Run the packaged entrypoint with:

uvx --from git+https://github.com/Alex2Yang97/yahoo-finance-mcp yahoo-finance-mcp
For local changes in this checkout, use:

uvx --from . yahoo-finance-mcp
Development Mode
If you are working inside a local clone and want to run the source tree directly:

uv run server.py
Integration with Claude for Desktop
To integrate this server with Claude for Desktop:

Install Claude for Desktop to your local machine.

Install VS Code to your local machine. Then run the following command to open the claude_desktop_config.json file:

MacOS: code ~/Library/Application\ Support/Claude/claude_desktop_config.json
Windows: code $env:AppData\Claude\claude_desktop_config.json
Edit the Claude for Desktop config file, located at:

macOS:

{
  "mcpServers": {
    "yfinance": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Alex2Yang97/yahoo-finance-mcp",
        "yahoo-finance-mcp"
      ]
    }
  }
}
Windows:

{
  "mcpServers": {
    "yfinance": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Alex2Yang97/yahoo-finance-mcp",
        "yahoo-finance-mcp"
      ]
    }
  }
}
Note: You may need to put the full path to the uv executable in the command field. You can get this by running which uv on MacOS/Linux or where uv on Windows.

Restart Claude for Desktop

License
MIT

About
This is a Model Context Protocol (MCP) server that provides comprehensive financial data from Yahoo Finance. It allows you to retrieve detailed information about stocks, including historical prices, company information, financial statements, options data, and market news.

Topics
Resources
Readme
MIT license
Activity
Stars
359 stars
Watchers
6 watching
Forks
166 forks
Report repository
Releases
No releases published
Packages
No packages published
Contributors
6
 (6)
@Alex2Yang97
@richin13
@modesty
@lwsinclair
@liuyang1520
@haiiibin
Languages
Python
98.2%
Dockerfile
1.8%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
rehan1020
MCP-India-Stack
Repository navigation
Code
Issues
Pull requests
Agents
Actions
Projects
Wiki
Security and quality
Insights
rehan1020
MCP-India-Stack
Public
Go to file
t
T
rehan1020
rehan1020
chore: bump version to 0.6.9 for PyPI release
bb0a1c2
 · 
2 days ago
Name		
.github
chore: Update 6/7: Dependency reproducibility and yfinance isolation
last week
data
chore: bump version to 0.6.3 for clean publish
3 weeks ago
docs
chore: bump version to 0.6.7 across remaining files
last week
scripts
feat: Data supply-chain trust and verification (Update 2/7)
3 weeks ago
src/mcp_india_stack
chore: bump version to 0.6.9 for PyPI release
2 days ago
tests
chore: bump version to 0.6.9 for PyPI release
2 days ago
.env.example
Update 3/7: Resolve dead/unsafe scaffolding
3 weeks ago
.gitignore
docs: revamp documentation and finalize v0.4.2
4 months ago
.pre-commit-config.yaml
docs: refresh documentation for v0.2.0 launch
7 months ago
CHANGELOG.md
docs: revamp documentation and finalize v0.4.2
4 months ago
CODEOWNERS
release: v0.3.0 - Add 18 new tools, tax calculators, workflows, and d…
6 months ago
CONTRIBUTING.md
chore: Update 6/7: Dependency reproducibility and yfinance isolation
last week
LICENSE
docs: refresh documentation for v0.2.0 launch
7 months ago
NOTICES
docs: refresh documentation for v0.2.0 launch
7 months ago
README.md
Revise demo section to links only
3 weeks ago
SECURITY.md
release: v0.3.0 - Add 18 new tools, tax calculators, workflows, and d…
6 months ago
SETUP.md
chore: decompose server.py by domain into registrations module
2 weeks ago
_parsed_server.json
chore: decompose server.py by domain into registrations module
2 weeks ago
pyproject.toml
chore: bump version to 0.6.9 for PyPI release
2 days ago
release_notes_v0.6.5.md
chore: bump version to 0.6.5
3 weeks ago
render.yaml
feat: network boundary lockdown with CORS, Auth, and Rate Limiting (U…
last month
requirements.txt
fix: compile universal lockfile for py3.10-3.12 multi-environment CI
2 days ago
resources.md
chore: bump version to 0.6.7 across remaining files
last week
smithery.yaml
chore: decompose server.py by domain into registrations module
2 weeks ago
tiers.txt
Update 3/7: Resolve dead/unsafe scaffolding
3 weeks ago
Repository files navigation
README
Contributing
MIT license
Security
🇮🇳 MCP India Stack
A high-performance, offline-first Model Context Protocol (MCP) server equipping AI agents with Indian financial, tax, and government APIs. Zero authentication required.

PyPI version License: MIT MCP Compatible CI Verified on MseeP MseeP.ai Security Assessment Badge

📑 Table of Contents
Problem Statement
Tech Stack
Architecture Diagram
Demo & Links
Key Features
Quick Start
Tool Catalog
Agent Workflows & Resources
Data Architecture & Freshness
Limitations
Legal & Attribution
Launch Notes
📌 Problem Statement
Fragmented Access: Indian fintech, identity, and tax APIs are heavily siloed, requiring multiple disjointed integrations.
High Barriers to Entry: Existing solutions are plagued by paid subscriptions, strict rate limits, and complex API key management.
No Native AI Integration: There is no MCP-native standard designed specifically for autonomous AI agents to validate GSTIN, PAN, IFSC, or compute tax data.
Latency & Reliability Issues: Depending on remote third-party APIs for static/slow-moving datasets introduces unnecessary network delays and potential points of failure for AI workflows.
🛠️ Tech Stack
Layer	Technology
Protocol	MCP (FastMCP)
Runtime	Python
Distribution	PyPI / Smithery
Hosting	Render
Datasets	Offline-bundled (jsDelivr CDN sync)
🏗️ Architecture Diagram
Architecture MCP Client ↔ MCP Server ↔ 76 offline-first tool modules

🔗 Links
Deployment: https://pypi.org/project/mcp-india-stack/
PPT: https://gamma.app/docs/Problem-India-lacks-native-fintech-primitives-for-AI-agents-d1izzfemlvfvkf0?mode=doc
GitHub: https://github.com/rehan1020/MCP-India-Stack
PyPI: https://pypi.org/project/mcp-india-stack/
✨ Key Features
Offline-First Architecture: Bundles compressed datasets for zero-latency lookups (IFSC, Pincodes, HSN/SAC). No API rate limits.
Zero Authentication: No API keys, secrets, or subscriptions required. All logic runs locally.
Background Auto-Updates: Non-blocking CDN fetching ensures your datasets never go stale without impacting request latency.
Comprehensive Coverage: 76 dedicated tools for identity validation (PAN, Aadhaar, GSTIN, TAN, PRAN), tax calculation (Income Tax, TDS, GST), savings calculators (EPF, PPF, SIP), and master data lookups.
Enterprise-Ready: Thread-pool accelerated bulk validation tools for processing large batches of vendor or customer data.
🚀 Quick Start
Installation
pip install mcp-india-stack
Claude Desktop Configuration
Add the following to your claude_desktop_config.json file to enable the India Stack in Claude Desktop:

Windows (%APPDATA%\Claude\claude_desktop_config.json):

{
  "mcpServers": {
    "mcp-india-stack": {
      "command": "python",
      "args": ["-m", "mcp_india_stack"]
    }
  }
}
macOS/Linux (~/Library/Application Support/Claude/claude_desktop_config.json or ~/.config/Claude/claude_desktop_config.json):

{
  "mcpServers": {
    "mcp-india-stack": {
      "command": "python3",
      "args": ["-m", "mcp_india_stack"]
    }
  }
}
🛠️ Tool Catalog
🔍 Lookup Tools
lookup_ifsc — Bank branch details from IFSC code
lookup_pincode — India pincode details and post offices
lookup_hsn_code — HSN/SAC code lookup by code or keyword
decode_state_code — GST state code metadata
lookup_bbps_biller — BBPS biller directory lookup
lookup_bank — Basic bank master lookup by name or code
✅ Validation Tools
validate_gstin — GSTIN structure and checksum
validate_pan — PAN format and entity type decode
validate_upi_vpa — UPI VPA structure and provider decode
validate_aadhaar — Aadhaar number with Verhoeff checksum (masked output)
validate_voter_id — Voter ID (EPIC) format with legacy detection
validate_driving_license — DL format with state/RTO/year decode
validate_passport — Indian passport number format
validate_cin — Company Identification Number with full field decode
validate_din — Director Identification Number format
validate_fssai — FSSAI license number validation and decode
validate_epf_code — EPF establishment code validator
validate_esic_code — ESIC employer code validator
validate_tan — TAN validator
validate_pran — PRAN validator for NPS
validate_llpin — LLPIN validator
decode_isin — ISIN decoder with Luhn validation
decode_digilocker_uri — DigiLocker URI decoder and validator mapper
decode_pan_type — Decode PAN entity type from the 4th character
📱 Identity & Contact
validate_mobile_number — Mobile number with operator/circle detection
⚡ Bulk Operations
bulk_validate_gstin — Parallel GSTIN batch validation
bulk_validate_pan — Parallel PAN batch validation
bulk_validate_ifsc — Parallel IFSC batch validation
bulk_validate_aadhaar — Parallel Aadhaar batch validation
🧮 Tax & Financial Calculators (FY2025-26)
calculate_income_tax — Old vs new regime comparison with surcharge, rebate, cess
calculate_tds — TDS rate lookup and computation for 15+ sections
calculate_gst — GST breakdown (CGST/SGST/IGST/cess) with HSN lookup
calculate_surcharge — Surcharge and marginal relief calculator
calculate_hra_exemption — HRA exemption calculator for salary planning
calculate_capital_gains — Capital gains with Section 54/54F exemption
calculate_advance_tax — Advance tax estimator
calculate_gst_late_fee — GST late filing penalty
calculate_income_tax_interest — Sections 234A/B/C interest
calculate_presumptive_tax — 44AD/44ADA presumptive tax
get_regulatory_deadlines — Tax & regulatory compliance calendar
💰 Savings & Investment Calculators
calculate_epf_esic — EPF/ESIC contribution calculator
calculate_emi — Loan EMI with amortization schedule
calculate_gratuity — Gratuity under Payment of Gratuity Act
calculate_ppf_maturity — PPF maturity projections
calculate_fd_maturity — Fixed Deposit maturity
calculate_rd_maturity — Recurring Deposit maturity
calculate_sip_returns — SIP returns with inflation adjustment
calculate_step_up_sip — Step-up SIP comparison
calculate_nps_projection — NPS corpus and pension
calculate_sukanya_samriddhi — SSY and SCSS calculator
🏠 Real Estate
calculate_home_vs_rent — Buy vs rent financial comparison
calculate_leave_encashment_tax — Section 10(10AA) leave encashment
💼 HR & Payroll
calculate_professional_tax — State-wise professional tax
calculate_salary_restructuring — Tax-optimized salary restructuring
🏦 Banking & Payments
calculate_neft_rtgs_imps_charges — Transaction charges
📈 Stock Market
get_stock_quote — Fetch live/delayed Indian stock quotes and summaries (NSE/BSE) using yfinance.
get_stock_history — Fetch historical end-of-day data for Indian stocks using yfinance.
⚖️ Legal Reference
decode_cnr_number — CNR (Case Number Record) decoder and validator
lookup_court_establishment_code — Court establishment code directory lookup
lookup_ipc_section — IPC section lookup with BNS crosswalk
lookup_bns_section — BNS section lookup with IPC crosswalk
lookup_crpc_section — CrPC section lookup with BNSS crosswalk
lookup_bnss_section — BNSS section lookup with CrPC crosswalk
lookup_evidence_act_section — Indian Evidence Act section lookup
lookup_bsa_section — BSA section lookup with IEA crosswalk
decode_ipc_bns_crosswalk — Bidirectional IPC↔BNS section crosswalk
calculate_limitation_deadline — Limitation Act 1963 deadline calculator
calculate_court_fee — State-wise court fee calculator
calculate_stamp_duty — State-wise stamp duty and registration fee calculator
📋 RTI Toolkit
calculate_rti_fee — RTI application fee calculator (central + state)
calculate_rti_deadline — RTI response and appeal deadline calculator
calculate_rti_penalty_estimate — RTI penalty estimator (Section 20)
draft_rti_application — RTI application drafter (Section 6)
draft_first_appeal — First appeal template generator (Section 19)
draft_second_appeal — Second appeal template generator (Section 19)
🔐 Account Aggregator (Offline)
build_aa_consent_request — AA consent request builder
validate_aa_consent_artifact — AA consent validator
decode_aa_fi_type — AA FI type decoder
🔄 Agent Workflows & Resources
Prompt Workflows (Overview)
Built-in prompt templates to guide AI agents through complex multi-step tasks:

vendor_kyc — GSTIN, PAN, and IFSC verification sequence.
salary_planner — Income, HRA, and optimized take-home salary planning.
invoice_audit — Cross-referencing GSTINs, HSN codes, and applicable GST rates.
Server Resources (Overview)
Dynamic JSON resources provided directly to the LLM context:

india://status — Version, DB connectivity, and runtime flags
india://changelog — Structured changelog resource
india://schema/* — JSON schemas for all tool outputs
📡 Data Architecture & Freshness
This package bundles static datasets for offline-first workflows (approx. 10-11MB compressed footprint), covering IFSCs, Pincodes, HSN/SAC masters, and curated UPI handles.

An optional auto-update mechanism fetches the latest versions from the jsDelivr CDN in the background:

Non-blocking: Stale data triggers a background refresh; the current request immediately uses existing cached data to ensure zero latency.
Opt out: Set the MCP_INDIA_STACK_NO_AUTO_UPDATE=1 environment variable to disable all update checks.
Manual refresh: Run mcp-india-stack --refresh-all to synchronously refresh all datasets from the CDN.
Cache location: Platform-specific via platformdirs (e.g., ~/.cache/mcp-india-stack on Linux).
⚠️ Limitations
Stateless Validation: GSTIN, Aadhaar, Voter ID, DL, Passport, CIN, and DIN validators check structural formatting and checksums only. They do not verify active registration status with government issuing authorities.
Algorithmic Constraints: PAN validation is structural; the PAN check character logic is not publicly verifiable.
Tax Estimates: All tax calculations are algorithmic estimates based on FY2025-26 rules. Actual liability may differ. Always consult a Chartered Accountant.
Static Rates: HSN/SAC rates are static references and may vary based on specific conditions or new government notifications.
⚖️ Legal & Attribution
See NOTICES for detailed dataset attribution, licensing details, and third-party acknowledgments.

See LEGAL_NOTICE.md for important legal disclaimers including:

No Government Affiliation — This project is not affiliated with NIC, eCourts, MeitY, or any government body.
Not Legal Advice — All outputs (bare-act lookups, limitation calculations, court fee estimates, stamp duty estimates, RTI deadline/penalty calculations) are algorithmic estimates, not legal advice.
Data Accuracy — State-subject data (court fees, stamp duty) carries as_of / last_verified fields and is not live-verified against issuing authorities.
Personal Data — Identity validation (Aadhaar, PAN, etc.) is structural/checksum only. Users are responsible for DPDP Act compliance.
🚀 Launch Notes
This repository is release-ready for GitHub launch with:

0.6.0 package metadata and changelog coverage.
A complete MCP server-card under docs/.well-known/mcp/server-card.json.
Local setup and publishing steps in SETUP.md.
Contribution guidance and versioning policy in CONTRIBUTING.md.
New in v0.6.0 — Legal Reference & RTI Toolkit
Legal Reference: CNR decoder, court establishment lookup, bare-act section lookups (IPC/BNS/CrPC/BNSS/IEA/BSA), IPC↔BNS crosswalk, limitation period calculator, court fee calculator (10 states), stamp duty calculator (10 states).
RTI Toolkit: RTI fee calculator, deadline tracker, penalty estimator, application/appeal template drafters.
Capital Gains: Updated LTCG exemption from ₹1L to ₹1.25L (Budget 2024).
Stock Market: Added yfinance-based get_stock_quote and get_stock_history tools.
Bug fixes in v0.4.2 (Round 2 — Deep Code Audit)
Capital Gains: Asset-type-specific LTCG thresholds — real estate 24mo, gold/debentures 36mo, crypto always 30% flat.
EPF/ESIC: Employee EPF correctly capped at ₹15K wage ceiling. Added voluntary_pf_on_actual for VPF.
HRA: Removed Bangalore/Hyderabad/Pune from metro cities. Only Delhi/Mumbai/Chennai/Kolkata get 50%.
Presumptive Tax: Full 7-slab new regime coverage with 87A rebate (was truncated at 3 slabs).
GST Late Fee: GSTR9 cap enforced (0.25% of turnover). Nil return rate corrected to ₹20/day.
Income Tax Interest: Section 234C uses cumulative paid vs required (not single-quarter).
Advance Tax: Installments show incremental installment_amount (not confusing cumulative).
Salary Restructuring: Removed obsolete ₹19,200 conveyance exemption. Standard deduction (₹75K) shown.
Bug fixes in v0.4.1
Security: Masked Aadhaar number leakage in response fields.
Validation: Fixed mobile number over-counting digits issue.
Tax Rules: Corrected Presumptive Tax (44AD/44ADA) thresholds to FY25-26 rules.
Financial: Fixed Step-up SIP compounding return calculation.
Data: Added missing HSN codes (8517, 9401, 2523, 3004, 8708) with correct GST rates.
Professional Tax: Fixed annual total calculations based on correct monthly slabs.
Income Tax: Fixed 80D deduction cap for senior citizens.
ISIN: Fixed Luhn checksum multi-digit expansion logic.
EMI Calculator: Improved error responses to not leak fallback fields on invalid inputs.
Advance Tax: Added support for overriding internal computations with user-provided tax_liability.
Offline-First Guarantee: All tools in this package work without an internet connection. No API keys required. No data is sent to any external server. All datasets are bundled in the package at install time.

About
MCP server for Indian APIs — GSTIN, IFSC, PAN, UPI, pincode, HSN/SAC. Zero auth. Offline-first. For AI agents.

pypi.org/project/mcp-india-stack/
Topics
Resources
Readme
MIT license
Contributing
Contributing
Security policy
Security policy
Activity
Stars
64 stars
Watchers
2 watching
Forks
11 forks
Report repository
Releases
Deployments
Packages
Contributors
Languages
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 Skip to content
GirishKumarDV
Live-NSE-BSE-MCP
Repository navigation
Code
Issues
Pull requests
Agents
Actions
Projects
Security and quality
Insights
GirishKumarDV
Live-NSE-BSE-MCP
Public
Go to file
t
T
author
Girish.Kumar
Restructure Project and update Readme
75cedc2
 · 
last year
Name		
client
Restructure Project and update Readme
last year
examples
Restructure Project and update Readme
last year
ise_mcp
Restructure Project and update Readme
last year
tests
Restructure Project and update Readme
last year
.gitignore
Restructure Project and update Readme
last year
LICENSE
Restructure Project and update Readme
last year
MANIFEST.in
Restructure Project and update Readme
last year
README.md
Restructure Project and update Readme
last year
__init__.py
vibe client
last year
env.example
Restructure Project and update Readme
last year
ise-mcp-server.bat
Restructure Project and update Readme
last year
ise-mcp-stdio.bat
Restructure Project and update Readme
last year
pyproject.toml
Restructure Project and update Readme
last year
requirements.txt
Restructure Project and update Readme
last year
setup.py
Restructure Project and update Readme
last year
Repository files navigation
README
MIT license
Indian Stock Exchange MCP Server
This server provides access to live market data from Indian Stock Exchanges (BSE & NSE) through the Model Context Protocol (MCP), powered by IndianAPI.

🚀 Quick Start
Prerequisites
Python 3.8+
pip (Python package installer)
API Key from IndianAPI: Sign up at https://indianapi.in/ and obtain an API key for the Stock Market API
Installation
Note: This package is not yet published to PyPI. Please use source installation for now.

Option 1: Quick Install from Source (Recommended)
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -e .
Option 2: Development Installation
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -r requirements.txt
pip install -e .
Option 3: Manual Execution (No Installation)
If you prefer not to install the package:

git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -r requirements.txt
# Run directly with: python -m ise_mcp.server
Important: Since the package isn't on PyPI yet, use module execution (python -m ise_mcp.server) or install from source for the console scripts to work.

Configuration
Get your API key:

Visit https://indianapi.in/
Sign up for a free account
Navigate to the Stock Market API section
Subscribe to get your API key
Configure environment variables:

# Copy the example environment file
cp env.example .env

# Edit .env and add your IndianAPI key
# ISE_API_KEY=your_indianapi_key_here
Usage
HTTP Server Mode (for web clients like Cursor, VSCode, Dify)
After installation, you can run the server in several ways:

Method 1: Module Execution (Recommended)

# From the project root directory
python -m ise_mcp.server
Method 2: Using Batch Script (Windows)

# Use the provided batch script (note the .\ prefix for PowerShell)
.\ise-mcp-server.bat

# Or with environment variables
$env:ISE_HTTP_PORT=9000; .\ise-mcp-server.bat
Method 3: Development Mode

# If not installed, run as module from parent directory
cd ..
python -m ise_mcp.server
Note: Console scripts from PyPI (ise-mcp-server) are not available yet. Use module execution or the batch script instead.

The server will start on http://localhost:8000 by default.

Stdio Mode (for direct MCP clients like Claude Desktop)
Method 1: Module Execution (Recommended)

# From the project root directory
python -m ise_mcp.stdio_server
Method 2: Using Batch Script (Windows)

# Use the existing batch script (note the .\ prefix for PowerShell)
.\ise-mcp-stdio.bat
Note: Console scripts from PyPI (ise-mcp-stdio) are not available yet. Use module execution or the batch script instead.

Important: Do NOT run the server files directly (e.g., python server.py) as this will cause import errors. Always use the console scripts or module execution.

🔧 Configuration
The server uses environment variables for configuration. Create a .env file in the project root with the following variables:

# Required: API Key from IndianAPI (https://indianapi.in/)
ISE_API_KEY=your_indianapi_key_here

# Optional: API Base URL (default: https://stock.indianapi.in/)
ISE_API_BASE_URL=https://stock.indianapi.in/

# Optional: Server configuration
ISE_HTTP_HOST=0.0.0.0
ISE_HTTP_PORT=8000
ISE_REQUEST_TIMEOUT=30
ISE_LOG_LEVEL=INFO
Important: The ISE_API_KEY is required and the server will not start without it. Make sure to add your .env file to .gitignore to prevent committing sensitive information.

🌐 Client Integrations
Claude Desktop Integration
Claude Desktop uses the stdio transport for direct MCP communication.

Step 1: Install the Server
Since the package isn't on PyPI yet, install from source:

git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -e .
Step 2: Configure Claude Desktop
Windows: Edit %APPDATA%\Claude\claude_desktop_config.json macOS: Edit ~/Library/Application Support/Claude/claude_desktop_config.json

Choose one of the following configuration methods based on your setup:

Option 1: Using Virtual Environment Python (Most Reliable)

If you have a virtual environment with dependencies installed:

{
  "mcpServers": {
    "ise-mcp": {
      "command": "C:\\path\\to\\your\\project\\venv\\Scripts\\python.exe",
      "args": ["-m", "ise_mcp.stdio_server"],
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here"
      }
    }
  }
}
Option 2: Using PYTHONPATH (Recommended Fallback)

{
  "mcpServers": {
    "ise-mcp": {
      "command": "python",
      "args": ["-m", "ise_mcp.stdio_server"],
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here",
        "PYTHONPATH": "C:\\path\\to\\your\\project"
      }
    }
  }
}
Option 3: Using Batch Script (Windows)

{
  "mcpServers": {
    "ise-mcp": {
      "command": "C:\\path\\to\\your\\project\\ise-mcp-stdio.bat",
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here"
      }
    }
  }
}
Option 4: Direct File Execution

{
  "mcpServers": {
    "ise-mcp": {
      "command": "python",
      "args": ["ise_mcp/stdio_server.py"],
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here",
        "PYTHONPATH": "C:\\path\\to\\your\\project"
      }
    }
  }
}
Option 5: Using PowerShell (if execution policies allow)

{
  "mcpServers": {
    "ise-mcp": {
      "command": "powershell",
      "args": ["-Command", "cd 'C:\\path\\to\\your\\project'; python -m ise_mcp.stdio_server"],
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here"
      }
    }
  }
}
Option 6: After Global Installation

If you've installed the package globally with pip install -e .:

{
  "mcpServers": {
    "ise-mcp": {
      "command": "python",
      "args": ["-m", "ise_mcp.stdio_server"],
      "env": {
        "ISE_API_KEY": "your_indianapi_key_here"
      }
    }
  }
}
macOS/Linux Equivalents:

For macOS/Linux, replace Windows paths with Unix-style paths:

C:\\path\\to\\your\\project becomes /path/to/your/project
venv\\Scripts\\python.exe becomes venv/bin/python
Use forward slashes / instead of backslashes \\
Notes:

Replace C:\\path\\to\\your\\project with your actual project path
Replace your_indianapi_key_here with your actual API key from IndianAPI
Try options in order - Option 1 (virtual environment) is most reliable
If one doesn't work, try the next option
Step 3: Restart Claude Desktop
After saving the configuration, restart Claude Desktop. You should see the ISE MCP tools available in your chat.

Testing Claude Integration
Once configured, you can ask Claude:

"Show me trending stocks in the Indian market"
"Get me data for Reliance Industries"
"What are the top gainers today?"
VSCode Integration
VSCode can use the HTTP transport to connect to the MCP server.

Step 1: Install MCP Extension
Install an MCP-compatible extension in VSCode or use the built-in MCP support if available.

Step 2: Start the HTTP Server
Clone and setup the server first:

# Clone the repository
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP

# Install dependencies  
pip install -r requirements.txt

# Start the server
python -m ise_mcp.server
Step 3: Configure VSCode
Add to your VSCode settings.json:

{
  "mcp.servers": {
    "ise-mcp": {
      "url": "http://localhost:8000/jsonrpc",
      "type": "http"
    }
  }
}
Step 4: Set Environment Variables
Ensure your ISE_API_KEY is set:

# In your terminal before starting VSCode
export ISE_API_KEY=your_indianapi_key_here
code .
Cursor Integration
Cursor supports MCP through HTTP transport.

Step 1: Start the HTTP Server
Clone and setup the server first:

# Clone the repository
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP

# Install dependencies  
pip install -r requirements.txt

# Start the server
python -m ise_mcp.server
Step 2: Configure Cursor
In Cursor, go to Settings → Extensions → MCP and add:

Server URL: http://localhost:8000/jsonrpc
Server Type: HTTP JSON-RPC
Step 3: Environment Setup
Make sure your API key is configured in your .env file:

ISE_API_KEY=your_indianapi_key_here
Testing Cursor Integration
You can now ask Cursor's AI:

"Use the ISE MCP to get stock data for TCS"
"Show me the most active stocks on NSE"
Other MCP Clients
HTTP Transport (Web Clients)
For any HTTP-based MCP client:

URL: http://localhost:8000/jsonrpc
Type: HTTP JSON-RPC 2.0
Content-Type: application/json
Stdio Transport (Command Line)
For stdio-based MCP clients:

# Clone and setup first
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -r requirements.txt

# Direct stdio connection
python -m ise_mcp.stdio_server

# Or with environment variables
ISE_API_KEY=your_key python -m ise_mcp.stdio_server
Dify Integration
Dify can connect using HTTP transport:

URL: http://localhost:8000/jsonrpc
Type: MCP over HTTP
Headers: Content-Type: application/json
Available Tools
The server provides the following tools for accessing Indian stock market data:

Market Data Tools
get_stock_data - Get detailed financial data for a specific company
get_trending_stocks - Get trending stocks with top gainers and losers
get_52_week_high_low - Get stocks with highest and lowest prices in the last 52 weeks
get_nse_most_active - Get most active stocks on NSE by trading volume
get_bse_most_active - Get most active stocks on BSE by trading volume
get_price_shockers - Get stocks with significant price changes
Research Tools
search_industry - Search for companies within a specific industry
get_analyst_recommendations - Get analyst target prices and recommendations
get_stock_forecasts - Get detailed forecast information for a stock
get_historical_data - Get historical stock data with various filters
get_historical_stats - Get historical statistics for a stock
Investment Tools
search_mutual_funds - Search for mutual funds
get_mutual_funds - Get latest mutual fund data with NAV and returns
get_commodities - Get real-time commodity futures data
🔗 API Endpoints
Health Check
GET http://localhost:8000/health
Server Information
GET http://localhost:8000/info
MCP JSON-RPC
POST http://localhost:8000/jsonrpc
📝 Example Usage
Get Stock Data
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_stock_data",
    "arguments": {
      "name": "Reliance"
    }
  },
  "id": 1
}
Get Trending Stocks
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_trending_stocks",
    "arguments": {}
  },
  "id": 2
}
🛠️ Development & Testing
Running Tests
The project includes several test files for different aspects of functionality:

1. Tool Testing
# Test individual MCP tools functionality
python tests/test_tools.py
2. Connection Testing
# Test basic HTTP connections and API responses
python tests/test_connection.py
3. Clean Tools Testing
# Test tool validation and clean responses
python tests/test_clean_tools.py
4. VSCode Integration Testing
# Test VSCode MCP integration
python tests/test_vscode_connection.py
5. Run All Tests
# If you have pytest installed (recommended)
pytest tests/

# Or run all test files manually
python tests/test_tools.py && python tests/test_connection.py && python tests/test_clean_tools.py && python tests/test_vscode_connection.py
Testing with Different Clients
Testing with curl
# Start the HTTP server
python -m ise_mcp.server

# Test health endpoint
curl http://localhost:8000/health

# Test server info
curl http://localhost:8000/info

# Test MCP tool call
curl -X POST http://localhost:8000/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_trending_stocks",
      "arguments": {}
    },
    "id": 1
  }'
Testing with Python Client
# Use the included Python client
cd client
python simple_mcp_client.py

# Or run the basic usage example
cd examples
python basic_usage.py
Debug Mode
Set the log level to DEBUG in your .env file:

ISE_LOG_LEVEL=DEBUG
Development Workflow
Setup Development Environment:

git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
Create Configuration:

cp env.example .env
# Edit .env and add your API key
Run Tests:

python tests/test_tools.py
Start Development Server:

python -m ise_mcp.server
🔒 Security
Environment Variables: All sensitive configuration is stored in environment variables
API Key Protection: The API key is never logged or exposed in responses
CORS: Proper CORS headers are set for cross-origin requests
Input Validation: All tool inputs are validated against JSON schemas
📦 Publishing to PyPI
Current Status: This package is not yet published to PyPI. Users must install from source.

Users should install from source using the methods described in the Installation section.

Development Installation
# Clone and install in development mode
git clone https://github.com/GirishKumarDV/Live-NSE-BSE-MCP.git
cd Live-NSE-BSE-MCP
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black .

# Type check
mypy ise_mcp/
🐛 Troubleshooting
Common Issues
Relative Import Error (attempted relative import with no known parent package):

Problem: Running python server.py or python stdio_server.py directly
Solution: Use module execution (python -m ise_mcp.server, python -m ise_mcp.stdio_server) or install from source with pip install -e .
Server won't start:

Check that your ISE_API_KEY from IndianAPI is set in the .env file
Verify the API key is valid and not expired
API errors:

Verify your IndianAPI key is valid and has sufficient quota
Check if you've subscribed to the Stock Market API on IndianAPI
Connection issues:

Ensure the server is running on the correct host/port
Check if port 8000 is available
Verify firewall settings
CORS errors:

The server includes CORS headers, but check your client configuration
Ensure you're making requests to the correct endpoint
Module not found:

Ensure you've installed the package with pip install -e . from the project directory
Check if virtual environment is activated
Note: PyPI installation (pip install ise-mcp-server) is not available yet
Import errors:

Check Python version compatibility (requires Python 3.8+)
Ensure all dependencies are installed: pip install -r requirements.txt
Installation Issues
Error: No module named 'ise_mcp'
# Solution 1: Install the package
pip install -e .

# Solution 2: Run from correct directory
cd /path/to/Live-NSE-BSE-MCP
python -m ise_mcp.server
Error: ModuleNotFoundError: No module named 'mcp'
# Install MCP dependency
pip install mcp>=1.0.0

# Or install all requirements
pip install -r requirements.txt
Client Integration Issues
Claude Desktop Not Detecting Server
Check configuration file location:
Windows: %APPDATA%\Claude\claude_desktop_config.json
macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
Verify JSON syntax is valid
Restart Claude Desktop completely
Check console logs for error messages
VSCode/Cursor Connection Issues
Ensure HTTP server is running: python -m ise_mcp.server
Test server health: curl http://localhost:8000/health
Check if MCP extension is properly installed
Verify environment variables are set
Error Handling
The server provides detailed error messages in JSON-RPC format:

-32600: Invalid Request
-32601: Method not found
-32602: Invalid params
-32603: Internal error
Transport-Specific Issues
HTTP Transport
Check if port 8000 is available: netstat -an | grep 8000
Verify firewall settings
Test with curl http://localhost:8000/health
Check server logs for error messages
Stdio Transport
Ensure no other output to stdout
Check that environment variables are set
Verify MCP client configuration
Test stdio connection: echo '{"jsonrpc":"2.0","method":"ping","id":1}' | python -m ise_mcp.stdio_server
Development Issues
Tests Failing
# Check if server is running
curl http://localhost:8000/health

# Verify API key is set
echo $ISE_API_KEY

# Run individual tests
python tests/test_connection.py
python tests/test_tools.py
Debugging Server Issues
Enable debug logging in .env:

ISE_LOG_LEVEL=DEBUG
Check server logs for detailed error information

Test API endpoints manually with curl

Verify IndianAPI service status

📚 Related Projects
MCP Client: client/ - Python client for testing
Examples: examples/ - Usage examples
🤝 Contributing
Fork the repository
Create a feature branch
Make your changes
Add tests if applicable
Submit a pull request
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🔗 Links
IndianAPI Marketplace: https://indianapi.in/
Indian Stock API: https://stock.indianapi.in/
Model Context Protocol: https://modelcontextprotocol.io/
MCP Specification: https://spec.modelcontextprotocol.io/
About
An MCP Server that brings you live Indian Stock Exchanges data. Talk to the MCP server to get your latest market news, ipos, top performing stocks, MFs, ETFs and more.

Resources
Readme
MIT license
Activity
Stars
13 stars
Watchers
2 watching
Forks
7 forks
Report repository
Releases
No releases published
Packages
No packages published
Contributors
No contributors
Languages
Python
99.9%
Batchfile
0.1%
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
 