"""Storage interface: Lambda handlers depend on this Protocol, not on boto3 directly,
so the same handler code runs against DynamoDB in AWS and against an in-memory store
in local tests (master spec section 19: "Use dependency injection or interfaces for
external providers"). Shaped closely after DynamoDB's own item/key/query semantics
so the DynamoDB-backed implementation is a thin pass-through, not a translation layer.
"""
from __future__ import annotations

from typing import Protocol


class Store(Protocol):
    def put_item(self, table_name: str, item: dict) -> None: ...
    def get_item(self, table_name: str, key: dict) -> dict | None: ...
    def query_index(
        self, table_name: str, index_name: str, partition_key_name: str, partition_key_value: str
    ) -> list[dict]: ...
