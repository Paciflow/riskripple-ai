# Tradeoffs

Design decisions made while building this, with the alternative considered and why
it was rejected. Not a list of regrets — a record of what was actually decided and
why, so a judge or a future contributor doesn't have to reverse-engineer intent from
the diff.

## Geometric (not arithmetic) annualized return

**Chose:** compound/geometric annualization (`(prod(1+r))^(periods/n) - 1`).
**Rejected:** arithmetic mean × periods.
**Why:** the arithmetic mean systematically overstates return for volatile series
(volatility drag) — demonstrated in `backend/tests/finance/test_returns.py`, where
+10%/-10% compounds to -1% but averages to 0%. Reporting the arithmetic figure to an
investor would be a real, material overstatement, not a rounding quibble. See
`docs/FINANCIAL_MODELS.md`.

## Local lexical retriever as the default, Bedrock Knowledge Base as a drop-in

**Chose:** build `LocalLexicalRetriever` (TF-IDF, pure Python) first and make
`BedrockKnowledgeBaseRetriever` match its exact call shape (`retrieve(query, top_k=)
-> list[RetrievedChunk]`).
**Rejected:** building only against a Bedrock Knowledge Base from the start.
**Why:** `bedrock:Retrieve` is access-denied on the only AWS account available before
the hackathon (see `docs/KNOWN_LIMITATIONS.md`). Building retrieval, chunking,
citation-building, and every agent tool that depends on them against an
interface that can be swapped later meant the entire RAG pipeline could be built,
tested, and evaluated (`docs/EVALUATION.md`) now instead of waiting for Saturday.
**Cost:** TF-IDF is not semantic retrieval — it won't match a paraphrase that shares
no vocabulary with the source text. This is a real capability gap versus the
production path, not a cosmetic one, and is documented as such rather than
papered over.

## Deterministic local orchestrator instead of only a live agent loop

**Chose:** `workflows/local_orchestrator.py` calls each agent's tool functions
directly, in the spec's documented sequence, without an LLM making the
tool-selection decisions.
**Rejected:** building only the `strands.Agent`-driven path and demoing nothing
until Bedrock access was confirmed.
**Why:** the entire tool chain (ingestion → chunking → retrieval → exposure graph →
finance calculations → persona evaluation → report) needed to be provably correct
on real data independent of whether the LLM reasoning layer works, because that
layer is unverified until the hackathon account exists. This produces an actual,
checkable result today; the live agent path, once confirmed, replaces the fixed
sequence with the model's own tool choices on top of the same tools.
**Cost:** the current demo doesn't show the LLM doing anything — it shows the tools
it would call doing the right thing. That's a materially weaker demo than a working
live agent, and the gap is called out explicitly rather than blurred (`docs/AGENTS.md`).

## One Step Functions task instead of 13 states

**Chose:** `infrastructure/cdk/lib/workflow-stack.ts` wraps the spec's 13 conceptual
pipeline states in one Lambda task.
**Rejected:** modeling all 13 as separate Step Functions states with their own
retry/catch policies now.
**Why:** each state's retry/catch semantics only matter once the thing inside it
(mostly live Bedrock agent calls) is confirmed to behave a particular way under
failure. Building 13 states of error-handling surface around calls that have never
been exercised live risks guessing wrong about failure modes and then having to
redo it anyway. Doing this once, after Saturday's smoke test, is less total work
than guessing twice.
**Cost:** the deployed pipeline (once it is deployed) will initially have coarser
retry granularity than the spec describes — a full-pipeline retry, not a per-step one.

## Synchronous Lambda instead of async + polling, for the demo

**Chose:** `/api/analyses` runs the investigation synchronously and returns the
result in the same request.
**Rejected:** starting a Step Functions execution and having the frontend poll for
completion, as the spec's architecture implies for the real system.
**Why:** against frozen fixture data, the orchestrator completes in 1-2 seconds —
comfortably inside API Gateway's 29-second timeout, and far simpler to demo live
without a polling UI. This is explicitly a hackathon-demo simplification, not a
claim that it scales: a real Bedrock-agent-driven investigation will likely take
much longer than 2 seconds and will need the async path the architecture already
describes.
**Cost:** the deployed API doesn't yet match the architecture doc's own description
of itself. Flagged in `docs/KNOWN_LIMITATIONS.md` rather than silently diverging.

## Client-side portfolio calculator instead of waiting for a backend endpoint

**Chose:** port the finance engine to TypeScript (`frontend/src/lib/finance.ts`) and
compute portfolio metrics for an uploaded/edited CSV directly in the browser against
a bundled price-history snapshot.
**Rejected:** building a `/api/portfolio/parse` Lambda + S3 presigned upload flow
first.
**Why:** nothing is deployed yet, so a backend endpoint would be unusable for a
demo until deployment happens (which depends on hackathon AWS access). A
client-side calculator is fully real and interactive *today*, with no AWS
dependency, and directly closes the master spec's "users can upload a portfolio"
gap in the meantime.
**Cost:** two implementations of the same math now exist (Python and TypeScript).
They're cross-verified against the same hand-checked synthetic test values (see
`frontend/src/lib/finance.test.ts`), but a future change to one won't automatically
propagate to the other — a real maintenance cost, accepted deliberately and
documented in `docs/KNOWN_LIMITATIONS.md`.

## Lambda container images instead of zip deployments

**Chose:** `backend/Dockerfile.lambda`, built from the repo root, baking in
`data/fixtures/` and all heavy dependencies (pandas, numpy, scipy, networkx,
strands-agents).
**Rejected:** zip-based Lambda layers.
**Why:** this dependency set is too large and too native-extension-heavy (numpy,
scipy) to fit comfortably in Lambda's layer size limits without significant
splitting effort. A container image has a much higher size ceiling and was
confirmed to actually build and run the handler end-to-end locally with Docker —
proof the dependency set is a solved problem, not a theoretical one.
**Cost:** slower cold starts than a thin zip package, and the image must be rebuilt
and re-pushed to ECR on every deploy, which is slower than a zip upload during
iteration.

## Frozen fixture snapshot instead of live API calls during the demo

**Chose:** `scripts/build_demo_snapshot.py` pulls real data once and freezes it
under `data/fixtures/`; the demo runs against that snapshot, not live calls.
**Rejected:** calling Yahoo Finance / SEC EDGAR / Federal Register live during the
actual demo.
**Why:** Yahoo's chart API is unofficial, undocumented, and was observed returning
HTTP 429 under bursty unauthenticated requests during development — an unacceptable
risk for a timed demo in front of judges. A frozen, content-hashed snapshot is
reproducible and immune to a source being slow, rate-limited, or down at the wrong
moment.
**Cost:** the demo's "live" regulatory event and market data is only as current as
the last time someone ran the build script — currently 2026-11-11 — not truly live.
This is disclosed, not hidden, everywhere the frontend shows a date range.
