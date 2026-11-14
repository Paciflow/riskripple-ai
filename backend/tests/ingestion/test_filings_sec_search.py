from __future__ import annotations

import httpx

from riskripple.ingestion import filings_sec as FS

# Real response shape captured from a live efts.sec.gov call (2026-11-14) searching
# "copper" scoped to Intel -- trimmed to the fields the parser actually uses.
_REAL_SHAPED_HIT = {
    "_id": "0000050863-24-000010:intc-20231230.htm",
    "_source": {
        "ciks": ["0000050863"],
        "display_names": ["INTEL CORP  (INTC)  (CIK 0000050863)"],
        "form": "10-K",
        "file_date": "2024-01-26",
    },
}


def _mock_client(hits: list[dict]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"hits": {"hits": hits}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_filings_fulltext_parses_a_real_response_shape():
    client = _mock_client([_REAL_SHAPED_HIT])

    result = FS.search_filings_fulltext("copper", entity_name="Intel", client=client)

    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.entity_name == "INTEL CORP  (INTC)  (CIK 0000050863)"
    assert hit.cik == "0000050863"
    assert hit.accession_number == "0000050863-24-000010"
    assert hit.primary_document == "intc-20231230.htm"
    assert hit.document_url == (
        "https://www.sec.gov/Archives/edgar/data/50863/000005086324000010/intc-20231230.htm"
    )


def test_search_filings_fulltext_no_hits():
    client = _mock_client([])

    result = FS.search_filings_fulltext("a term nobody filed", client=client)

    assert result.hits == []
