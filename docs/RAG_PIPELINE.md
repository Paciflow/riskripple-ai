# RAG Pipeline

How a source document becomes a cited piece of evidence in an investigation report.
See `docs/EVALUATION.md` for a measured benchmark of how well the retrieval step
actually works, and `docs/KNOWN_LIMITATIONS.md` for what's unverified.

## Stages

```
raw document text  →  chunk_document()  →  Retriever.retrieve()  →  build_evidence_context()  →  citation
   (ingestion)          (chunking.py)        (retrieval.py)           (retrieval.py)              (SourceMetadata)
```

### 1. Chunking (`backend/src/riskripple/rag/chunking.py`)

`chunk_document(document_id, text, title=, source_url=, chunk_tokens=1000,
overlap_tokens=150)` is structure-aware and token-based, not character-based:

- Splits on blank-line paragraph boundaries first, and packs whole paragraphs into
  a chunk up to `chunk_tokens` (via `tiktoken`'s `cl100k_base` encoding — chosen so
  chunk size is meaningful regardless of markup density, not because this project
  calls the OpenAI API).
- Carries `overlap_tokens` of trailing context into the next chunk, so a fact
  sitting across a chunk boundary isn't lost to either side.
- Falls back to a hard token-boundary split only for a single paragraph that alone
  exceeds `chunk_tokens` (verified with a 5,000-word single-paragraph synthetic
  test — real filing text wraps in paragraphs long before that).
- Every `DocumentChunk` carries a `content_hash` (used for deduplication) and
  optional `title`/`source_url`/`jurisdiction`/`related_entities` metadata that
  flows through to the citation.

### 2. Retrieval (`backend/src/riskripple/rag/retrieval.py`)

Two interchangeable retrievers, same call shape (`retrieve(query, top_k=,
metadata_filter=) -> list[RetrievedChunk]`):

- **`LocalLexicalRetriever`** — TF-IDF cosine similarity, pure Python, zero AWS
  dependency. This is what's actually been run and evaluated
  (`docs/EVALUATION.md`: 34 grounded queries, 0.88 hit@3 at the recommended
  relevance threshold). Every score is a literal term-overlap computation, which
  made it possible to debug citation accuracy by hand while building this.
- **`BedrockKnowledgeBaseRetriever`** — the production path, backed by Bedrock
  Knowledge Bases + a managed vector store. **Confirmed working live** on the
  hackathon account (2026-11-14) against a real Amazon S3 Vectors-backed Knowledge
  Base with the real 10-Ks and Federal Register documents indexed — see
  `docs/KNOWLEDGE_BASE.md` for the real deployment and a real semantic-match example
  it produced that the lexical retriever below cannot. Required zero code changes.
  Not yet wired into the active tool layer (still an explicit, undecided tradeoff,
  not an oversight — see `docs/KNOWLEDGE_BASE.md`'s last section).

`metadata_filter` lets a caller scope retrieval to a specific document (e.g.
`{"document_id": "NVDA_10K"}`), which is how `retrieve_company_filings` in
`tools/regulatory_tools.py` actually uses it — scoped to a known company rather
than searching the whole corpus, avoiding cross-company false matches.

**`min_score`** (added after the evaluation benchmark surfaced a real gap): the
retriever has no relevance floor by default (`min_score=0.0`, for backward
compatibility), meaning *any* nonzero term overlap counts as a result. Measured
against the real demo corpus, genuinely unrelated queries scored at most ~0.06
while true matches started above ~0.23 — so any caller asserting "no relevant
evidence found" (rather than just "the list is nonempty") should pass
`min_score=0.15`. See `docs/EVALUATION.md` for the full tradeoff data (raising the
threshold trades a small amount of recall for a large gain in negative-query
precision).

### 3. Evidence context and citations (`build_evidence_context`)

Deduplicates retrieved chunks by `content_hash`, then formats them with inline
citation markers:

```
[1] NVDA 10-K (2026-02-25) (https://www.sec.gov/Archives/edgar/data/.../nvda-20260125.htm)
<chunk text>

---

[2] ...
```

This is the exact text handed to an agent's prompt as grounding context. The
numbered markers are what `validate_report_citations`
(`tools/persona_tools.py`) checks against before a report is allowed to save —
every citation in a final `InvestigationReport` must trace back to a real
`[n]` marker from an actual retrieved chunk, not a number the model invented.
This is the concrete enforcement behind the master spec's "never fabricate a
citation" requirement; it doesn't depend on the model behaving, since it's a
rejection check that runs regardless of what the model wrote.

## What's NOT semantic here

`LocalLexicalRetriever` cannot match a paraphrase that shares no vocabulary with
the source. "chips that can't be sold to China" will not find a passage that says
"restricted destinations" without the word "China" or "chips" appearing in it. This
is a real, known gap versus the production (Bedrock KB, embedding-based) path —
documented, not hidden, in `docs/TRADEOFFS.md` and `docs/KNOWN_LIMITATIONS.md`.
