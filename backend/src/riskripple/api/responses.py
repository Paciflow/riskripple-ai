"""API Gateway (Lambda proxy integration) response helpers."""
from __future__ import annotations

import json
from typing import Any

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def json_response(status_code: int, body: Any) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **_CORS_HEADERS},
        "body": json.dumps(body, default=str),
    }


def error_response(status_code: int, message: str) -> dict:
    return json_response(status_code, {"error": message})
