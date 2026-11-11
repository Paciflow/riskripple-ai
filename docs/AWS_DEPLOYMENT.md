# AWS Deployment

## Prerequisites

- AWS CLI configured with credentials for the target account
- Node.js 18+, Docker (for building the Lambda container image), AWS CDK
  (`npm install -g aws-cdk`, or use `npx cdk` from `infrastructure/cdk/`)
- Confirm `bedrock:InvokeModel` access and an enabled foundation model in the
  target account's region: `aws bedrock list-foundation-models --region <region>`.
  Set `BEDROCK_MODEL_ID` in `infrastructure/cdk/lib/workflow-stack.ts` /
  `api-stack.ts` environment variables (or override via
  `backend/src/riskripple/agents/definitions.py`'s `BEDROCK_MODEL_ID` env var)
  accordingly. **Do not assume a specific Claude/Nova model ID is available** —
  this has not been verified on any account yet.

## Deploy

```bash
cd infrastructure/cdk
npm install
npx cdk bootstrap aws://<account-id>/<region>   # once per account/region
npx cdk synth                                    # validate first
npx cdk deploy --all
```

This deploys 4 stacks: `RiskRipple-Storage`, `RiskRipple-Api`,
`RiskRipple-Ingestion`, `RiskRipple-Workflow`. The API stack and workflow stack
each build a Docker image from `backend/Dockerfile.lambda` — the build context is
the **repo root**, not `backend/`, because the frozen demo data snapshot
(`data/fixtures/`) is baked into the image intentionally (see the Dockerfile's own
comment for why).

**Verified locally:** `cdk synth` succeeds for all 4 stacks, and the exact
Dockerfile has been built and run with Docker directly, including a full
end-to-end invocation of the `analyses` handler producing a real investigation
result from the baked-in data. **Not yet verified:** an actual `cdk deploy` — the
personal AWS account used during development has `cloudformation:ListStacks`
(and by extension, CDK deploy) access-denied. This is an IAM/account limitation,
not a code issue.

## Frontend

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/prod" > .env.production
npm run build
```

Deploy `frontend/dist/` via AWS Amplify Hosting (connect the repo, or drag-and-drop
the build output in the Amplify console for a quick hackathon deploy).

## Teardown (end of hackathon)

```bash
cd infrastructure/cdk
npx cdk destroy --all
```

S3 buckets and DynamoDB tables are set to `RemovalPolicy.RETAIN` deliberately (see
`storage-stack.ts`) so an accidental `cdk destroy` doesn't silently delete
investigation history — delete those manually after confirming you've exported
anything worth keeping, since the hackathon's temporary account is deleted after
the event (per the workshop's own Nov 14–16 window).

## Before the account is deleted

- Export any investigation reports and the audit trail you want to keep (they're
  in S3/DynamoDB, not just the frontend).
- Commit the final state of `data/fixtures/` if you refreshed it against the
  hackathon account's own ingestion run.
