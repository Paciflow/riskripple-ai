from riskripple.alerts.relevance import check_relevance

GRAPH = {
    "nodes": [{"id": "NVDA", "highlighted": False}, {"id": "TSMC", "highlighted": False}],
    "edges": [
        {
            "source": "NVDA",
            "target": "TSMC",
            "relationship_type": "supplier",
            "confidence": "verified",
            "evidence_source": 'NVDA 10-K: "We utilize foundries, such as TSMC..."',
        }
    ],
}


def test_direct_match_on_company_name():
    text = "The semiconductors covered by this rule are the Nvidia H200 and its equivalents."
    matches = check_relevance(text, GRAPH, ["NVDA"])
    assert len(matches) == 1
    assert matches[0].symbol == "NVDA"
    assert matches[0].relationship == "direct"


def test_supply_chain_match_via_known_supplier():
    text = "This rule affects Taiwan Semiconductor Manufacturing Company's export licensing."
    matches = check_relevance(text, GRAPH, ["NVDA"])
    assert len(matches) == 1
    assert matches[0].symbol == "NVDA"
    assert matches[0].relationship == "supply_chain"
    assert matches[0].node_id == "TSMC"


def test_no_match_for_unrelated_document():
    text = "This rule concerns agricultural export subsidies for soybean producers."
    assert check_relevance(text, GRAPH, ["NVDA"]) == []


def test_does_not_false_positive_on_substring_of_unrelated_word():
    # Regression test: naive substring matching on "Intel" matched "Artificial
    # Intelligence" in 3 of 5 real Federal Register documents before this fix
    # (see docs/EVALUATION.md-adjacent note in relevance.py's module docstring).
    graph = {
        "nodes": [{"id": "INTC", "highlighted": False}],
        "edges": [],
    }
    text = "Framework for Artificial Intelligence Diffusion: this interim final rule..."
    assert check_relevance(text, graph, ["INTC"]) == []


def test_real_intel_mention_still_matches():
    graph = {"nodes": [{"id": "INTC", "highlighted": False}], "edges": []}
    text = "...by removing Intel Semiconductor (Dalian) Ltd from the Entity List."
    matches = check_relevance(text, graph, ["INTC"])
    assert len(matches) == 1
    assert matches[0].symbol == "INTC"
    assert matches[0].relationship == "direct"
