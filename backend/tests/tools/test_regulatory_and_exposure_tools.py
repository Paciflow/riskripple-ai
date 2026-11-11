from pathlib import Path

import pytest

from riskripple.tools import regulatory_tools as RT
from riskripple.tools import exposure_tools as ET
from riskripple.tools import persona_tools as PT

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="demo data snapshot not built (run scripts/build_demo_snapshot.py)"
)


def test_list_new_documents_reads_federal_register_fixture():
    result = RT.list_new_documents(fixtures_dir=str(FIXTURES_DIR))
    assert result["count"] > 0
    assert any("export" in d["title"].lower() or "entity list" in d["title"].lower() for d in result["documents"])


def test_search_sanctions_records_is_not_a_legal_determination():
    result = RT.search_sanctions_records("Banco Nacional de Cuba", fixtures_dir=str(FIXTURES_DIR))
    assert result["is_legal_sanctions_determination"] is False
    assert len(result["matches"]) > 0


def test_retrieve_company_filings_real_nvda_10k():
    result = RT.retrieve_company_filings("NVDA", fixtures_dir=str(FIXTURES_DIR))
    assert result["found"]
    assert "export" in result["text"].lower()


def test_retrieve_company_filings_missing_symbol():
    result = RT.retrieve_company_filings("NOT_A_REAL_SYMBOL", fixtures_dir=str(FIXTURES_DIR))
    assert not result["found"]


def test_resolve_entity_aliases_below_threshold_returns_unresolved():
    result = RT.resolve_entity_aliases("Totally Unrelated Corp", {"TSMC": ["Taiwan Semiconductor"]})
    assert result["resolved"] is False


def test_summarize_event_evidence_against_real_nvda_filing():
    result = RT.summarize_event_evidence(
        "semiconductor export restrictions", "NVDA", fixtures_dir=str(FIXTURES_DIR)
    )
    assert result["found"]
    assert "export" in result["evidence_context"].lower()


def test_load_company_graph_and_exposure_chain_real_data():
    graph_json = ET.load_company_graph(["NVDA", "AMD", "INTC"], fixtures_dir=str(FIXTURES_DIR))
    assert any(n["id"] == "TSMC" for n in graph_json["nodes"])

    direct = ET.find_direct_exposure_tool(graph_json, event_entities=["TSMC", "Nonexistent"])
    assert direct["direct_exposure"] == ["TSMC"]
    assert direct["no_established_link"] == ["Nonexistent"]

    hops = ET.traverse_relationships_tool(graph_json, start_nodes=["TSMC"], max_hops=1)
    assert "NVDA" in hops["hop_distances"]

    exposure = ET.calculate_exposure_weights(
        portfolio_weights={"NVDA": 0.5, "SPY": 0.5},
        direct_exposure_symbols=[],
        hop_distances=hops["hop_distances"],
    )
    assert exposure["exposure"]["NVDA"]["exposure_type"] == "indirect"
    assert exposure["exposure"]["SPY"]["exposure_type"] == "no_established_link"


def test_resolve_company_identity_fuzzy_match():
    result = ET.resolve_company_identity("Nvidia", known_symbols=["NVDA", "AMD", "INTC"])
    assert result["resolved"]
    assert result["symbol"] == "NVDA"


def test_generate_decision_explanation_flags_constraint_violations():
    evaluations = {
        "prudent": {
            "annualized_return": 0.05,
            "annualized_volatility": 0.08,
            "max_drawdown": -0.1,
            "constraint_violations": ["single-asset weight on AGG (32.5%) exceeds persona max of 15.0%"],
            "scenario_pnl": {"severe": -1000.0},
        },
        "audacieux": {
            "annualized_return": 0.2,
            "annualized_volatility": 0.3,
            "max_drawdown": -0.3,
            "constraint_violations": [],
            "scenario_pnl": {"severe": -5000.0},
        },
    }
    scenario_summary = PT.compare_scenario_results(evaluations)
    explanation = PT.generate_decision_explanation(evaluations, scenario_summary)
    assert len(explanation["facts"]) == 2
    assert any("prudent" in i for i in explanation["ai_interpretations"])
    assert scenario_summary["severe"]["hardest_hit"] == "audacieux"
