# Alert Pipeline

The "watch and react" loop: detect a new regulatory document, check it against a
tracked portfolio's real exposure graph, and auto-trigger a full investigation for
any genuinely relevant one. See `docs/RIPPLE_INVESTIGATION.md` for the additional
dynamic-discovery step layered on top of this, and `docs/KNOWN_LIMITATIONS.md` for
what's unverified.

## Why this exists

Before this was built, ingestion (`api/handlers/ingest.py`), the exposure graph
(`graph/company_graph.py`), and the investigation orchestrator
(`workflows/local_orchestrator.py`) all existed and were independently tested, but
nothing connected "a new document appeared" to "does this affect a tracked
portfolio" to "run an investigation and record an alert." This module is that
connection.

## Flow

```
Federal Register documents  →  scan_for_new_documents()  →  check_relevance()  →  run_investigation()  →  Alert
     (ingestion)                  (diff vs. Store)         (literal match only)   (same tested pipeline)  (persisted)
```

### 1. Diffing (`scan_for_new_documents`)

Every document is looked up in `riskripple-regulatory-events` (the `Store`
abstraction -- `LocalStore` locally, `DynamoStore` once deployed). A document not
already present is "new"; every document, new or not, gets recorded as seen. This is
what makes a second run against the same input produce zero duplicate alerts --
confirmed in `tests/alerts/test_pipeline.py` and in `scripts/run_alert_scan.py`'s own
re-run check.

### 2. Relevance (`alerts/relevance.py::check_relevance`)

Literal, word-boundary matching only -- against the portfolio's own tickers (direct)
and the exposure graph's supplier edges (indirect/supply-chain), reusing the same
graph `load_company_graph` already builds from real 10-K text. Never a similarity
score, never an LLM guess. Confirmed against the real 20-document fixture set: exactly
2 of 20 are relevant to the demo portfolio, and both are found via a genuine literal
mention (one direct "Nvidia H200", one indirect via Samsung/SK Hynix supply-chain
edges touching NVDA/AMD/INTC).

### 3. Auto-triggered investigation (`run_investigation`)

Any match re-uses the exact same orchestrator a manual analysis would call -- no
separate "alert" code path for the financial math. As of the Ripple Investigation
addition, `run_alert_scan` also runs `investigation.loop.run_ripple_investigation`
between steps 2 and 3 and threads its output into the resulting report (see
`docs/RIPPLE_INVESTIGATION.md`); this never changes *whether* an alert fires, only
what additional, separately-labeled findings the resulting report carries.

### 4. Persistence (`Alert`)

One `Alert` record per relevant document, with every `RelevanceMatch` (symbol,
relationship type, matched entity, evidence sentence) and a link to the full
`InvestigationReport` it triggered. Stored in `riskripple-alerts`
(`infrastructure/cdk/lib/storage-stack.ts`, GSI `by-status`).

## Known limitation

Coverage is bounded by two things, both documented in `docs/KNOWN_LIMITATIONS.md`:
what gets fetched at all (the Federal Register query terms), and what the alias list
in `graph/company_graph.py` knows to look for. `docs/RIPPLE_INVESTIGATION.md` widens
the second without touching the trust boundary that keeps every alert traceable to
real text.
