from riskripple.graph.company_graph import (
    extract_supplier_edges_from_filing_text,
    build_graph,
    find_direct_exposure,
    traverse_relationships,
    export_graph_json,
)


SAMPLE_FILING_TEXT = (
    "We utilize foundries, such as Taiwan Semiconductor Manufacturing Company Limited, "
    "or TSMC, and Samsung Electronics Co., Ltd., or Samsung, to produce our semiconductor "
    "wafers. We purchase memory from SK Hynix Inc., Micron Technology, Inc., and Samsung. "
    "Our competitors include many companies with no known supply relationship to us."
)


def test_extract_supplier_edges_finds_known_suppliers_with_evidence():
    edges = extract_supplier_edges_from_filing_text(
        company_symbol="NVDA", filing_text=SAMPLE_FILING_TEXT, evidence_label="NVDA 10-K"
    )
    targets = {e.target for e in edges}
    assert {"TSMC", "Samsung", "SK Hynix", "Micron"}.issubset(targets)
    for e in edges:
        assert e.source == "NVDA"
        assert e.relationship_type == "supplier"
        assert e.confidence == "verified"
        assert "NVDA 10-K" in e.evidence_source


def test_extract_supplier_edges_ignores_unmentioned_companies():
    edges = extract_supplier_edges_from_filing_text(
        company_symbol="NVDA", filing_text=SAMPLE_FILING_TEXT, evidence_label="NVDA 10-K"
    )
    targets = {e.target for e in edges}
    assert "Hon Hai (Foxconn)" not in targets  # never mentioned in this sample text


def test_graph_traversal_direct_and_indirect_exposure():
    edges = extract_supplier_edges_from_filing_text(
        company_symbol="NVDA", filing_text=SAMPLE_FILING_TEXT, evidence_label="NVDA 10-K"
    )
    graph = build_graph(edges)

    direct = find_direct_exposure(graph, event_entities=["TSMC", "NonExistentCo"])
    assert direct == ["TSMC"]

    distances = traverse_relationships(graph, start_nodes=["TSMC"], max_hops=1)
    assert distances.get("NVDA") == 1


def test_export_graph_json_shape():
    edges = extract_supplier_edges_from_filing_text(
        company_symbol="NVDA", filing_text=SAMPLE_FILING_TEXT, evidence_label="NVDA 10-K"
    )
    graph = build_graph(edges)
    payload = export_graph_json(graph, highlight_nodes=["TSMC"])
    assert any(n["id"] == "TSMC" and n["highlighted"] for n in payload["nodes"])
    assert all("relationship_type" in e for e in payload["edges"])
