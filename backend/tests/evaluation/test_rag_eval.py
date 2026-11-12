from pathlib import Path

from riskripple.evaluation.rag_eval import EVAL_CASES, build_corpus, run_eval

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"


def test_corpus_builds_from_real_fixtures():
    corpus = build_corpus(FIXTURES_DIR)
    assert len(corpus) > 0
    document_ids = {c.document_id for c in corpus}
    assert {"NVDA_10K", "AMD_10K", "INTC_10K"}.issubset(document_ids)


def test_baseline_retrieval_quality_meets_floor():
    corpus = build_corpus(FIXTURES_DIR)
    report = run_eval(corpus, EVAL_CASES, min_score=0.0)
    summary = report.summary()
    # Regression floor, not a target: see docs/EVALUATION.md for the full breakdown
    # and the min_score=0.0 vs 0.15 tradeoff this is deliberately not applying here.
    assert summary["hit_rate@3"] >= 0.85
    assert summary["mrr"] >= 0.8


def test_min_score_threshold_fixes_negative_controls_without_losing_unique_fr_recall():
    corpus = build_corpus(FIXTURES_DIR)
    report = run_eval(corpus, EVAL_CASES, min_score=0.15)
    summary = report.summary()
    assert summary["by_category"]["negative_control"]["hit_rate@1"] == 1.0
    assert summary["by_category"]["federal_register_unique"]["hit_rate@1"] == 1.0
