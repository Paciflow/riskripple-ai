from pathlib import Path

import pytest

from riskripple.schemas.models import AnalysisStatus
from riskripple.workflows.local_orchestrator import run_investigation

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="demo data snapshot not built (run scripts/build_demo_snapshot.py)"
)

DEMO_PORTFOLIO = {
    "SPY": 0.3, "QQQ": 0.2, "NVDA": 0.2, "AMD": 0.1, "INTC": 0.1, "AGG": 0.05, "GLD": 0.05,
}


def test_run_investigation_end_to_end_real_data():
    analysis, report = run_investigation(
        portfolio_weights=DEMO_PORTFOLIO,
        portfolio_value=100_000.0,
        event_title="semiconductor export restrictions on advanced computing chips to China",
        event_entities=["TSMC", "Samsung", "SK Hynix"],
    )

    assert analysis.status == AnalysisStatus.COMPLETE
    assert len(analysis.persona_evaluations) == 3
    assert len(analysis.evidence_citations) > 0

    node_set = set(analysis.exposure_graph.nodes)
    assert {"NVDA", "TSMC", "Samsung"}.issubset(node_set)

    assert report.analysis_id == analysis.analysis_id
    assert len(report.facts) == 3
    assert any("hypothetical" in a.lower() for a in report.assumptions)
    assert report.citations == analysis.evidence_citations


def test_run_investigation_rejects_weights_not_summing_to_one():
    with pytest.raises(ValueError):
        run_investigation(
            portfolio_weights={"SPY": 0.5, "QQQ": 0.2},
            portfolio_value=100_000.0,
            event_title="irrelevant",
            event_entities=[],
        )
