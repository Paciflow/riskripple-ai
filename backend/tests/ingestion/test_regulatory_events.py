from __future__ import annotations

import httpx

from riskripple.ingestion import regulatory_events as RE


def _make_client(term_to_results: dict[str, list[dict]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        term = httpx.QueryParams(request.url.query.decode())["conditions[term]"]
        return httpx.Response(200, json={"results": term_to_results.get(term, [])})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _doc(number: str, title: str) -> dict:
    return {
        "document_number": number,
        "title": title,
        "publication_date": "2026-01-01",
        "agencies": [{"name": "Bureau of Industry and Security"}],
        "html_url": f"https://example.gov/{number}",
        "abstract": "",
    }


def test_search_documents_multi_dedupes_across_terms():
    client = _make_client(
        {
            "semiconductor export": [_doc("A-1", "Shared doc"), _doc("A-2", "Only in term A")],
            "rare earth": [_doc("A-1", "Shared doc"), _doc("B-1", "Only in term B")],
        }
    )

    result = RE.search_documents_multi(terms=["semiconductor export", "rare earth"], client=client)

    assert {d.document_number for d in result.documents} == {"A-1", "A-2", "B-1"}


def test_search_documents_multi_defaults_to_the_broader_term_list():
    client = _make_client({term: [_doc(f"{i}", term)] for i, term in enumerate(RE.DEFAULT_REGULATORY_SEARCH_TERMS)})

    result = RE.search_documents_multi(client=client)

    assert len(result.documents) == len(RE.DEFAULT_REGULATORY_SEARCH_TERMS)
    assert "semiconductor export" in RE.DEFAULT_REGULATORY_SEARCH_TERMS
