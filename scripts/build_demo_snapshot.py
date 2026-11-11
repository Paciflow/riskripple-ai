#!/usr/bin/env python3
"""Build the frozen, reproducible data snapshot used for the datathon demo.

Pulls real data from live public sources ONCE and freezes it under data/fixtures/, so
the demo never depends on a source being reachable, rate-limit-free, or unchanged at
presentation time. Run this again any time you want a fresher snapshot before the
hackathon.

Usage: python scripts/build_demo_snapshot.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from riskripple.ingestion import (  # noqa: E402
    market_data,
    sanctions_ofac,
    sanctions_gac,
    macro_fred,
    filings_sec,
    regulatory_events,
)

FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"

# Fictional $100k demo portfolio universe (section 20 of the master spec): broad market,
# tech, bonds, gold, cash proxy, plus individual semiconductor names for the direct
# exposure scenario (export-restriction demo).
UNIVERSE = ["SPY", "QQQ", "AGG", "GLD", "BIL", "NVDA", "AMD", "INTC"]

# CIK numbers for 10-K ingestion into the RAG fixture set (semiconductor exposure demo).
FILING_TARGETS = {
    "NVDA": "0001045810",
    "AMD": "0000002488",
    "INTC": "0000050863",
}


def build_market_snapshots(manifest: dict) -> None:
    out_dir = FIXTURES_DIR / "market"
    manifest["market"] = {}
    for symbol in UNIVERSE:
        print(f"[market] fetching {symbol} ...")
        result = market_data.fetch_price_history_yahoo(symbol)
        market_data.save_snapshot(result, out_dir)
        manifest["market"][symbol] = {
            "rows": len(result.prices),
            "content_hash": result.metadata.content_hash,
            "observation_date": str(result.metadata.observation_date),
        }
        time.sleep(1.5)  # be polite to an unofficial, rate-limited endpoint


def build_sanctions_snapshots(manifest: dict) -> None:
    out_dir = FIXTURES_DIR / "regulatory"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[regulatory] fetching OFAC SDN list ...")
    ofac = sanctions_ofac.fetch_sdn_list()
    (out_dir / "ofac_sdn.json").write_text(
        json.dumps([r.__dict__ for r in ofac.records], indent=2)
    )
    (out_dir / "ofac_sdn.metadata.json").write_text(ofac.metadata.model_dump_json(indent=2))
    manifest["ofac_sdn"] = {"records": len(ofac.records), "content_hash": ofac.metadata.content_hash}

    print("[regulatory] fetching Global Affairs Canada consolidated list ...")
    gac = sanctions_gac.fetch_consolidated_list()
    (out_dir / "gac_consolidated.json").write_text(
        json.dumps([r.__dict__ for r in gac.records], indent=2)
    )
    (out_dir / "gac_consolidated.metadata.json").write_text(gac.metadata.model_dump_json(indent=2))
    manifest["gac_consolidated"] = {"records": len(gac.records), "content_hash": gac.metadata.content_hash}


def build_regulatory_events_snapshot(manifest: dict) -> None:
    out_dir = FIXTURES_DIR / "regulatory"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[regulatory] fetching Federal Register semiconductor export-control documents ...")
    result = regulatory_events.search_documents(
        term="semiconductor export",
        agency_slugs=[regulatory_events.BIS_AGENCY_SLUG],
        per_page=20,
    )
    (out_dir / "federal_register_bis_semiconductor.json").write_text(
        json.dumps([d.__dict__ for d in result.documents], indent=2)
    )
    (out_dir / "federal_register_bis_semiconductor.metadata.json").write_text(
        result.metadata.model_dump_json(indent=2)
    )
    manifest["federal_register_bis_semiconductor"] = {
        "documents": len(result.documents),
        "content_hash": result.metadata.content_hash,
    }


def build_macro_snapshots(manifest: dict) -> None:
    out_dir = FIXTURES_DIR / "macro"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest["macro"] = {}
    for series_id in ["DGS10", "DGS3MO"]:
        print(f"[macro] fetching FRED {series_id} ...")
        result = macro_fred.fetch_series(series_id)
        result.observations.to_csv(out_dir / f"{series_id}.csv", header=[series_id])
        (out_dir / f"{series_id}.metadata.json").write_text(result.metadata.model_dump_json(indent=2))
        manifest["macro"][series_id] = {
            "rows": len(result.observations),
            "content_hash": result.metadata.content_hash,
        }
        time.sleep(0.5)


def build_filings_snapshots(manifest: dict) -> None:
    out_dir = FIXTURES_DIR / "filings"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest["filings"] = {}
    for symbol, cik in FILING_TARGETS.items():
        print(f"[filings] fetching {symbol} (CIK {cik}) submissions ...")
        submissions = filings_sec.fetch_company_submissions(cik)
        tenk_filings = filings_sec.filter_filings(submissions.recent_filings, "10-K", limit=1)
        if not tenk_filings:
            print(f"  no recent 10-K found for {symbol}, skipping document fetch")
            continue
        filing = tenk_filings[0]
        print(f"  fetching 10-K document {filing.accession_number} ...")
        text, doc_metadata = filings_sec.fetch_filing_text(cik, filing)
        (out_dir / f"{symbol}_10K.txt").write_text(text)
        (out_dir / f"{symbol}_10K.metadata.json").write_text(doc_metadata.model_dump_json(indent=2))
        manifest["filings"][symbol] = {
            "accession_number": filing.accession_number,
            "filing_date": filing.filing_date,
            "chars": len(text),
            "content_hash": doc_metadata.content_hash,
        }
        time.sleep(0.5)


def main() -> None:
    manifest = {"built_at": datetime.now(timezone.utc).isoformat()}
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    build_market_snapshots(manifest)
    build_sanctions_snapshots(manifest)
    build_regulatory_events_snapshot(manifest)
    build_macro_snapshots(manifest)
    build_filings_snapshots(manifest)

    (FIXTURES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nSnapshot manifest written to {FIXTURES_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
