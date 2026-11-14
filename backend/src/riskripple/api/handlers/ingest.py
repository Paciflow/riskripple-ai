"""EventBridge-scheduled ingestion handler: refreshes the regulatory/market/macro
data under s3://<data-bucket>/raw and /processed by calling the same ingestion
adapters used by scripts/build_demo_snapshot.py, writing to S3 instead of the local
data/fixtures/ directory. Also runs the alert pipeline (riskripple.alerts.pipeline)
against the Federal Register documents this same run just fetched -- this is the
"watch and react" loop (see docs/ALERT_PIPELINE.md) actually running on a schedule,
not just something callable by hand.

UNTESTED LIVE (s3/dynamodb permissions on this handler's role are defined in
infrastructure/cdk/lib/ingestion-stack.ts but deployment itself is blocked by the
personal account's CloudFormation access denial -- see docs/KNOWN_LIMITATIONS.md).

The tracked-portfolio list is a single hardcoded demo portfolio
(TRACKED_PORTFOLIOS below) because there is no real multi-portfolio registry yet --
every portfolio in this build is the same fictional demo allocation. A real version
would read tracked portfolios from the `riskripple-portfolios` table instead.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3

from riskripple.alerts.pipeline import run_alert_scan
from riskripple.config import FIXTURES_DIR
from riskripple.ingestion import macro_fred, regulatory_events, sanctions_gac, sanctions_ofac
from riskripple.storage import get_store

_BUCKET = os.environ.get("RISKRIPPLE_DATA_BUCKET")

TRACKED_PORTFOLIOS = [
    {
        "portfolio_id": "demo_portfolio",
        "weights": {"SPY": 0.30, "QQQ": 0.20, "NVDA": 0.20, "AMD": 0.10, "INTC": 0.10, "AGG": 0.05, "GLD": 0.05},
        "value": 100_000.0,
    },
]


def _serialize_fred_observations(observations) -> dict:
    """pandas Series indexed by Timestamp -> json.dumps-safe dict. Extracted so this
    specific, previously-broken transformation (see handler's comment) has its own
    fast, no-network regression test."""
    return {k.isoformat(): v for k, v in observations.to_dict().items()}


def _put_json(s3_client, key: str, payload: object) -> None:
    s3_client.put_object(
        Bucket=_BUCKET, Key=key, Body=json.dumps(payload, indent=2, default=str).encode("utf-8")
    )


def handler(event: dict, context) -> dict:
    s3_client = boto3.client("s3")
    prefix = f"raw/regulatory/{datetime.now(timezone.utc).date().isoformat()}"
    results = {}

    ofac = sanctions_ofac.fetch_sdn_list()
    _put_json(s3_client, f"{prefix}/ofac_sdn.json", [r.__dict__ for r in ofac.records])
    _put_json(s3_client, f"{prefix}/ofac_sdn.metadata.json", ofac.metadata.model_dump())
    results["ofac_sdn_records"] = len(ofac.records)

    gac = sanctions_gac.fetch_consolidated_list()
    _put_json(s3_client, f"{prefix}/gac_consolidated.json", [r.__dict__ for r in gac.records])
    results["gac_records"] = len(gac.records)

    # Broader net than a single hardcoded term (see ingestion/regulatory_events.py) --
    # this is Layer 1 of the two-layer narrowness documented in docs/KNOWN_LIMITATIONS.md:
    # a document about an unrelated material/sector couldn't be detected before, no
    # matter how good relevance-matching was, because it was never fetched at all.
    fedreg = regulatory_events.search_documents_multi(agency_slugs=[regulatory_events.BIS_AGENCY_SLUG])
    fedreg_dicts = [d.__dict__ for d in fedreg.documents]
    _put_json(s3_client, f"{prefix}/federal_register_bis_semiconductor.json", fedreg_dicts)
    results["federal_register_documents"] = len(fedreg.documents)

    fred = macro_fred.fetch_series("DGS10")
    # Series is indexed by pandas Timestamp -- json.dumps can't use that as a dict key
    # (confirmed by actually running this handler against live data for the first
    # time; every prior test exercised this path with mocked/frozen responses that
    # never produced a DatetimeIndex -- see docs/KNOWN_LIMITATIONS.md).
    _put_json(s3_client, f"{prefix}/fred_dgs10.json", _serialize_fred_observations(fred.observations))
    results["fred_observations"] = len(fred.observations)

    store = get_store()
    total_alerts = 0
    for portfolio in TRACKED_PORTFOLIOS:
        alerts = run_alert_scan(
            documents=fedreg_dicts,
            portfolio_symbols=list(portfolio["weights"].keys()),
            portfolio_weights=portfolio["weights"],
            portfolio_value=portfolio["value"],
            store=store,
            fixtures_dir=str(FIXTURES_DIR),
        )
        total_alerts += len(alerts)
    results["alerts_generated"] = total_alerts

    return {"statusCode": 200, "body": json.dumps(results)}
