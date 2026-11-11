"""DynamoDB-backed Store implementation. UNTESTED LIVE: this account's IAM user
does not have dynamodb permissions verified end-to-end (see
docs/KNOWN_LIMITATIONS.md); verify against the hackathon account before relying on it."""
from __future__ import annotations

import boto3


class DynamoStore:
    def __init__(self, region_name: str | None = None):
        self._resource = boto3.resource("dynamodb", region_name=region_name)

    def put_item(self, table_name: str, item: dict) -> None:
        self._resource.Table(table_name).put_item(Item=item)

    def get_item(self, table_name: str, key: dict) -> dict | None:
        response = self._resource.Table(table_name).get_item(Key=key)
        return response.get("Item")

    def query_index(
        self, table_name: str, index_name: str, partition_key_name: str, partition_key_value: str
    ) -> list[dict]:
        from boto3.dynamodb.conditions import Key

        response = self._resource.Table(table_name).query(
            IndexName=index_name,
            KeyConditionExpression=Key(partition_key_name).eq(partition_key_value),
        )
        return response.get("Items", [])
