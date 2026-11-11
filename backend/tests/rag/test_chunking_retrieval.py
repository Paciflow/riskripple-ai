from riskripple.rag.chunking import chunk_document, count_tokens, DEFAULT_CHUNK_TOKENS
from riskripple.rag.retrieval import LocalLexicalRetriever, build_evidence_context, deduplicate, RetrievedChunk


SAMPLE_TEXT = (
    "Paragraph one is about export controls and semiconductor restrictions on advanced "
    "computing chips.\n\n"
    "Paragraph two discusses supplier relationships with Taiwan Semiconductor "
    "Manufacturing Company and Samsung Electronics.\n\n"
    "Paragraph three is unrelated: it discusses office lease obligations and real "
    "estate commitments in California."
)


def test_chunk_document_produces_chunks_within_token_budget():
    chunks = chunk_document(document_id="doc1", text=SAMPLE_TEXT, chunk_tokens=30, overlap_tokens=5)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.token_count <= 30 + 5  # small slack for paragraph packing at the boundary
        assert c.document_id == "doc1"


def test_chunk_document_handles_oversized_paragraph():
    long_paragraph = "word " * 5000  # single paragraph, no blank-line breaks
    chunks = chunk_document(document_id="doc2", text=long_paragraph, chunk_tokens=200, overlap_tokens=20)
    assert len(chunks) > 1
    assert all(c.token_count <= 200 for c in chunks)


def test_chunk_document_empty_text_returns_no_chunks():
    assert chunk_document(document_id="doc3", text="   \n\n  ") == []


def test_count_tokens_nonzero_for_nonempty_text():
    assert count_tokens("hello world") > 0


def test_retriever_ranks_relevant_chunk_higher():
    chunks = chunk_document(document_id="doc1", text=SAMPLE_TEXT, chunk_tokens=40, overlap_tokens=5)
    retriever = LocalLexicalRetriever(chunks)
    results = retriever.retrieve("semiconductor export restrictions", top_k=3)
    assert len(results) > 0
    top_text = results[0].chunk.text.lower()
    assert "export" in top_text or "semiconductor" in top_text


def test_retriever_returns_nothing_for_unrelated_query():
    chunks = chunk_document(document_id="doc1", text=SAMPLE_TEXT, chunk_tokens=40, overlap_tokens=5)
    retriever = LocalLexicalRetriever(chunks)
    results = retriever.retrieve("quantum biology underwater basket weaving", top_k=3)
    assert results == []


def test_deduplicate_removes_identical_content_hash():
    chunks = chunk_document(document_id="doc1", text=SAMPLE_TEXT, chunk_tokens=40, overlap_tokens=5)
    duped = [RetrievedChunk(chunk=chunks[0], score=0.9), RetrievedChunk(chunk=chunks[0], score=0.5)]
    assert len(deduplicate(duped)) == 1


def test_build_evidence_context_includes_citation_markers():
    chunks = chunk_document(
        document_id="doc1", text=SAMPLE_TEXT, title="Test Filing", source_url="https://example.com/doc",
        chunk_tokens=40, overlap_tokens=5,
    )
    results = [RetrievedChunk(chunk=c, score=1.0) for c in chunks]
    context = build_evidence_context(results)
    assert "[1]" in context
    assert "Test Filing" in context
