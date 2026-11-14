#!/usr/bin/env python3
"""Run the alert pipeline against the real demo fixtures and write the result for
the frontend's Alerts page. This is the actual 'watch and react' loop running
end-to-end: new-document diffing -> real exposure-graph relevance check ->
auto-triggered investigation -> a persisted alert record.

Usage: python3 scripts/run_alert_scan.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from riskripple.alerts.pipeline import run_alert_scan  # noqa: E402
from riskripple.storage.local_store import LocalStore  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"
OUT_PATH = REPO_ROOT / "frontend" / "src" / "data" / "alerts.json"

PORTFOLIO_WEIGHTS = {"SPY": 0.30, "QQQ": 0.20, "NVDA": 0.20, "AMD": 0.10, "INTC": 0.10, "AGG": 0.05, "GLD": 0.05}


def main() -> None:
    documents = json.loads((FIXTURES_DIR / "regulatory" / "federal_register_bis_semiconductor.json").read_text())
    print(f"Scanning {len(documents)} real Federal Register documents against the demo portfolio...")

    store = LocalStore()
    alerts = run_alert_scan(
        documents=documents,
        portfolio_symbols=list(PORTFOLIO_WEIGHTS.keys()),
        portfolio_weights=PORTFOLIO_WEIGHTS,
        portfolio_value=100_000.0,
        store=store,
        fixtures_dir=str(FIXTURES_DIR),
    )

    print(f"\n{len(alerts)} alert(s) generated (the other {len(documents) - len(alerts)} documents "
          f"were new but not relevant to this portfolio, and correctly suppressed):\n")
    for a in alerts:
        print(f"  [{a.document_id}] {a.title}")
        for m in a.matches:
            print(f"      {m.symbol} ({m.relationship} via '{m.node_id}'): \"{m.evidence_snippet[:100]}...\"")
        print(f"      -> linked investigation: {a.linked_analysis_id}\n")

    # Confirm the diffing actually works: re-running against the same store yields nothing new.
    second_pass = run_alert_scan(
        documents=documents, portfolio_symbols=list(PORTFOLIO_WEIGHTS.keys()),
        portfolio_weights=PORTFOLIO_WEIGHTS, portfolio_value=100_000.0,
        store=store, fixtures_dir=str(FIXTURES_DIR),
    )
    print(f"Re-running against the same store: {len(second_pass)} new alerts (should be 0 -- confirms diffing works).")

    payload = [json.loads(a.model_dump_json()) for a in alerts]
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
