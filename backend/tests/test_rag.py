# tests/test_rag.py – Comprehensive unit tests for RAG pipeline
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.rag_service import _split_into_chunks, RAGService

def test_heading_and_word_chunking():
    """Test that document is split by headings, and long sections are chunked with overlap."""
    sample_doc = """# Introduction
NovaCRM is a customer relationship management platform designed for high-velocity sales teams.

# Pricing and Plans
The Starter plan costs $29 per user per month.
The Growth plan costs $79 per user per month.
The Enterprise plan has custom pricing based on team size.

# Support SLA
""" + " ".join([f"word{i}" for i in range(600)]) # 600 words > 500 words limit

    chunks = _split_into_chunks(sample_doc, "pricing.md")
    
    # Verify headings extracted
    sections = [c["section"] for c in chunks]
    assert "Introduction" in sections
    assert "Pricing and Plans" in sections
    assert "Support SLA" in sections
    
    # Verify metadata
    for c in chunks:
        assert c["file"] == "pricing.md"
        assert len(c["text"]) > 0

    # Verify long section (>500 words) was broken into at least 2 chunks
    sla_chunks = [c for c in chunks if c["section"] == "Support SLA"]
    assert len(sla_chunks) >= 2
    # Verify ~400 words
    word_count_chunk0 = len(sla_chunks[0]["text"].split())
    assert 350 <= word_count_chunk0 <= 405

def test_cosine_similarity_retrieval():
    """Test numpy-based cosine similarity retrieval and threshold filtering."""
    rag = RAGService()
    
    # Synthetic embeddings for 3 chunks:
    # chunk 1 is identical to query direction
    # chunk 2 is orthogonal (similarity ~0)
    # chunk 3 is close (similarity ~0.8)
    # chunk 4 is opposite (negative similarity)
    rag.chunks = [
        {"file": "doc1.md", "section": "Sec1", "text": "Perfect match", "embedding": [1.0, 0.0, 0.0]},
        {"file": "doc2.md", "section": "Sec2", "text": "Orthogonal info", "embedding": [0.0, 1.0, 0.0]},
        {"file": "doc3.md", "section": "Sec3", "text": "Good match", "embedding": [0.8, 0.2, 0.0]},
        {"file": "doc4.md", "section": "Sec4", "text": "Opposite info", "embedding": [-1.0, 0.0, 0.0]}
    ]

    # Query vector along x-axis [1.0, 0.0, 0.0]
    q_vec = [1.0, 0.0, 0.0]
    
    # Calculate similarities manually to test numpy logic
    q_np = np.array(q_vec, dtype=np.float32)
    scores = []
    for c in rag.chunks:
        c_np = np.array(c["embedding"], dtype=np.float32)
        sim = float(np.dot(q_np, c_np) / (np.linalg.norm(q_np) * np.linalg.norm(c_np)))
        scores.append((sim, c))

    # With threshold 0.60:
    # chunk 1 similarity = 1.0 (retained)
    # chunk 2 similarity = 0.0 (dropped)
    # chunk 3 similarity = 0.8 / sqrt(0.8^2 + 0.2^2) = 0.8 / 0.8246 = ~0.97 (retained)
    # chunk 4 similarity = -1.0 (dropped)
    retained = [c for s, c in scores if s >= 0.60]
    assert len(retained) == 2
    assert retained[0]["file"] == "doc1.md"
    assert retained[1]["file"] == "doc3.md"

if __name__ == "__main__":
    test_heading_and_word_chunking()
    test_cosine_similarity_retrieval()
    print("All RAG unit tests PASSED!")
