from __future__ import annotations

from pathlib import Path

from riskripple.investigation.loop import run_ripple_investigation
from riskripple.schemas.models import RelevanceMatch

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"

PORTFOLIO = ["NVDA", "AMD", "INTC"]


def test_discovers_a_real_dependency_not_in_any_existing_alias_list():
    # "Rare Earth Elements" is not in KNOWN_SUPPLIER_ALIASES/KNOWN_COMPANY_NAMES --
    # today's check_relevance() would never find this. The deterministic fallback
    # loop should discover it anyway, via a real match in INTC's actual 10-K.
    trace, hypotheses = run_ripple_investigation(
        document_title="New Export Controls on Rare Earth Elements Announced",
        document_abstract="The rule restricts exports of certain Rare Earth Elements.",
        portfolio_symbols=PORTFOLIO,
        initial_matches=[],
        fixtures_dir=str(FIXTURES_DIR),
    )

    assert any(h.status == "evidence_supported_hypothesis" and "INTC" in h.related_symbols for h in hypotheses)
    matched_step = next(s for s in trace if s.result_status == "evidence_supported_hypothesis")
    assert "rare earth" in matched_step.evidence_found[0].lower()


def test_an_unconnected_candidate_is_reported_as_unverified_not_dropped_or_fabricated():
    trace, hypotheses = run_ripple_investigation(
        document_title="Regulatory Action Concerning the Argentina Lithium Triangle",
        document_abstract="Officials announced new rules affecting the Argentina Lithium Triangle region.",
        portfolio_symbols=PORTFOLIO,
        initial_matches=[],
        fixtures_dir=str(FIXTURES_DIR),
    )

    assert hypotheses == []  # no fabricated claim
    unverified_steps = [s for s in trace if s.result_status == "unverified_possibility"]
    assert any("Argentina Lithium Triangle" in s.question for s in unverified_steps)


def test_already_confirmed_matches_are_not_re_proposed_as_new_candidates():
    initial = [
        RelevanceMatch(
            symbol="NVDA", relationship="direct", node_id="NVDA",
            matched_entity="NVIDIA", evidence_snippet="NVIDIA was named directly.",
        )
    ]
    trace, _ = run_ripple_investigation(
        document_title="Action Targeting NVIDIA",
        document_abstract="NVIDIA products are affected.",
        portfolio_symbols=PORTFOLIO,
        initial_matches=initial,
        fixtures_dir=str(FIXTURES_DIR),
    )

    first_step = trace[0]
    assert "NVIDIA" not in first_step.evidence_found


def test_respects_the_max_hypotheses_budget():
    trace, hypotheses = run_ripple_investigation(
        document_title="Action Involving Rare Earth Elements and Silicon Wafer Supply",
        document_abstract="Covers Rare Earth Elements and Silicon Wafer production.",
        portfolio_symbols=PORTFOLIO,
        initial_matches=[],
        fixtures_dir=str(FIXTURES_DIR),
        max_hypotheses=1,
    )

    assert len(hypotheses) <= 1
