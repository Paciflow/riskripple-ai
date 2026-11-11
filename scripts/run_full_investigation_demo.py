#!/usr/bin/env python3
"""Full end-to-end demo: the semiconputer export-restriction scenario (master spec
section 20), run entirely against real frozen data, no AWS required.

Usage: python scripts/run_full_investigation_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from riskripple.workflows.local_orchestrator import run_investigation  # noqa: E402

# Fictional $100,000 demo portfolio (master spec section 20). Labeled fictional
# throughout -- never presented as a real account.
DEMO_PORTFOLIO_WEIGHTS = {
    "SPY": 0.30, "QQQ": 0.20, "NVDA": 0.20, "AMD": 0.10,
    "INTC": 0.10, "AGG": 0.05, "GLD": 0.05,
}
DEMO_PORTFOLIO_VALUE = 100_000.0
DEMO_EVENT_TITLE = "Semiconductor export restrictions on advanced computing chips to China"
DEMO_EVENT_ENTITIES = ["TSMC", "Samsung", "SK Hynix"]


def main() -> None:
    print("=" * 78)
    print("RiskRipple AI -- Demo Investigation (FICTIONAL PORTFOLIO, SIMULATION ONLY)")
    print("=" * 78)
    print(f"\nQuestion: How could '{DEMO_EVENT_TITLE}' affect this portfolio?\n")

    analysis, report = run_investigation(
        portfolio_weights=DEMO_PORTFOLIO_WEIGHTS,
        portfolio_value=DEMO_PORTFOLIO_VALUE,
        event_title=DEMO_EVENT_TITLE,
        event_entities=DEMO_EVENT_ENTITIES,
    )

    print(f"Analysis ID: {analysis.analysis_id}  |  Status: {analysis.status.value}\n")

    print("--- Exposure graph ---")
    print(f"Nodes: {', '.join(analysis.exposure_graph.nodes)}")
    for edge in analysis.exposure_graph.edges:
        print(f"  {edge.source} --[{edge.relationship_type}, {edge.confidence}]--> {edge.target}")

    print("\n--- Persona comparison ---")
    print("  (Each persona's OWN candidate allocation, generated from its policy --")
    print("   not a re-evaluation of the held demo portfolio above.)")
    for fact in report.facts:
        print(f"  {fact}")

    print("\n--- Hypothetical stress scenarios ---")
    for a in report.assumptions:
        print(f"  {a}")

    print("\n--- AI interpretation (flagged separately from facts) ---")
    for interp in report.ai_interpretations:
        print(f"  {interp}")

    print(f"\n--- Evidence citations ({len(report.citations)}) ---")
    for c in report.citations[:5]:
        print(f"  {c.source_name} (as of {c.observation_date or c.publication_date or 'n/a'})")
    if len(report.citations) > 5:
        print(f"  ... and {len(report.citations) - 5} more")

    print("\n--- Known limitations ---")
    for lim in report.limitations[:2]:
        print(f"  {lim}")

    print(f"\nFull report saved via save_investigation_report (report_id={report.report_id}).")


if __name__ == "__main__":
    main()
