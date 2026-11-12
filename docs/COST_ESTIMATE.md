# Cost Estimate

**This is an estimate, not a bill.** Nothing has been deployed yet (see
`docs/KNOWN_LIMITATIONS.md`), so there is no real AWS invoice to report. Every rate
below is cited to a source and date; where sources disagreed or a live pricing page
didn't return a clean table when checked, that's stated explicitly rather than
smoothed over. Verify against the [AWS Pricing Calculator](https://calculator.aws/)
before treating this as a budget commitment.

## Rates used (US East, N. Virginia)

| Service | Rate | Source | Checked |
|---|---|---|---|
| Lambda (x86) | $0.20 / 1M requests + $0.0000166667 / GB-second | Consistent across multiple third-party pricing trackers (eon.io, wiz.io, dash0.com) citing the AWS Lambda pricing page; AWS's own page wasn't re-verified line-by-line in this pass. | 2026-11-11 |
| DynamoDB on-demand | $0.625 / 1M write request units, $0.125 / 1M read request units, $0.25 / GB-month storage | A direct fetch of `aws.amazon.com/dynamodb/pricing/on-demand/` on 2026-11-11 returned these figures from the page's worked examples (the main rate table itself didn't render in the fetch). Two independent third-party trackers agree on these as the post-late-2024 rates; a few others still list the older, roughly 2x figures ($1.25 / $0.25) — if you're reading this near a pricing change, check the live page. | 2026-11-11 |
| Bedrock, Claude Sonnet (current gen) | $3.00 / 1M input tokens, $15.00 / 1M output tokens | AWS's own Bedrock pricing page, per search result snippet: Claude Sonnet 5's promotional launch rate ($2/$10) was in effect only through 2026-08-31; the standard rate since is $3/$15. | 2026-11-11 |
| S3 Standard storage | ~$0.023 / GB-month (first 50 TB) | **Not reconfirmed against the live page this pass** — the fetch attempt returned an empty pricing table. This is the long-standing published S3 Standard rate from general knowledge, not a figure pulled fresh today. At this project's storage scale (tens of MB), the exact rate barely moves the total — but don't cite this number elsewhere without checking `aws.amazon.com/s3/pricing/` directly. | Not independently verified 2026-11-11 |
| API Gateway (REST) | $3.50 / 1M requests (first 333M/month) | Long-standing published rate, not reconfirmed this pass for the same reason as S3. | Not independently verified 2026-11-11 |

## Estimate 1 — hackathon demo weekend (what this project will actually cost)

Assumptions, stated so you can redo the math if they're wrong:
- ~30 judge-facing investigation runs over the demo window (generous — likely far
  fewer in practice).
- Each run: 1 Lambda invocation (the `analyses` handler, synchronous per
  `docs/KNOWN_LIMITATIONS.md`), ~2 seconds at 1024 MB (2 GB-seconds), plus ~4
  DynamoDB writes and ~6 reads (analysis + audit events + portfolio lookup).
- If the live Bedrock agent path is confirmed working and used for all 30 runs: 5
  agents × ~3,000 input + ~600 output tokens each, per run (a deliberately generous
  per-agent budget — the actual tool-result context is usually smaller).
- Daily EventBridge ingestion Lambda: 3 runs (Sat/Sun/Mon) × ~10 GB-seconds each
  (fetching + parsing OFAC/GAC/Federal Register/FRED/SEC/Yahoo).
- S3: the entire `data/fixtures/` snapshot (a few hundred MB) plus report output,
  stored for the ~3-day event window.

| Line item | Calculation | Cost |
|---|---|---|
| Lambda requests | 33 invocations × $0.20/1M | ~$0.00001 |
| Lambda compute | (30×2 + 3×10) = 90 GB-seconds × $0.0000166667 | ~$0.0015 |
| DynamoDB writes | 30×4 = 120 WRU × $0.625/1M | ~$0.0001 |
| DynamoDB reads | 30×6 = 180 RRU × $0.125/1M | ~$0.00002 |
| DynamoDB storage | <0.1 GB for 3 days × $0.25/GB-month (prorated) | ~$0.001 |
| Bedrock tokens (if live) | 30 runs × 5 agents × (3,000×$3 + 600×$15)/1M | **~$2.25** |
| S3 storage | ~0.3 GB for 3 days, prorated | ~$0.0007 |
| API Gateway | 33 requests × $3.50/1M | ~$0.0001 |
| **Total** | | **≈ $2.25-$2.30**, essentially all of it Bedrock tokens if the live path is used |

**Bottom line: this costs a few dollars for the entire hackathon weekend, dominated
almost entirely by Bedrock token usage if the live agent path works — everything
else is fractions of a cent at this scale.** The free tiers for Lambda (1M
requests/month) and DynamoDB (25 GB + throughput) likely cover this run entirely on
their own, before any paid-rate calculation above even applies.

## Estimate 2 — sustained production use (illustrative only)

Not something this project is being built toward in the datathon window, but useful
context for "what if this ran for real": at 10,000 investigations/month with the
same per-run assumptions above, Bedrock tokens alone would be roughly
10,000 × 5 × (3,000×$3 + 600×$15)/1M ≈ **$750/month**, again dwarfing Lambda/DynamoDB/S3
(each still in the single-digit dollars at that volume). The first real optimization
lever at that scale would be reducing per-agent prompt/context size or batching
Bedrock inference (AWS states batch inference runs at a 50% discount versus
on-demand, per the same pricing page), not infrastructure cost.

## What's NOT included

- Bedrock Knowledge Base / OpenSearch Serverless vector store costs — not
  provisioned in this build (see `docs/KNOWN_LIMITATIONS.md`), so there's no basis
  to estimate it without guessing at an index size; OpenSearch Serverless bills by
  OCU-hour and is the more likely dominant cost if/when a real Knowledge Base is
  provisioned.
- Data transfer costs — negligible at this scale, not modeled.
- CloudWatch Logs ingestion/storage — negligible at this log volume, not modeled.
- Amplify Hosting for the frontend — free tier (1,000 build minutes, 15 GB served)
  comfortably covers a hackathon demo; not separately priced here.
