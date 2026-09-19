from agent.agents.rag.augmentation import augment, rerank_chunks
from agent.tools.embedding_tools import chunk_text


def test_chunk_text_splits_on_paragraphs_and_respects_size():
    text = "First paragraph with some content.\n\nSecond paragraph with larger content that should continue.\n\nThird paragraph."
    chunks = chunk_text(text, size=40, overlap=10)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 60 for chunk in chunks)


def test_rerank_chunks_prefers_report_when_question_is_about_rejection():
    chunks = [
        {"text": "A regular invoice note", "score": 0.71, "source_type": "invoice", "invoice_number": "INV-100"},
        {"text": "The invoice was rejected for a price mismatch", "score": 0.72, "source_type": "report", "invoice_number": "INV-100"},
    ]

    ranked = rerank_chunks("Why was invoice INV-100 rejected?", chunks)
    assert ranked[0]["source_type"] == "report"
    assert ranked[0]["final_score"] >= ranked[1]["final_score"]


def test_augment_deduplicates_and_limits_chars():
    chunks = [
        {"text": "Duplicate text", "score": 0.9, "source_type": "report", "invoice_id": "abc", "invoice_number": "INV-100"},
        {"text": "Duplicate text", "score": 0.9, "source_type": "report", "invoice_id": "abc", "invoice_number": "INV-100"},
        {"text": "Another invoice note", "score": 0.8, "source_type": "invoice", "invoice_id": "def", "invoice_number": "INV-200"},
    ]

    blocks = augment("Why was invoice INV-100 rejected?", chunks, max_chars=250)
    assert any("INV-100" in block for block in blocks)
    assert len("\n".join(blocks)) <= 300
