from app.rag import build_context, chunk_text, RetrievedChunk


def test_chunk_text_with_overlap():
    text = "one two three four five six seven eight nine ten"
    chunks = chunk_text(text, chunk_size=4, overlap=1)
    assert chunks[0] == "one two three four"
    assert chunks[1].startswith("four")
    assert len(chunks) >= 2


def test_build_context():
    chunks = [
        RetrievedChunk(text="alpha", source="doc.txt", chunk_index=0, score=0.9),
        RetrievedChunk(text="beta", source="doc.txt", chunk_index=1, score=0.8),
    ]
    context = build_context(chunks)
    assert "Source: doc.txt" in context
    assert "alpha" in context
    assert "beta" in context
