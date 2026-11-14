# Bedrock Knowledge Base (live, real vectorization/indexing)

Deployed for real on the hackathon account (`637423589728`, `us-east-1`) on
2026-11-14, after `AdministratorAccess` and live `bedrock:InvokeModel` access were
confirmed (see `docs/KNOWN_LIMITATIONS.md`). This is the production RAG retrieval
path referenced in `docs/RAG_PIPELINE.md` and implemented (before this, untested)
as `rag/retrieval.py::BedrockKnowledgeBaseRetriever`.

## What's deployed

- **Vector storage: Amazon S3 Vectors** (not OpenSearch Serverless) -- a native S3
  vector bucket/index, chosen because it needed no cluster or security-policy setup
  and this account could create one directly via `aws s3vectors`.
  - Bucket: `riskripple-vectors-637423589728`
  - Index: `riskripple-documents` (1024-dim, float32, cosine distance)
- **Embedding model**: `amazon.titan-embed-text-v2:0`, 1024 dimensions.
- **Knowledge Base**: id `SSYDB0BFCH`, type `VECTOR`, storage type `S3_VECTORS`.
- **Data source**: id `YYNL3HJFCR`, S3 prefix
  `s3://riskripple-data-637423589728-us-east-1/rag/documents/` -- the real 3 held
  companies' 10-Ks (`NVDA_10K.txt`, `AMD_10K.txt`, `INTC_10K.txt`) plus all 20 real
  Federal Register documents (as `fedreg_<document_number>.txt`, title+abstract).
  `FIXED_SIZE` chunking, 250 tokens, 15% overlap.
- **IAM role**: `riskripple-kb-role` -- scoped to exactly 3 things: invoke the Titan
  embedding model, read the data bucket, read/write the vector bucket/index. Trust
  policy restricts `AssumeRole` to `bedrock.amazonaws.com` for this account's
  knowledge bases only.

## A real bug hit and fixed while standing this up

The first ingestion attempt (500-token chunks) failed on 10 of 23 documents with
`Filterable metadata must have at most 2048 bytes`. Halving the chunk size to 250
tokens only reduced the failure count (9 of 23) -- the real cause, confirmed by
inspecting a stored vector directly (`aws s3vectors list-vectors --return-metadata`),
was that the S3 Vectors index was created without `nonFilterableMetadataKeys`, so
Bedrock's own `AMAZON_BEDROCK_TEXT` (the chunk text) and `AMAZON_BEDROCK_METADATA`
keys counted against the 2KB *filterable* metadata cap by default. Recreating the
index with both keys marked non-filterable fixed it completely: 23/23 documents,
0 failures, on the next ingestion run.

## Proof it actually works (not just "deployed")

```
$ aws bedrock-agent-runtime retrieve --knowledge-base-id SSYDB0BFCH \
    --retrieval-query '{"text": "reliance on a sole supplier for advanced chip manufacturing in Taiwan"}' ...
```
returned AMD's real 10-K passage about relying on TSMC for sub-7nm wafer production
(score 0.75) -- **without the query containing the words "TSMC" or "Taiwan
Semiconductor"**. This is a genuine semantic match the local `LocalLexicalRetriever`
(TF-IDF, term-overlap only) cannot make; see "What's NOT semantic here" in
`docs/RAG_PIPELINE.md` for that documented gap. `BedrockKnowledgeBaseRetriever`
required zero code changes to work against this live KB on the first try.

## Not yet wired into the active pipeline

`regulatory_tools.summarize_event_evidence` still uses `LocalLexicalRetriever`
directly. Swapping in `BedrockKnowledgeBaseRetriever` there would make that tool
always require network + AWS credentials, losing the "runs anywhere, no AWS
dependency" property the local path has -- a real tradeoff, not just a wiring change,
left as an explicit decision rather than made silently.

## Teardown

The entire hackathon account is destroyed automatically per the event schedule
(Monday 2026-11-16, 13:59) -- no manual cleanup of these specific resources is
required for cost reasons. If recreating this setup elsewhere: delete the data
source, knowledge base, S3 Vectors index, S3 Vectors bucket, and `riskripple-kb-role`
IAM role, in that order.
