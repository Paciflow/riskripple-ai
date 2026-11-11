"""Regulatory/geopolitical event detection via the Federal Register API.

Source: https://www.federalregister.gov/developers/documentation/api/v1
Free, no API key, no observed rate limiting. This is the feed for Agent 1 (Regulatory
Watchdog): official U.S. government rule publications, filterable by agency, that
directly cover export-control and sanctions actions -- e.g. BIS "Additions and
Revisions to the Entity List" -- rather than generic news noise that would need much
more work to establish as a reliable, citable source.

GDELT (api.gdeltproject.org) was evaluated as a broader geopolitical-news supplement
but rate-limits aggressively (HTTP 429 under light testing) and was not wired in;
revisit if broader-than-U.S. event coverage becomes a priority.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from riskripple.schemas.provenance import SourceMetadata

FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Agency slugs relevant to export-control / trade-restriction events (semiconductor
# scenario). See https://www.federalregister.gov/api/v1/agencies for the full list.
BIS_AGENCY_SLUG = "industry-and-security-bureau"
OFAC_AGENCY_SLUG = "foreign-assets-control-office"


@dataclass
class RegulatoryDocument:
    document_number: str
    title: str
    publication_date: str
    agencies: list[str]
    document_url: str
    abstract: str | None


@dataclass
class RegulatoryDocumentsResult:
    documents: list[RegulatoryDocument]
    metadata: SourceMetadata


def search_documents(
    *,
    term: str,
    agency_slugs: list[str] | None = None,
    per_page: int = 20,
    client: httpx.Client | None = None,
) -> RegulatoryDocumentsResult:
    """Search Federal Register publications by keyword and (optionally) agency.

    Used to detect new/changed regulatory events relevant to a sector or jurisdiction,
    e.g. term="semiconductor export" + agency_slugs=[BIS_AGENCY_SLUG].
    """
    params: dict[str, object] = {
        "conditions[term]": term,
        "per_page": per_page,
        "order": "newest",
    }
    if agency_slugs:
        params["conditions[agencies][]"] = agency_slugs

    own_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        resp = client.get(FEDERAL_REGISTER_API_URL, params=params)
        resp.raise_for_status()
    finally:
        if own_client:
            client.close()

    raw = resp.content
    payload = resp.json()

    documents = [
        RegulatoryDocument(
            document_number=r["document_number"],
            title=r["title"],
            publication_date=r["publication_date"],
            agencies=[a.get("name", "") for a in r.get("agencies", [])],
            document_url=r.get("html_url", ""),
            abstract=r.get("abstract"),
        )
        for r in payload.get("results", [])
    ]

    metadata = SourceMetadata(
        source_name="Federal Register API (federalregister.gov)",
        source_url=str(resp.url),
        retrieved_at=datetime.now(timezone.utc),
        data_version=hashlib.sha256(raw).hexdigest()[:16],
        content_hash=hashlib.sha256(raw).hexdigest(),
        license_or_restriction="U.S. government public domain publication; official and free, no API key required.",
    )
    return RegulatoryDocumentsResult(documents=documents, metadata=metadata)
