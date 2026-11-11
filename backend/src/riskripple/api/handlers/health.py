"""GET /health"""
from __future__ import annotations

from riskripple.api.responses import json_response


def handler(event: dict, context) -> dict:
    return json_response(200, {"status": "ok", "service": "riskripple-ai"})
