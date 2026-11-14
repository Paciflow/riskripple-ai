"""The 'watch and react' loop: detect new regulatory/export-control documents, check
each against a portfolio's real exposure graph, and auto-trigger a full investigation
(the same tested pipeline as workflows.local_orchestrator.run_investigation) for any
genuinely relevant one.

This is the piece that was missing before: every component it calls already existed
and was independently tested (ingestion, the exposure graph, the orchestrator) but
nothing previously connected "a new document appeared" to "does this affect a
tracked portfolio" to "run an investigation and record an alert." See
docs/ALERT_PIPELINE.md.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from riskripple.alerts.relevance import check_relevance
from riskripple.investigation.loop import run_ripple_investigation
from riskripple.schemas.models import Alert, RelevanceMatch
from riskripple.storage.base import Store
from riskripple.tools.exposure_tools import load_company_graph
from riskripple.workflows.local_orchestrator import run_investigation

SEEN_DOCUMENTS_TABLE = "riskripple-regulatory-events"
ALERTS_TABLE = "riskripple-alerts"

# Gates the Ripple Investigation step (investigation.loop) below. Defaults to on: the
# deterministic fallback loop requires no Bedrock access and has its own test suite
# (tests/investigation/test_loop.py) proving it only ever reports real, literal
# evidence -- it is safe to run by default. Set to "0" to fall back to exactly the
# original alert pipeline (relevance match -> investigation, nothing in between) if
# this ever needs to be disabled quickly.
RIPPLE_INVESTIGATION_ENABLED = os.environ.get("RISKRIPPLE_ENABLE_RIPPLE_INVESTIGATION", "1") != "0"


def scan_for_new_documents(documents: list[dict], store: Store) -> list[dict]:
    """Returns the subset of `documents` not already recorded in `store`, and
    records every document passed in as seen (so a second call with the same input
    returns nothing — this is the diffing step a dynamic store makes possible that a
    flat file snapshot can't do on its own).
    """
    new_docs = []
    for doc in documents:
        doc_id = doc["document_number"]
        existing = store.get_item(SEEN_DOCUMENTS_TABLE, {"event_id": doc_id})
        if existing is None:
            new_docs.append(doc)
        store.put_item(
            SEEN_DOCUMENTS_TABLE,
            {
                "event_id": doc_id,
                "title": doc.get("title", ""),
                "publication_date": doc.get("publication_date"),
                "jurisdiction": "us_bis",
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return new_docs


def run_alert_scan(
    *,
    documents: list[dict],
    portfolio_symbols: list[str],
    portfolio_weights: dict[str, float],
    portfolio_value: float,
    store: Store,
    fixtures_dir: str | None = None,
) -> list[Alert]:
    """Scans `documents` (as returned by ingestion.regulatory_events.search_documents)
    for ones new since the last call, checks each against `portfolio_symbols`'s real
    exposure graph, and auto-runs a full investigation for any relevant one.

    Returns the alerts generated THIS run (not the full historical list — callers
    that want that should query `store` directly, e.g. via query_index once deployed
    to DynamoDB with the by-status index).
    """
    new_docs = scan_for_new_documents(documents, store)
    if not new_docs:
        return []

    graph_json = load_company_graph(portfolio_symbols, fixtures_dir=fixtures_dir)

    alerts: list[Alert] = []
    for doc in new_docs:
        text = f"{doc.get('title', '')}\n\n{doc.get('abstract', '')}"
        matches = check_relevance(text, graph_json, portfolio_symbols)
        if not matches:
            continue  # new, but not relevant to this portfolio -- correctly suppressed

        trace, hypotheses = [], []
        if RIPPLE_INVESTIGATION_ENABLED:
            # Look beyond the fixed alias lists for additional, previously-unknown
            # ripple effects -- see investigation/loop.py. This never changes whether
            # an alert fires (that's still decided by check_relevance above); it only
            # adds extra, separately-labeled findings to the resulting report.
            trace, hypotheses = run_ripple_investigation(
                document_title=doc.get("title", ""),
                document_abstract=doc.get("abstract", ""),
                portfolio_symbols=portfolio_symbols,
                initial_matches=matches,
                fixtures_dir=fixtures_dir,
            )

        analysis, _report = run_investigation(
            portfolio_weights=portfolio_weights,
            portfolio_value=portfolio_value,
            event_title=doc["title"],
            event_entities=sorted({m.node_id for m in matches}),
            fixtures_dir=fixtures_dir,
            hypotheses=hypotheses,
            investigation_trace=trace,
        )

        alert = Alert(
            document_id=doc["document_number"],
            title=doc["title"],
            source_name="Federal Register (Bureau of Industry and Security)",
            source_url=doc.get("document_url", ""),
            publication_date=doc.get("publication_date"),
            matches=[
                RelevanceMatch(
                    symbol=m.symbol,
                    relationship=m.relationship,
                    node_id=m.node_id,
                    matched_entity=m.matched_entity,
                    evidence_snippet=m.evidence_snippet,
                )
                for m in matches
            ],
            linked_analysis_id=analysis.analysis_id,
            status="investigated",
        )
        store.put_item(ALERTS_TABLE, alert.model_dump(mode="json"))
        alerts.append(alert)

    return alerts
