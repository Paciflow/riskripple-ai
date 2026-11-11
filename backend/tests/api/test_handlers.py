import json
from pathlib import Path

import pytest

from riskripple.api.handlers import analyses, health

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="demo data snapshot not built (run scripts/build_demo_snapshot.py)"
)


def test_health_handler():
    resp = health.handler({}, None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "ok"


def test_analyses_post_then_get_round_trip():
    post_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "portfolio_weights": {"SPY": 0.5, "AGG": 0.5},
            "portfolio_value": 100_000.0,
            "event_title": "semiconductor export restrictions",
            "event_entities": ["TSMC"],
        }),
    }
    post_resp = analyses.handler(post_event, None)
    assert post_resp["statusCode"] == 201
    payload = json.loads(post_resp["body"])
    analysis_id = payload["analysis"]["analysis_id"]

    get_event = {"httpMethod": "GET", "pathParameters": {"analysis_id": analysis_id}}
    get_resp = analyses.handler(get_event, None)
    assert get_resp["statusCode"] == 200
    assert json.loads(get_resp["body"])["analysis_id"] == analysis_id


def test_analyses_post_rejects_bad_weights():
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "portfolio_weights": {"SPY": 0.9},
            "event_title": "test",
        }),
    }
    resp = analyses.handler(event, None)
    assert resp["statusCode"] == 400


def test_analyses_get_missing_id_returns_404():
    event = {"httpMethod": "GET", "pathParameters": {"analysis_id": "does-not-exist"}}
    resp = analyses.handler(event, None)
    assert resp["statusCode"] == 404
