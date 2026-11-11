"""Deterministic local orchestrator: runs the same 13-state sequence the Step
Functions state machine will run in AWS (see infrastructure/cdk and
docs/ARCHITECTURE.md), but calls each agent's tool functions directly in Python
instead of through a live Bedrock-backed Agent.

This exists because bedrock:InvokeModel is access-denied on the personal AWS account
used for development (docs/KNOWN_LIMITATIONS.md), so the LLM-driven tool-selection
layer in riskripple.agents.definitions is untested live. This orchestrator proves the
tool chain itself -- real data in, real numbers out, real citations -- end to end
without that dependency. Swapping to the Step Functions + Bedrock Agent path later
should produce the same AnalysisResult shape, not different data.
"""
from __future__ import annotations

import time
from pathlib import Path

from riskripple.schemas.models import (
    AnalysisResult,
    AnalysisStatus,
    AuditEvent,
    ExposureEdge,
    ExposureGraph,
    InvestigationReport,
    PersonaEvaluation,
    PersonaName,
)
from riskripple.schemas.provenance import SourceMetadata
from riskripple.tools import exposure_tools as ET
from riskripple.tools import finance_tools as FT
from riskripple.tools import persona_tools as PT
from riskripple.tools import regulatory_tools as RT

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"


class _AuditLog:
    """In-memory audit trail; mirrors the AuditEvent records that would be written to
    DynamoDB/CloudWatch in the deployed system (section 17)."""

    def __init__(self, analysis_id: str):
        self.analysis_id = analysis_id
        self.events: list[AuditEvent] = []

    def record(self, step: str, tool_name: str | None = None, status: str = "success", detail: str | None = None, started_at: float | None = None) -> None:
        duration_ms = (time.monotonic() - started_at) * 1000 if started_at else None
        self.events.append(
            AuditEvent(
                analysis_id=self.analysis_id,
                agent_name=step,
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                detail=detail,
            )
        )


def run_investigation(
    *,
    portfolio_weights: dict[str, float],
    portfolio_value: float,
    event_title: str,
    event_entities: list[str],
    persona_names: list[str] | None = None,
    fixtures_dir: str | None = None,
) -> tuple[AnalysisResult, InvestigationReport]:
    """Run the full investigation pipeline against real frozen demo data.

    States mirror the master spec section 15 Step Functions definition:
    ValidateAnalysisRequest -> LoadPortfolio -> LoadRegulatoryEvent -> RetrieveEvidence
    -> ResolveEntities -> MapExposure -> CalculateFinancialMetrics -> RunStressScenarios
    -> EvaluatePersonas -> GenerateExplanation -> ValidateCitations -> PersistResults
    -> NotifyCompletion.
    """
    fixtures_dir = fixtures_dir or str(FIXTURES_DIR)
    persona_names = persona_names or [p.value for p in PersonaName]

    analysis = AnalysisResult(portfolio_id="demo-portfolio", status=AnalysisStatus.RUNNING)
    audit = _AuditLog(analysis.analysis_id)

    # 1. ValidateAnalysisRequest
    t0 = time.monotonic()
    if abs(sum(portfolio_weights.values()) - 1.0) > 1e-3:
        audit.record("ValidateAnalysisRequest", status="failure", detail="weights do not sum to 1", started_at=t0)
        analysis.status = AnalysisStatus.FAILED
        raise ValueError("portfolio weights must sum to 1.0")
    audit.record("ValidateAnalysisRequest", started_at=t0)

    symbols = list(portfolio_weights.keys())
    citations: list[SourceMetadata] = []

    # 2. LoadPortfolio (already given) -- 3. LoadRegulatoryEvent
    t0 = time.monotonic()
    doc_result = RT.list_new_documents(fixtures_dir=fixtures_dir)
    audit.record("LoadRegulatoryEvent", tool_name="list_new_documents", started_at=t0)

    # 4. RetrieveEvidence (per holding with a 10-K fixture available)
    evidence_by_symbol = {}
    for symbol in symbols:
        t0 = time.monotonic()
        summary = RT.summarize_event_evidence(event_title, symbol, fixtures_dir=fixtures_dir)
        audit.record("RetrieveEvidence", tool_name="summarize_event_evidence", detail=symbol, started_at=t0)
        if summary["found"]:
            evidence_by_symbol[symbol] = summary["evidence_context"]
            filing = RT.retrieve_company_filings(symbol, fixtures_dir=fixtures_dir)
            if filing["found"] and filing["metadata"]:
                citations.append(SourceMetadata(**filing["metadata"]))

    # 5. ResolveEntities -- 6. MapExposure
    t0 = time.monotonic()
    graph_json = ET.load_company_graph(symbols, fixtures_dir=fixtures_dir)
    audit.record("MapExposure", tool_name="load_company_graph", started_at=t0)

    direct = ET.find_direct_exposure_tool(graph_json, event_entities)
    hops = ET.traverse_relationships_tool(graph_json, start_nodes=event_entities, max_hops=2)
    exposure = ET.calculate_exposure_weights(
        portfolio_weights, direct["direct_exposure"], hops["hop_distances"]
    )

    exposure_graph = ExposureGraph(
        event_id="demo-event",
        nodes=[n["id"] for n in graph_json["nodes"]],
        edges=[ExposureEdge(**{k: v for k, v in e.items()}) for e in graph_json["edges"]],
    )

    # 7. CalculateFinancialMetrics
    t0 = time.monotonic()
    history = FT.load_price_history(symbols, snapshot_dir=f"{fixtures_dir}/market")
    returns = FT.calculate_returns(history["_panel_csv"])
    audit.record("CalculateFinancialMetrics", tool_name="load_price_history+calculate_returns", started_at=t0)
    for symbol, prov in history["provenance"].items():
        citations.append(SourceMetadata(
            source_name=prov["source_name"], source_url=prov["source_url"],
            retrieved_at=analysis.created_at, observation_date=prov["observation_date"],
            currency=prov["currency"], data_version="demo-snapshot", content_hash="n/a",
            license_or_restriction="see docs/DATA_SOURCES.md",
        ))

    # 8. RunStressScenarios -- 9. EvaluatePersonas (combined via evaluate_portfolio_alternatives)
    t0 = time.monotonic()
    evaluations = PT.evaluate_portfolio_alternatives(returns["_returns_csv"], persona_names)
    audit.record("EvaluatePersonas", tool_name="evaluate_portfolio_alternatives", started_at=t0)

    # 10. GenerateExplanation
    t0 = time.monotonic()
    scenario_summary = PT.compare_scenario_results(evaluations)
    explanation = PT.generate_decision_explanation(evaluations, scenario_summary)
    audit.record("GenerateExplanation", tool_name="generate_decision_explanation", started_at=t0)

    # 11. ValidateCitations
    t0 = time.monotonic()
    cited_names = [c.source_name for c in citations]
    validation = PT.validate_report_citations(
        [c.model_dump() for c in citations], cited_names
    )
    audit.record("ValidateCitations", tool_name="validate_report_citations", status="success" if validation["all_citations_supported"] else "failure", started_at=t0)

    analysis.status = AnalysisStatus.COMPLETE
    analysis.persona_evaluations = [PersonaEvaluation(**ev) for ev in evaluations.values()]
    analysis.exposure_graph = exposure_graph
    analysis.evidence_citations = citations
    analysis.assumptions = explanation["assumptions"]
    analysis.limitations = [
        "Exposure graph uses only literal supplier mentions found in the 3 semiconductor "
        "10-Ks in the demo fixture set; absence of an edge means 'not found in this "
        "limited text', not 'confirmed no relationship'.",
        "Stress scenario shocks are illustrative assumptions, not calibrated forecasts.",
        f"Exposure classification: {exposure['exposure']}",
    ]

    report = InvestigationReport(
        analysis_id=analysis.analysis_id,
        investment_question=f"How could '{event_title}' affect this portfolio?",
        event_summary=event_title,
        facts=explanation["facts"],
        assumptions=explanation["assumptions"],
        hypothetical_scenarios=list(scenario_summary.keys()),
        ai_interpretations=explanation["ai_interpretations"],
        citations=citations,
        limitations=analysis.limitations,
        next_steps=[
            "Expand the supplier-relationship fixture set beyond 3 companies for broader coverage.",
            "Verify Bedrock access on the hackathon AWS account and re-run via the live agent path.",
        ],
    )

    # 12. PersistResults
    t0 = time.monotonic()
    PT.save_investigation_report(report.model_dump(), report.report_id)
    audit.record("PersistResults", tool_name="save_investigation_report", started_at=t0)

    # 13. NotifyCompletion
    audit.record("NotifyCompletion")

    return analysis, report
