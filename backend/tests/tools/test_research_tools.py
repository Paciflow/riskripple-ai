from __future__ import annotations

from pathlib import Path

from riskripple.tools.research_tools import propose_candidate_entities, search_filings_fulltext

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"


def test_search_filings_fulltext_finds_real_rare_earth_disclosure_in_intc_10k():
    result = search_filings_fulltext("rare earth", fixtures_dir=str(FIXTURES_DIR))

    assert result["found"] is True
    symbols_hit = {h["symbol"] for h in result["hits"]}
    assert symbols_hit == {"INTC"}
    hit = next(h for h in result["hits"] if h["symbol"] == "INTC")
    assert "rare earth elements" in hit["evidence_snippet"].lower()


def test_search_filings_fulltext_correctly_reports_no_match_for_an_absent_material():
    # Confirmed by direct grep against the real fixtures: none of the 3 filings
    # mention copper. A real "no match" result, not a stub.
    result = search_filings_fulltext("copper", fixtures_dir=str(FIXTURES_DIR))

    assert result["found"] is False
    assert result["hits"] == []


def test_search_filings_fulltext_respects_word_boundaries():
    # Regression for the same false-positive class as alerts/relevance.py: "Intel"
    # must not match inside an unrelated word.
    result = search_filings_fulltext("Intel", symbols=["AMD"], fixtures_dir=str(FIXTURES_DIR))
    for hit in result["hits"]:
        assert hit["matched_text"].lower() == "intel"


def test_propose_candidate_entities_finds_real_multiword_entities():
    text = (
        "US intelligence reportedly believes she was spying for China's Ministry of "
        "State Security, and Taiwan Semiconductor Manufacturing Company Limited "
        "declined to comment."
    )
    result = propose_candidate_entities(text)

    assert "Ministry of State Security" in result["candidates"]
    assert "Taiwan Semiconductor Manufacturing Company Limited" in result["candidates"]


def test_propose_candidate_entities_excludes_generic_boilerplate():
    # Regression: "United States" matched trivially against XBRL tag soup in all 3
    # fixture filings when run end-to-end via scripts/run_alert_scan.py, producing a
    # junk hypothesis with no real signal.
    text = "The rule applies to exports from the United States affecting Ministry of State Security operations."
    result = propose_candidate_entities(text)

    assert "United States" not in result["candidates"]
    assert "Ministry of State Security" in result["candidates"]


def test_propose_candidate_entities_is_capped():
    text = " ".join(f"Example Entity {i} Corporation" for i in range(20))
    result = propose_candidate_entities(text, max_candidates=5)

    assert len(result["candidates"]) <= 5
