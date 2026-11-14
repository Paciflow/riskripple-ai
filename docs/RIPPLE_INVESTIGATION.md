# Ripple Investigation Agent

Added to answer a real gap: `alerts/relevance.py::check_relevance` only ever checks
two fixed lists (the portfolio's own tickers, and 7 hardcoded supplier aliases in
`graph/company_graph.py`). A real event naming something not on either list --
a material, an equipment vendor, an unfamiliar entity -- produced nothing, no matter
how relevant it actually was. This module goes looking *beyond* those fixed lists,
without weakening the "never invent a relationship" rule that governs everything
else in this codebase.

See `docs/ALERT_PIPELINE.md` for where this sits in the alert pipeline, and
`docs/KNOWN_LIMITATIONS.md` for live-Bedrock status.

## Design: two trust boundaries stay fixed, one new step goes in between

```
check_relevance()  →  run_ripple_investigation()  →  run_investigation()
(deterministic,         (NEW: dynamic discovery,        (deterministic financial
 unchanged --             bounded, evidence-gated)        math, unchanged --
 "is this real and                                        the agent never
 does it touch                                             computes a number)
 something known")
```

The new step never decides *whether* an alert fires -- `check_relevance` still does
that. It only adds extra findings to the resulting `InvestigationReport`, each
explicitly labeled with an `EvidenceStatus`:

- `verified_fact` -- directly supported by a tool's returned evidence or a
  deterministic calculation.
- `evidence_supported_hypothesis` -- a plausible mechanism with partial real evidence
  (a literal textual match, not yet a quantified financial impact).
- `unverified_possibility` -- worth investigating, no supporting evidence found. This
  is reported, not dropped -- "no established link" is itself a real, useful result.
- `simulated_outcome` -- explicit assumption-based output, never the model's own
  invented number.

A verified relationship (e.g. a real 10-K disclosure) does not by itself prove a
financial outcome; that distinction is why a hypothesis never gets upgraded past
`evidence_supported_hypothesis` without going through the existing deterministic
math in `run_investigation`.

## Two modes

### Deterministic fallback (`investigation/loop.py::run_ripple_investigation`) -- the default

No LLM. A fixed, generic two-round question sequence:

1. `propose_candidate_entities` (`tools/research_tools.py`) -- a regex proper-noun
   extractor over the event's title/abstract, explicitly a noisy heuristic, not NER.
   Candidates already covered by `check_relevance`'s matches are excluded.
2. For each new candidate (bounded by `max_hypotheses`, default 3),
   `search_filings_fulltext` checks ALL portfolio holdings' real 10-K text for a
   literal mention -- not just the company the original match was about, which is
   what also catches "could another holding be exposed the same way" without any
   hardcoded competitor map.

Every step is recorded as an `InvestigationStep` (question, why it was relevant,
tools consulted, evidence found, result status, follow-ups) -- this is the audit
trail rendered in the report, not raw model reasoning.

**Verified against real data** (`tests/investigation/test_loop.py`,
`scripts/run_alert_scan.py`): running this against the real demo fixture set found a
genuine, previously-undiscoverable connection -- Intel's actual 10-K disclosure about
sourcing "rare earth elements" concentrated in China -- that `check_relevance`'s fixed
alias list could never have surfaced, because "rare earth elements" was never in
`KNOWN_SUPPLIER_ALIASES`. It also correctly reported "unverified" (not fabricated) for
a genuinely unconnected candidate (a synthetic "Argentina Lithium Triangle" test case
with no real filing match).

**A real bug this surfaced and the fix**: an early version matched "United States"
as a candidate and found it trivially present in all 3 filings' raw XBRL boilerplate
-- a technically-literal but meaningless match (every U.S. company's 10-K says
"United States" constantly). Fixed with a small, explicit denylist
(`_GENERIC_NOISE_CANDIDATES` in `research_tools.py`) for maximally-common phrases with
no differentiating signal -- same curated-list philosophy as `KNOWN_SUPPLIER_ALIASES`,
not a general informativeness model. Regression-tested
(`test_propose_candidate_entities_excludes_generic_boilerplate`).

### Agent-driven (`agents/definitions.py::build_ripple_investigator_agent`) -- UNTESTED LIVE

A Strands/Bedrock agent with the same research tools plus the existing
regulatory/exposure tools, given the same evidence-classification instructions
directly in its system prompt. `bedrock:InvokeModel` has been access-denied on every
AWS account checked so far (`scripts/verify_bedrock_agent.py` -- see
`docs/KNOWN_LIMITATIONS.md`), so this has never actually run. The deterministic
fallback above is the default and does not depend on this working.

## Bounds (enforced in Python, not left to model self-discipline)

- `max_rounds` (default 2), `max_hypotheses` (default 3) in
  `run_ripple_investigation`'s signature -- tighter than a fuller recursive budget by
  design, to keep a live agent call's cost/latency/output size bounded during a demo.
- Gated behind `RISKRIPPLE_ENABLE_RIPPLE_INVESTIGATION` (default on) in
  `alerts/pipeline.py`, so it can be disabled instantly if it ever needs to be,
  falling back to exactly the original alert pipeline.

## What's deliberately out of scope this pass

Bedrock Knowledge Bases, Step Functions orchestration of this loop, and a general
news API (so a non-filing event like a press story can be detected at all) -- see
`docs/KNOWN_LIMITATIONS.md` and `docs/TRADEOFFS.md`.
