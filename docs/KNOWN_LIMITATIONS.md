# Known Limitations

This document is maintained as we build, not written retroactively — each item below
was found by actually running something (a command, a build, a test), not by
inspection alone.

## AWS access gaps (personal dev account, `011356580161`, `us-east-2`)

- **`bedrock:ListFoundationModels` and `bedrock:InvokeModel` are access-denied.**
  Confirmed via `aws bedrock list-foundation-models`. This means:
  - The `BedrockModel`-backed `strands.Agent` objects in
    `backend/src/riskripple/agents/definitions.py` have never been invoked live.
    They construct correctly and register their tools correctly (verified), but the
    LLM's tool-selection/orchestration behavior on top of those tools is untested.
  - `BedrockKnowledgeBaseRetriever` in `backend/src/riskripple/rag/retrieval.py` is
    untested against a live Knowledge Base for the same reason.
  - **Action before the hackathon demo:** on the temporary AWS account, run
    `aws bedrock list-foundation-models --region <region>` to find an enabled model
    ID, set `BEDROCK_MODEL_ID` accordingly, and smoke-test one agent end to end
    before relying on the live path in front of judges.
- **`cloudformation:ListStacks` (and by extension `cdk deploy`) is access-denied.**
  `cdk synth` works and has been run successfully for all 4 stacks
  (`RiskRipple-Storage`, `RiskRipple-Api`, `RiskRipple-Ingestion`,
  `RiskRipple-Workflow`), but nothing has been deployed from this account. The
  Lambda container image itself has been built and run locally with Docker
  (confirmed working, including a full real investigation end to end), so the risk
  is isolated to CloudFormation/IAM permissions on this account, not the
  application code.

## Data pipeline

- **SEC EDGAR filing text extraction is capped at 200,000 characters** per filing
  (`fetch_filing_text`'s `max_chars`), and the extracted text includes a large
  block of raw XBRL tag soup at the start of the document before the readable
  narrative sections. It works well enough for retrieval (confirmed: real queries
  correctly surface the actual export-control risk-factor paragraphs), but a
  production version should skip to Item 1/Item 1A before chunking rather than
  truncating by character count.
- **The exposure graph only knows about 7 hardcoded supplier names**
  (`KNOWN_SUPPLIER_ALIASES` in `graph/company_graph.py`) and only scans the 3
  semiconductor 10-Ks in the demo fixture set. Absence of an edge means "not
  found in this limited text," not "confirmed no relationship" — this is stated
  explicitly in every `InvestigationReport.limitations` list, not hidden.
- **The Global Affairs Canada sanctions adapter parses a bilingual XML export**;
  it has not been tested against the GAC entity-only (non-individual) records or
  against schedule/program filtering beyond what's used in
  `search_sanctions_records`.
- **SEC EDGAR and Federal Register requests use a placeholder contact**
  (`SEC_EDGAR_CONTACT` env var, defaulting to a fictional address). Replace with a
  real team contact via environment variable before any ingestion volume beyond
  light testing — SEC's fair-access policy expects a genuine contact.
- Yahoo Finance's chart API is unofficial and undocumented (no SLA, observed HTTP
  429 under bursty unauthenticated requests). The demo deliberately runs off the
  frozen snapshot in `data/fixtures/` rather than live calls for this reason.

## Backend / Lambda

- **`save_investigation_report` writes to local disk** (`/tmp` in the Lambda
  container, via `RISKRIPPLE_REPORTS_DIR`). `/tmp` in Lambda is ephemeral and
  per-execution-environment, not shared or durable. Production should write
  reports to S3 (`reports/` prefix per the data lake layout) instead — not yet
  wired.
- **The `/api/analyses` Lambda runs the investigation synchronously** rather than
  starting the Step Functions execution and polling, as a hackathon-demo
  simplification (the orchestrator completes in ~1-2s against frozen data, well
  within API Gateway's 29s timeout). The Step Functions state machine exists
  (`infrastructure/cdk/lib/workflow-stack.ts`) but isn't wired to the API yet;
  doing so is contingent on confirming the live Bedrock agent path works first.
- **The spec's 13 conceptual Step Functions states (section 15) currently execute
  as sub-steps inside one Lambda task**, not as 13 separate Step Functions states.
  See the docstring in `workflow-stack.ts` for the reasoning — this was a
  deliberate choice to avoid adding retry/catch surface area around an unverified
  live-agent path, not a shortcut taken to look finished.
- Path resolution for fixture/report directories had a real bug (repo-relative
  `parents[N]` paths that broke once the package was installed flat into a Lambda
  container's `/var/task`) — found by actually building and running the Docker
  image, fixed in `riskripple/config.py`. Flagging the fix process here as a
  reminder: cdk synth succeeding does NOT mean the container actually runs
  correctly; only running it does.

## Frontend

- Runs entirely off a single frozen `demoAnalysis.json` fixture (generated by
  actually running the real orchestrator against real data, not hand-written).
  `VITE_API_BASE_URL` swaps it for a live API call once the backend is deployed,
  but that path is untested (no deployed API to point it at yet).
- **No one has visually confirmed the rendered pages.** The production build
  (`tsc -b && vite build`) passes clean and the dev server was confirmed to serve
  correctly on all 7 routes via HTTP, which catches most structural/type errors,
  but a headless-browser visual check (Playwright) could not complete in this
  sandboxed environment — its Chromium download stalled indefinitely despite the
  CDN being reachable. The attempt was removed rather than left half-working.
  **Action before the demo:** run `npm run dev` and click through all 7 pages
  yourself at least once.
- No authentication/authorization layer. Fine for a demo; not fine for anything
  beyond it.

## Testing

- 73 backend tests pass, covering finance calculations, ingestion adapters (where
  feasible without live network calls in CI), the persona engine, the RAG
  chunking/retrieval layer, exposure graph extraction, agent tool wrappers, the
  end-to-end local orchestrator, and the Lambda handlers (against an in-memory
  store).
- No RAG evaluation benchmark (section 16.2's 30-50 question set) has been built
  yet — out of scope given the time available before the hackathon; flagged
  rather than fabricated.
- No load/concurrency testing of the Lambda handlers.
