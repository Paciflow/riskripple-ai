#!/usr/bin/env python3
"""Run the RAG retrieval evaluation benchmark and print/save a report.

Usage: python scripts/run_rag_eval.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from riskripple.evaluation.rag_eval import EVAL_CASES, build_corpus, run_eval  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"
RESULTS_PATH = REPO_ROOT / "data" / "evaluation" / "rag_eval_results.json"


def _run_and_print(corpus, min_score: float) -> dict:
    report = run_eval(corpus, EVAL_CASES, min_score=min_score)
    summary = report.summary()

    print(f"\n=== min_score={min_score} ===")
    print(f"{'Category':<28} {'n':>4} {'hit@1':>8} {'hit@3':>8}")
    for cat, stats in summary["by_category"].items():
        print(f"{cat:<28} {stats['n']:>4} {stats['hit_rate@1']:>8.2f} {stats['hit_rate@3']:>8.2f}")

    print(f"\nOverall: n={summary['n_cases']}  hit@1={summary['hit_rate@1']:.2f}  "
          f"hit@3={summary['hit_rate@3']:.2f}  MRR={summary['mrr']:.2f}  "
          f"keyword_accuracy={summary['keyword_accuracy']:.2f}")

    failures = [r for r in report.results if not r.hit_at_3 or not r.keyword_ok]
    if failures:
        print(f"{len(failures)} case(s) failed hit@3 or the keyword check:")
        for r in failures:
            got = [rc.chunk.document_id for rc in r.retrieved[:3]]
            print(f"  [{r.case.category}] \"{r.case.query}\" -> expected {sorted(r.case.expected_document_ids)}, got {got}")

    return {
        "min_score": min_score,
        "summary": summary,
        "cases": [
            {
                "query": r.case.query,
                "category": r.case.category,
                "expected_document_ids": sorted(r.case.expected_document_ids),
                "retrieved_document_ids": [rc.chunk.document_id for rc in r.retrieved[:5]],
                "hit_at_1": r.hit_at_1,
                "hit_at_3": r.hit_at_3,
                "keyword_ok": r.keyword_ok,
            }
            for r in report.results
        ],
    }


def main() -> None:
    corpus = build_corpus(FIXTURES_DIR)
    print(f"Corpus: {len(corpus)} chunks from 3 filings + 20 Federal Register documents")

    runs = [_run_and_print(corpus, min_score=0.0), _run_and_print(corpus, min_score=0.15)]

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "corpus_chunks": len(corpus),
        "runs": runs,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {RESULTS_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
