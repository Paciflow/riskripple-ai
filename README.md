# RiskRipple AI

*From global events to smarter investment decisions.*

An AWS-powered agentic investment intelligence platform built for the **PolyFinances
Datathon 2026 — AlphaForge AI Challenge** (with Banque Nationale, supported by AWS).
It analyzes how geopolitical events, sanctions, tariffs, and export restrictions
ripple into financial assets and investment portfolios, combining a real,
deterministic quantitative finance engine with retrieval-grounded, persona-aware AI
interpretation.

**Simulation only.** All portfolios and events in the demo are fictional. Nothing
here executes real trades or gives personalized financial advice.

## What's real here

Everything in this repo is either (a) a deterministic calculation you can verify by
hand, (b) data pulled live from a named public source and frozen for reproducibility,
or (c) explicitly labeled as untested/blocked, with the reason why. See
[docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the current honest list —
read it before a demo.

- A full quantitative finance package (returns, volatility, correlation, max
  drawdown, Sharpe, concentration, stress testing), unit-tested against
  hand-verified synthetic values.
- Real data ingestion from OFAC, Global Affairs Canada, the Federal Register, FRED,
  SEC EDGAR, and Yahoo Finance — frozen into a reproducible demo snapshot in
  `data/fixtures/`.
- A company exposure graph whose supplier-relationship edges are extracted from
  literal sentences in real SEC 10-K filings (verified against NVIDIA/AMD/Intel).
- Five Strands Agents (AWS's agent SDK) with Bedrock-backed tool definitions, wired
  to the finance/RAG/graph layers above — **structurally verified, live LLM
  invocation blocked on the current dev AWS account** (see limitations doc).
- A working end-to-end investigation pipeline that runs without any AWS dependency,
  producing a real, cited report from real data.
- AWS CDK infrastructure (storage, API, ingestion, workflow) that synthesizes
  cleanly and whose Lambda container image has been built and run locally end to
  end — **not yet deployed** (blocked by this account's IAM permissions, not a code
  issue).
- A React/Vite/Tailwind dashboard driven by that same real investigation output,
  plus a live, client-side portfolio calculator (CSV upload or manual weights)
  that recomputes real metrics in the browser against a bundled price-history
  snapshot — no backend required (see `frontend/README.md`).

## Repository layout

```
riskripple-ai/
├── frontend/              React + Vite + TypeScript + Tailwind dashboard
├── backend/
│   └── src/riskripple/
│       ├── finance/       Deterministic quant engine (no AI, no AWS)
│       ├── ingestion/     Real public-data adapters (OFAC, SEC, FRED, ...)
│       ├── rag/           Chunking + retrieval (local + Bedrock KB adapter)
│       ├── graph/         Company exposure graph (NetworkX)
│       ├── personas/      Prudent/Équilibré/Audacieux policy engine
│       ├── tools/         Strands @tool wrappers per agent
│       ├── agents/        strands.Agent assembly (Bedrock-backed)
│       ├── workflows/     Deterministic local orchestrator (no AWS needed)
│       ├── storage/       DynamoDB / in-memory storage interface
│       ├── api/           Lambda handlers
│       └── schemas/       Shared Pydantic domain models
├── infrastructure/cdk/    AWS CDK (TypeScript): storage, api, ingestion, workflow stacks
├── data/fixtures/         Frozen, reproducible real-data snapshot for the demo
├── scripts/               Snapshot builder + demo runner scripts
└── docs/                  Architecture, data sources, limitations, demo script
```

## Quickstart (no AWS required)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m pytest tests -q                       # 73 tests, all local/offline-safe

cd ..
python scripts/build_demo_snapshot.py           # refresh the real data snapshot (optional, already committed)
python scripts/run_full_investigation_demo.py   # full pipeline, real data, no AWS
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Deploying to AWS

```bash
cd infrastructure/cdk
npm install
npx cdk synth          # validated locally; all 4 stacks synthesize cleanly
npx cdk deploy --all   # requires CloudFormation/IAM permissions -- see docs/AWS_DEPLOYMENT.md
```

Before deploying for the hackathon demo: confirm `bedrock:InvokeModel` access and set
`BEDROCK_MODEL_ID` to a model actually enabled in that account's region (see
[docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)).

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design and AWS service usage
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — every source, with URL, license, and caveats
- [docs/INGESTION_PIPELINE.md](docs/INGESTION_PIPELINE.md) — how a source becomes a frozen, hashed fixture
- [docs/RAG_PIPELINE.md](docs/RAG_PIPELINE.md) — chunking, retrieval, citation enforcement
- [docs/FINANCIAL_MODELS.md](docs/FINANCIAL_MODELS.md) — formulas and conventions
- [docs/AGENTS.md](docs/AGENTS.md) — agent responsibilities, tools, prompts
- [docs/EVALUATION.md](docs/EVALUATION.md) — RAG retrieval benchmark, with real results
- [docs/TRADEOFFS.md](docs/TRADEOFFS.md) — design decisions and what was rejected, with why
- [docs/COST_ESTIMATE.md](docs/COST_ESTIMATE.md) — cited AWS cost estimate (hackathon scale and beyond)
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — the 5-minute walkthrough
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) — what's unverified and why
