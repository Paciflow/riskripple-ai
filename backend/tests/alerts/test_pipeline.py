import json
from pathlib import Path

from riskripple.alerts.pipeline import run_alert_scan, scan_for_new_documents
from riskripple.storage.local_store import LocalStore

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"
PORTFOLIO_WEIGHTS = {"SPY": 0.30, "QQQ": 0.20, "NVDA": 0.20, "AMD": 0.10, "INTC": 0.10, "AGG": 0.05, "GLD": 0.05}


def _real_documents() -> list[dict]:
    path = FIXTURES_DIR / "regulatory" / "federal_register_bis_semiconductor.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_scan_for_new_documents_is_idempotent():
    store = LocalStore()
    docs = _real_documents()
    first_pass = scan_for_new_documents(docs, store)
    second_pass = scan_for_new_documents(docs, store)
    assert len(first_pass) == len(docs)
    assert second_pass == []


def test_run_alert_scan_flags_real_relevant_documents_and_suppresses_the_rest():
    store = LocalStore()
    alerts = run_alert_scan(
        documents=_real_documents(),
        portfolio_symbols=list(PORTFOLIO_WEIGHTS.keys()),
        portfolio_weights=PORTFOLIO_WEIGHTS,
        portfolio_value=100_000.0,
        store=store,
        fixtures_dir=str(FIXTURES_DIR),
    )
    # Grep-confirmed against the real fixture (see relevance.py's module docstring):
    # 2026-00789 names "Nvidia H200" directly; 2025-16735 names Intel/Samsung/SK
    # Hynix China subsidiaries. The other 18 real documents don't name any held
    # company or its known suppliers and must NOT produce an alert.
    flagged_ids = {a.document_id for a in alerts}
    assert flagged_ids == {"2026-00789", "2025-16735"}

    nvda_alert = next(a for a in alerts if a.document_id == "2026-00789")
    assert any(m.symbol == "NVDA" and m.relationship == "direct" for m in nvda_alert.matches)
    assert nvda_alert.linked_analysis_id is not None

    intc_alert = next(a for a in alerts if a.document_id == "2025-16735")
    symbols_matched = {m.symbol for m in intc_alert.matches}
    assert "INTC" in symbols_matched  # direct: "Intel Semiconductor (Dalian) Ltd"
    assert "NVDA" in symbols_matched  # supply_chain: via Samsung/SK Hynix edges


def test_run_alert_scan_is_idempotent_across_calls():
    store = LocalStore()
    docs = _real_documents()
    first = run_alert_scan(
        documents=docs, portfolio_symbols=list(PORTFOLIO_WEIGHTS.keys()),
        portfolio_weights=PORTFOLIO_WEIGHTS, portfolio_value=100_000.0,
        store=store, fixtures_dir=str(FIXTURES_DIR),
    )
    second = run_alert_scan(
        documents=docs, portfolio_symbols=list(PORTFOLIO_WEIGHTS.keys()),
        portfolio_weights=PORTFOLIO_WEIGHTS, portfolio_value=100_000.0,
        store=store, fixtures_dir=str(FIXTURES_DIR),
    )
    assert len(first) == 2
    assert second == []  # nothing "new" on the second pass -- already-seen documents
