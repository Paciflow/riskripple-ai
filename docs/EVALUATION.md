# RAG Retrieval Evaluation

Master spec section 16.2 calls for a 30-50 question retrieval benchmark. This is it:
34 hand-written queries, each grounded in content actually present in the demo
fixtures (grep-confirmed against the real 10-K text, or read directly from the real
Federal Register abstracts — nothing here is invented). Code:
[`backend/src/riskripple/evaluation/rag_eval.py`](../backend/src/riskripple/evaluation/rag_eval.py).
Run it yourself:

```bash
cd backend && source .venv/bin/activate && cd ..
python3 scripts/run_rag_eval.py
```

Full machine-readable output (every query, expected vs. retrieved document, per-case
pass/fail) is written to
[`data/evaluation/rag_eval_results.json`](../data/evaluation/rag_eval_results.json)
on every run — the numbers below are from an actual run, not hand-typed.

## Corpus

180 chunks: the 3 demo 10-Ks (NVDA/AMD/INTC) plus all 20 real Federal Register BIS
documents in the demo snapshot, chunked with the same `chunk_document` function the
rest of the system uses. Retrieval is `LocalLexicalRetriever` (TF-IDF cosine
similarity) — the Bedrock Knowledge Base path is untested (see
`docs/KNOWN_LIMITATIONS.md`), so this benchmark only evaluates the lexical fallback
that's actually been run.

## Question categories

| Category | n | What it tests |
|---|---|---|
| `federal_register_unique` | 15 | One query per Federal Register document whose topic is distinct from the others (paraphrased, not copied from the title). |
| `entity_list_generic` | 1 | A deliberately generic query ("additions to the Entity List") against 5 documents that share near-identical boilerplate titles — any of the 5 counts as correct. |
| `entity_list_disambiguated` | 5 | The same 5 documents, but queried with the specific entity counts/countries from each one's abstract (e.g. "140 entities... Japan South Korea Singapore"), to test whether enough specific vocabulary can disambiguate within a family of similar documents. |
| `filing_scoped` | 9 | 3 queries per company (NVDA/AMD/INTC), scoped via `metadata_filter={"document_id": ...}` the way `retrieve_company_filings` actually scopes retrieval, targeting real passages confirmed by grep (e.g. NVDA is the only filing mentioning "SK Hynix"; INTC mentions "foundry" 51 times vs. 5-11 for the others). |
| `negative_control` | 4 | Queries about topics with zero overlap with anything ingested (sourdough baking, fantasy football, solar panels, backpacking), to check the retriever doesn't force a confident-looking match out of nothing. |

## Results

Two configurations, both from the same run:

| min_score | hit@1 | hit@3 | MRR | keyword_accuracy |
|---|---|---|---|---|
| 0.0 (current default) | 0.85 | 0.88 | 0.86 | 0.94 |
| 0.15 (recommended) | 0.88 | 0.91 | 0.89 | 1.00 |

By category (`min_score=0.0`):

| Category | n | hit@1 | hit@3 |
|---|---|---|---|
| federal_register_unique | 15 | 1.00 | 1.00 |
| entity_list_generic | 1 | 1.00 | 1.00 |
| entity_list_disambiguated | 5 | 0.80 | 1.00 |
| filing_scoped | 9 | 1.00 | 1.00 |
| negative_control | 4 | 0.00 | 0.00 |

## What this found, and what was fixed

**Found and fixed:** `LocalLexicalRetriever`'s tokenizer didn't filter stopwords.
Against a large real corpus, this alone wasn't enough to explain the negative-control
failures (see below), but it was a real bug (common function words inflate cosine
similarity for unrelated queries) and is now fixed in
[`backend/src/riskripple/rag/retrieval.py`](../backend/src/riskripple/rag/retrieval.py)
with a unit test.

**Found, not silently hidden, documented as a tradeoff:** even after the stopword fix,
all 4 negative-control queries still returned confident-looking top-3 hits at
`min_score=0.0` (scores 0.011-0.057) — because each query shares at least one
ordinary content word with 10-K boilerplate (e.g. "costs," "strategy," "capacity")
and the retriever has no minimum-relevance floor; any nonzero overlap counts as a
result. True matches in this corpus scored 0.23+ at rank 1. Based on that gap, a
`min_score=0.15` parameter was added to `retrieve()` (default `0.0`, so no existing
caller's behavior changes silently) and documented in its docstring as the
recommended value for any caller that needs to say "no relevant evidence found"
(e.g. before an agent asserts a sanctions match or a supplier link) rather than
treating "the list wasn't empty" as "the list was relevant."

**The tradeoff, honestly:** raising the threshold to 0.15 fixes all 4 negative
controls but drops 2 of the 9 `filing_scoped` hits to empty (0.08 and 0.11 — in both
cases the *correct document* was still found at `min_score=0.0`, just a passage that
didn't contain the exact expected keyword) and 1 more borderline case (0.126). This
benchmark does not recommend blindly hardcoding 0.15 everywhere — it recommends
measuring the gap for your own queries before picking a threshold, which is exactly
what this benchmark was built to let you do again after any future chunking,
corpus, or tokenizer change.

**entity_list_disambiguated (0.80 hit@1, 1.00 hit@3):** one of the 5 disambiguated
queries ranked its correct document 2nd rather than 1st — expected, given 5
documents sharing most of their vocabulary ("Entity List," "Bureau of Industry and
Security," "Export Administration Regulations"); the specific entity counts and
countries in the query still pulled the right document into the top 3 every time.

## What this does not test

- The Bedrock Knowledge Base retriever (semantic/embedding-based) — untested, no
  live Bedrock access (see `docs/KNOWN_LIMITATIONS.md`).
- Answer generation/synthesis quality — this benchmark only scores which chunks get
  retrieved, not what an LLM would do with them (that path is also untested live,
  for the same reason).
- The OFAC/GAC sanctions lists or FRED macro series — those aren't narrative text
  and go through `search_sanctions_records`/direct lookup rather than this RAG path.

## Regression test

`backend/tests/evaluation/test_rag_eval.py` runs this same benchmark as part of the
normal test suite and asserts a floor (`hit_rate@3 >= 0.85`, `MRR >= 0.8` at
`min_score=0.0`; both `negative_control` and `federal_register_unique` at
`hit_rate@1 == 1.0` for `min_score=0.15`) so a future chunking or tokenizer change
that regresses retrieval quality fails CI rather than being noticed only by eyeballing
a demo.
