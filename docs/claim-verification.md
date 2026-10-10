# Economic claim verification: Prices pilot

Direct Prices chat and the Prices A2A artifact now use a shared verification layer
before rendering. Economic values come from retrieved observations. Explicit rules
check those values; no economic answer is hardcoded. Fixed prose templates express
the verified result and reviewed educational definitions.

## Flow

1. `PriceObservation` normalizes geography/sector and assigns a content-derived ID.
2. `prices_sector/verification.py` snapshots observations and search passages.
3. The server proposes basic official claims. The model may propose additional
   structured claims matching `core/verification/models.py`.
4. `verify_claims` validates every proposal and recomputes numerical results.
5. Only controlled rendered text reaches the direct Prices answer. Table rows are
   also filtered through observation verification. Rejected proposals remain in
   the audit rather than being displayed as economic facts.
6. The complete evidence/proposal/result snapshot is saved locally and included
   under `prices_sector_data.verification` (direct API: `data_context.verification`).
   A2A JSON artifacts preserve the same field and observation IDs.

## What the statuses mean

| Status | Guarantee |
|---|---|
| `verified` | Numerical claim passed deterministic checks against the retrieved snapshot. |
| `source_attributed` | Exact complete sentence(s) occur in a retrieved passage; not a semantic or causal proof. |
| `general_mechanism` | Reviewed educational template, not a finding about the current period. |
| `rejected` | Invalid schema, incompatible dimensions, wrong arithmetic/direction, or altered quote. |
| `insufficient_evidence` | Missing evidence, conflicting same-period values, unknown comparison base, or no registered statistical analysis. |

`verified` is not a guarantee that a remote data provider is correct. Geography
and sector checks use normalized source/adapter metadata and the parsed request.
The current qualitative path deliberately displays attributed excerpts rather
than model paraphrases: it does not implement semantic entailment or infer that
a passage explains the requested month. `scope_verified` and
`semantic_support_verified` are explicitly false for these excerpts.

## Numerical checks

Supported operations are an observation, a within-series rate change, and YoY
price direction. Checks cover evidence IDs, finite values, monthly periods, units,
geography, country, sector, indicator, series, source, index base, period ordering,
conflicting observations, and requested scope. Unknown bases withhold comparisons.
Arithmetic uses Decimal and compares proposals at the displayed two-decimal
precision. A 6% to 4% change renders as -2 percentage points. Positive YoY does
not establish month-on-month price direction. Hypothetical basket illustrations
are labelled as examples and computed from the actual verified rate.

Unknown claim types and unrestricted model `text` fields cannot bypass the schema.
There is no model-controlled formula evaluation. Statistical findings require
an analysis registry that is not yet implemented and are therefore withheld.

## IDs and revisions

Observation IDs hash the evidence content, including value, period, definition and
revision-relevant metadata. Retrieval times, freshness, request IDs and comparison
context do not change identity. Changed values/revisions remain separate evidence.
Each audit retains the complete snapshot and original retrieval timestamp. The
local store appends audit rows instead of overwriting previous answers.

## Audit storage and replay

Settings in `core/config.py`:

```dotenv
CLAIM_AUDIT_ENABLED=true
# Default: backend/data/claim_audits.sqlite3
# CLAIM_AUDIT_PATH=C:/path/to/claim_audits.sqlite3
```

Writes run off the async event loop using SQLite transactions. A storage failure
is reported in `verification.persistence` and does not discard the in-response
audit. The database is excluded from Git. This stores evidence and proposals, not
API keys. No automatic retention/deletion policy is implemented.

Run from an environment with `backend` on PYTHONPATH:

```python
from core.config import settings
from core.verification.audit import load_audit
from core.verification.pipeline import verify_claims

saved = load_audit("audit_ID_FROM_RESPONSE", settings.CLAIM_AUDIT_PATH)
replayed = verify_claims(saved["proposals"], saved["evidence"])
assert replayed["results"] == saved["results"]
```

Replay uses local evidence without model or search calls. For a paper experiment,
freeze the evidence and proposed claims, annotate correctness independently, and
compare supported-claim precision, numerical accuracy and answer coverage with
and without verification. Audit counts alone are not accuracy measurements and
the included synthetic regression tests are not a publication benchmark.

## Scope and limitations

- Direct Prices answers and their A2A artifact carry the verified wording/audit.
- Cross-sector orchestrator prose is separately labelled as outside this verifier;
  it may rewrite sector outputs and must not inherit their verification status.
- Missing history is withheld, not fabricated. The normal Prices trend request
  fetches multiple periods; a latest-only result cannot establish a trend.
- Semantic evidence review, registered statistical findings, as-of vintage
  selection, and all-sector verification remain future work.

## Validation

Focused tests cover synthetic arithmetic, null/missing/invalid evidence, zero and
negative rates, scope mismatches, incompatible bases, negation in quotations,
unsupported model claims, audit replay, storage failures, and chat/A2A propagation.
The implementation also passed a live MoSPI/Tavily/DDGS/Groq Prices request with
an available official result, verified numerical claims, source-attributed text,
and a saved audit.
