# Architecture

## System diagram

```mermaid
flowchart TD
    subgraph Sources["Public Data Sources"]
        OFAC[OFAC SDN List]
        GAC[Global Affairs Canada]
        FEDREG[Federal Register / BIS]
        FRED[FRED]
        SEC[SEC EDGAR]
        YF[Yahoo Finance]
    end

    subgraph Ingestion["Ingestion (EventBridge-scheduled Lambda)"]
        ING[ingest.handler]
    end

    subgraph Storage["Storage"]
        S3[(S3 Data Lake\nraw/ processed/ rag/ reports/)]
        DDB[(DynamoDB\nportfolios, events, analyses, audit)]
    end

    subgraph RAG["RAG Layer"]
        CHUNK[Chunking\ntiktoken, structure-aware]
        RETR[Retrieval\nlocal TF-IDF or Bedrock KB]
    end

    subgraph Agents["Strands Agents (Bedrock-backed)"]
        A1[Regulatory Watchdog]
        A2[Regulatory Investigator]
        A3[Exposure Mapper]
        A4[Quant Analyst]
        A5[Persona / Reporting]
    end

    subgraph Compute["Deterministic Engines"]
        FIN[Finance Engine\npandas/numpy/scipy]
        GRAPH[Exposure Graph\nNetworkX]
        PERS[Persona Policy Engine]
    end

    subgraph Orchestration["Orchestration"]
        SFN[Step Functions\n(currently: one Lambda task,\nsee workflow-stack.ts docstring)]
    end

    subgraph API["API"]
        APIGW[API Gateway]
        LAMBDA[Lambda: health, analyses]
    end

    FE[React Dashboard\nAmplify / Vite]

    Sources --> ING --> S3
    S3 --> CHUNK --> RETR
    DDB <--> LAMBDA
    S3 <--> LAMBDA
    A1 --> A2 --> A3 --> A4 --> A5
    A2 <-->|retrieve| RETR
    A3 <-->|traverse| GRAPH
    A4 <-->|calculate| FIN
    A5 <-->|evaluate| PERS
    SFN --> A1
    LAMBDA --> SFN
    APIGW --> LAMBDA
    FE --> APIGW
```

## Why these services, specifically

| Service | Why | Status |
|---|---|---|
| **S3** | Data lake for raw/processed/RAG documents and reports; cheap, durable, versioned | CDK written, synth passes |
| **DynamoDB** | Structured entity state (portfolios, events, analyses, audit) with GSIs for the actual access patterns used (by-portfolio, by-jurisdiction, by-analysis) | CDK written, synth passes |
| **Lambda (container image)** | Heavy scientific Python stack (pandas/numpy/scipy/networkx/strands-agents) exceeds what a zip layer handles reliably; a container image supports it cleanly | Built and run locally end to end |
| **API Gateway** | REST front door, CORS, request validation | CDK written, synth passes |
| **Step Functions** | Async orchestration, retry/catch around the investigation task, SNS notification on completion | CDK written, synth passes; see `workflow-stack.ts` docstring for why it's currently 1 task, not 13 |
| **EventBridge** | Scheduled daily ingestion refresh | CDK written, synth passes |
| **Bedrock (Agents + Knowledge Bases)** | The actual agentic reasoning and retrieval layer | **Access-denied on dev account** — code is real and structurally verified, live invocation unverified |
| **SNS** | Analysis-completion notification | CDK written |

We deliberately did **not** reach for EC2, ECS/EKS, or a persistent server: every
compute need here is bursty (an investigation, a daily ingestion run) and fits
Lambda's execution model without idle cost.

## Request flow (current, demo-ready path)

1. Frontend calls `POST /api/analyses` with portfolio weights + event details.
2. API Gateway invokes the `analyses` Lambda, which runs
   `workflows/local_orchestrator.run_investigation` **synchronously** (a documented
   simplification — see `docs/KNOWN_LIMITATIONS.md`).
3. That orchestrator calls each agent's tool functions directly, in the same order
   the Step Functions state machine's states are named, against the frozen data
   snapshot baked into the Lambda image.
4. Result is written to DynamoDB and returned directly in the response.
5. Frontend reads `AnalysisResult` + `InvestigationReport` and renders all 7 pages
   from it.

## Request flow (target, once Bedrock access is confirmed)

1. API starts a Step Functions execution and returns an `analysis_id` immediately.
2. Frontend polls `GET /api/analyses/{id}/status`.
3. Step Functions invokes each agent (now backed by a live Bedrock model) in
   sequence, with per-agent retry/catch.
4. SNS notifies on completion; frontend fetches the final report.

Decomposing the single `RunInvestigationTask` into 5 per-agent Step Functions tasks
is a refactor, not a redesign — the state names in `workflow-stack.ts` are already
aligned with this target.
