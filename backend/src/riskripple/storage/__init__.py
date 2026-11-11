"""Store factory: picks the DynamoDB-backed store when running in Lambda (AWS_EXECUTION_ENV
is set), otherwise an in-memory store for local development and tests."""
from __future__ import annotations

import os

from riskripple.storage.base import Store
from riskripple.storage.local_store import LocalStore

_singleton: Store | None = None


def get_store() -> Store:
    global _singleton
    if _singleton is None:
        if os.environ.get("AWS_EXECUTION_ENV") or os.environ.get("RISKRIPPLE_USE_DYNAMO"):
            from riskripple.storage.dynamo_store import DynamoStore

            _singleton = DynamoStore(region_name=os.environ.get("AWS_REGION"))
        else:
            _singleton = LocalStore()
    return _singleton
