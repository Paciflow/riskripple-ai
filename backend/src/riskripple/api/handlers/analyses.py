"""POST /api/analyses, GET /api/analyses/{analysis_id}

Simplification for the hackathon demo: this Lambda runs the investigation
synchronously (the local orchestrator completes in ~1-2s against the frozen demo
data), rather than starting the Step Functions execution and polling. The production
path described in docs/ARCHITECTURE.md (API starts a Step Functions execution,
returns an id immediately, frontend polls /status) is implemented in
infrastructure/cdk/lib/workflow-stack.ts but not yet wired to this handler --
wiring it through requires confirming bedrock:InvokeModel access on the hackathon
account first (see docs/KNOWN_LIMITATIONS.md).
"""
from __future__ import annotations

import json

from riskripple.api.responses import error_response, json_response
from riskripple.storage import get_store
from riskripple.workflows.local_orchestrator import run_investigation

ANALYSES_TABLE = "riskripple-analyses"


def _handle_post(body: dict) -> dict:
    try:
        analysis, report = run_investigation(
            portfolio_weights=body["portfolio_weights"],
            portfolio_value=body.get("portfolio_value", 100_000.0),
            event_title=body["event_title"],
            event_entities=body.get("event_entities", []),
            persona_names=body.get("personas"),
        )
    except (KeyError, ValueError) as exc:
        return error_response(400, str(exc))

    store = get_store()
    store.put_item(ANALYSES_TABLE, {**analysis.model_dump(), "report": report.model_dump()})

    return json_response(201, {"analysis": analysis.model_dump(), "report": report.model_dump()})


def _handle_get(analysis_id: str) -> dict:
    store = get_store()
    item = store.get_item(ANALYSES_TABLE, {"analysis_id": analysis_id})
    if item is None:
        return error_response(404, f"analysis {analysis_id} not found")
    return json_response(200, item)


def handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "POST")
    if method == "GET":
        analysis_id = (event.get("pathParameters") or {}).get("analysis_id")
        if not analysis_id:
            return error_response(400, "missing analysis_id path parameter")
        return _handle_get(analysis_id)

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "invalid JSON body")
    return _handle_post(body)
