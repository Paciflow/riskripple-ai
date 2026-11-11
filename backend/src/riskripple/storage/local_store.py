"""In-memory Store implementation for local development and tests. Not persisted
across process restarts -- that's intentional; it exists so handler logic can be
exercised without any AWS dependency."""
from __future__ import annotations

from collections import defaultdict


class LocalStore:
    def __init__(self) -> None:
        self._tables: dict[str, dict[tuple, dict]] = defaultdict(dict)

    @staticmethod
    def _key_tuple(key: dict) -> tuple:
        return tuple(sorted(key.items()))

    def put_item(self, table_name: str, item: dict) -> None:
        # Assumes the first key in the item that looks like an id field is the
        # partition key; callers that need a specific key should use the dict form.
        pk_field = next((k for k in item if k.endswith("_id")), next(iter(item)))
        self._tables[table_name][self._key_tuple({pk_field: item[pk_field]})] = dict(item)

    def get_item(self, table_name: str, key: dict) -> dict | None:
        return self._tables[table_name].get(self._key_tuple(key))

    def query_index(
        self, table_name: str, index_name: str, partition_key_name: str, partition_key_value: str
    ) -> list[dict]:
        return [
            item for item in self._tables[table_name].values()
            if item.get(partition_key_name) == partition_key_value
        ]
