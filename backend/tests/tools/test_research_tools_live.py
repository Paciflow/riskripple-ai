from __future__ import annotations

from unittest.mock import patch

from riskripple.ingestion.filings_sec import FullTextSearchHit, FullTextSearchResult
from riskripple.schemas.provenance import SourceMetadata
from riskripple.tools.research_tools import search_sec_edgar_live


def _fake_metadata() -> SourceMetadata:
    from datetime import datetime, timezone

    return SourceMetadata(
        source_name="SEC EDGAR full-text search (efts.sec.gov)", source_url="https://example.com",
        retrieved_at=datetime.now(timezone.utc), data_version="x", content_hash="x",
        license_or_restriction="test",
    )


def test_search_sec_edgar_live_does_not_raise_a_nameerror_building_the_date_range():
    # Regression: an earlier version used datetime/timedelta without importing them
    # at module level, which raised NameError on every call -- only caught during a
    # live agent run, not by any existing test (none of them actually called this
    # function). This test calls the real function; it must not raise regardless of
    # what search_filings_fulltext returns.
    hit = FullTextSearchHit(
        entity_name="INTEL CORP", cik="0000050863", accession_number="0000050863-24-000010",
        form_type="10-K", filing_date="2024-01-26", primary_document="intc-20231230.htm",
        document_url="https://example.com/intc.htm",
    )
    with patch(
        "riskripple.tools.research_tools.filings_sec.search_filings_fulltext",
        return_value=FullTextSearchResult(hits=[hit], metadata=_fake_metadata()),
    ), patch(
        "riskripple.tools.research_tools.filings_sec.fetch_filing_text",
        return_value=("...direct copper-to-copper bonding for low-resistance interconnects...", _fake_metadata()),
    ):
        result = search_sec_edgar_live("copper", entity_name="Intel")

    assert result["found"] is True
    assert "error" not in result
    assert "copper" in result["evidence_snippet"].lower()


def test_search_sec_edgar_live_returns_a_clean_error_instead_of_raising():
    with patch(
        "riskripple.tools.research_tools.filings_sec.search_filings_fulltext",
        side_effect=RuntimeError("simulated network failure"),
    ):
        result = search_sec_edgar_live("copper", entity_name="Intel")

    assert result["found"] is False
    assert "simulated network failure" in result["error"]
