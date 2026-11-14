# Hackathon Day Runbook

The temporary AWS account for the PolyFinances 2026 AlphaForge AI Challenge is
issued Saturday (2026-11-14) at noon and deleted Monday (2026-11-16) — a narrow,
one-shot window. This is the ordered sequence to run in it, written so that window
is spent deploying and demoing, not debugging things that could have been checked
beforehand. Everything in "Pre-flight" below is already true as of this commit;
re-check it didn't drift before Saturday.

## Pre-flight (do before Saturday — already true today, verify it still is)

- [ ] `cd backend && source .venv/bin/activate && python3 -m pytest tests/ -q` → 76 passed
- [ ] `cd frontend && npm run test && npm run build` → 25 passed, build clean
- [ ] `cd infrastructure/cdk && npx cdk synth` → 4 stacks synthesize with no AWS credentials present
- [ ] GitHub Actions CI is green on `main` (badge at the top of `README.md`, or `gh run list --limit 1`)
- [ ] `python3 scripts/build_demo_snapshot.py` has been run recently enough that
      `data/fixtures/manifest.json`'s `built_at` is a date you're comfortable
      presenting live (refresh it the night before if not)
- [ ] `python3 scripts/run_rag_eval.py` still reports `hit_rate@3` at or above the
      floor in `docs/EVALUATION.md` (regression-tested by
      `backend/tests/evaluation/test_rag_eval.py`, but worth a manual glance)
- [ ] Decide who has hands on the keyboard for the deploy sequence below, and who's
      narrating/prepping the demo script in parallel — don't let one person block
      on the other

## Day-of sequence (ordered)

Each step names what to do if it fails, so a failure doesn't stall the whole
sequence — move to the fallback and come back if time allows.

### 1. Confirm Bedrock access and pick a model (5 min)

```bash
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?contains(modelId,'anthropic.claude')].modelId"
```

Set the actual enabled model ID — **do not assume `anthropic.claude-sonnet-4-5-20250929-v1:0` (today's default in `backend/src/riskripple/agents/definitions.py`) is available; it has never been confirmed on any real account.**

```bash
export BEDROCK_MODEL_ID="<whatever came back>"
```

**If this fails (access denied or no Claude model listed):** stop here, skip
straight to step 6 (frontend-only deploy) and run the demo on the deterministic
local-orchestrator path (already fully working, no Bedrock needed) rather than
burning the window retrying permissions.

### 2. Smoke-test one agent live, before deploying anything (10 min)

Don't deploy first and discover the agent loop doesn't work second. From a shell
with the hackathon account's credentials and `BEDROCK_MODEL_ID` set:

```bash
cd backend && source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'src')
from riskripple.agents.definitions import build_quant_analyst_agent
agent = build_quant_analyst_agent()
print(agent('Calculate the annualized volatility for SPY using the available price history.'))
"
```

**If this fails:** read the actual error (model access, IAM, tool-schema issue) —
don't guess. If it's not fixable in ~10 minutes, fall back to the local orchestrator
for the demo and keep debugging in the background; the deterministic path is a
complete, real fallback, not an empty one.

**If it works:** you've just confirmed what's been unverified this entire build.
Note what the model actually did (which tool, in what order) in case it's worth
mentioning to judges as a specific, checked claim rather than "it should work."

### 3. `cdk bootstrap` (one-time, ~3 min)

```bash
cd infrastructure/cdk
npx cdk bootstrap aws://<account-id>/us-east-1
```

### 4. Deploy storage first, alone (~3 min)

```bash
npx cdk deploy RiskRipple-Storage --require-approval never
```

Deploying storage alone first means a failure in the API/workflow stacks later
doesn't also take down the tables holding anything already written.

### 5. Deploy the rest (~8-12 min, container image build + push)

```bash
npx cdk deploy RiskRipple-Api RiskRipple-Ingestion RiskRipple-Workflow --require-approval never
```

This is the step most likely to surprise you — it's the first time the Lambda
container image is built and pushed in this account, even though it's been built
and run locally with Docker already (see `docs/KNOWN_LIMITATIONS.md`). If it fails
on the image build itself, that's a real regression to investigate; if it fails on
IAM/ECR permissions, that's an account-permissions problem, not a code problem —
don't spend more than ~10 minutes on it before falling back.

**If this fails:** the local orchestrator and frontend-against-fixture-data demo
still work with zero AWS dependency. You have a complete fallback; use it rather
than running out the clock here.

### 6. Smoke-test the deployed API (~5 min)

```bash
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/health
```

Then exercise one real `/api/analyses` call and confirm the response shape matches
what `frontend/src/types.ts` expects before pointing the frontend at it.

### 7. Point the frontend at the live API and redeploy (~5 min)

```bash
cd frontend
echo "VITE_API_BASE_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com/prod" > .env.production
npm run build
```

Deploy `dist/` via Amplify Hosting (drag-and-drop in the console is fastest for a
one-shot hackathon deploy — see `docs/AWS_DEPLOYMENT.md`).

**If this fails or there's no time left:** the frontend already works standalone
against the frozen fixture (`VITE_API_BASE_URL` unset) — that is a legitimate demo
path, not a degraded one, and it's the one that's actually been tested end to end.
Say so plainly rather than implying it's live when it isn't.

### 8. Final end-to-end check before judges see it (~5 min)

Click through all 7 frontend routes against whichever backend you ended up running
(live or fixture) — this is also the first real visual confirmation of the
rendered pages (see `docs/KNOWN_LIMITATIONS.md`: no one has done this yet). Do it
before judges do.

## If something breaks and there's no time to fix it

Say what's real plainly, per the project's own standard: "the finance engine, data
ingestion, exposure graph, and RAG retrieval are fully real and tested — N
automated tests passing [give the current number from the CI badge]. The live
Bedrock agent reasoning and the AWS deployment were confirmed today for the first
time against this hackathon's temporary account." That is an honest, still
genuinely strong claim, and it's exactly what `docs/KNOWN_LIMITATIONS.md` has said
throughout this build rather than only once something breaks live.

## Before the account is deleted (Monday)

See `docs/AWS_DEPLOYMENT.md`'s "Before the account is deleted" section — export
anything from DynamoDB/S3 worth keeping, then `cdk destroy --all` (tables/buckets
are `RemovalPolicy.RETAIN`, so destroy won't silently drop data — delete those
manually after confirming the export).
