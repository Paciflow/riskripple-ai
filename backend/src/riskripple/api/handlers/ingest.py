"""EventBridge-scheduled ingestion handler: refreshes the regulatory/market/macro
data under s3://<data-bucket>/raw and /processed by calling the same ingestion
adapters used by scripts/build_demo_snapshot.py, writing to S3 instead of the local
data/fixtures/ directory. UNTESTED LIVE (s3 permissions on this handler's role are
defined in infrastructure/cdk/lib/ingestion-stack.ts but deployment itself is blocked
by the personal account's CloudFormation access denial -- see
docs/KNOWN_LIMITATIONS.md).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3

from riskripple.ingestion import macro_fred, regulatory_events, sanctions_gac, sanctions_ofac

_BUCKET = os.environ.get("RISKRIPPLE_DATA_BUCKET")


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

    fedreg = regulatory_events.search_documents(
        term="semiconductor export", agency_slugs=[regulatory_events.BIS_AGENCY_SLUG]
    )
    _put_json(s3_client, f"{prefix}/federal_register_bis_semiconductor.json", [d.__dict__ for d in fedreg.documents])
    results["federal_register_documents"] = len(fedreg.documents)

    fred = macro_fred.fetch_series("DGS10")
    _put_json(s3_client, f"{prefix}/fred_dgs10.json", fred.observations.to_dict())
    results["fred_observations"] = len(fred.observations)

    return {"statusCode": 200, "body": json.dumps(results)}
