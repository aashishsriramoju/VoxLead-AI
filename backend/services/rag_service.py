# services/rag_service.py – Lightweight RAG pipeline (No LangChain, No ChromaDB)
#
# Architecture:
# 1. Document Loader: Reads .md, .txt, and .pdf (via pypdf) from backend/knowledge_base/
# 2. Splitter: Splits by headings first, then into ~400-word chunks with ~50-word overlap
# 3. Embedding & Caching: Hashes files with SHA-256; caches vectors in .cache.json
# 4. Retrieval: Cosine similarity via numpy, drops chunks below threshold, returns top-4

import os
import re
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional

import numpy as np
from pypdf import PdfReader

from config import (
    RAG_SIMILARITY_THRESHOLD,
    RAG_TOP_K,
)
from services import llm_service

logger = logging.getLogger(__name__)

KB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledge_base"))
CACHE_FILE = os.path.join(KB_DIR, ".cache.json")


def _calculate_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of a file to detect content changes."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _split_into_chunks(text: str, filename: str) -> List[Dict[str, str]]:
    """
    Split document text by headings first.
    For sections > 500 words, split into ~400-word chunks with 50-word overlap.
    """
    chunks: List[Dict[str, str]] = []
    
    # Identify markdown headings (# Heading, ## Heading, etc.)
    heading_pattern = re.compile(r"^(#{1,6}\s+.*)$", re.MULTILINE)
    parts = heading_pattern.split(text)
    
    current_section = "General"
    sections: List[tuple[str, str]] = []
    
    # If the document starts without a heading
    idx = 0
    if parts and not heading_pattern.match(parts[0]):
        first_part = parts[0].strip()
        if first_part:
            sections.append((current_section, first_part))
        idx = 1
        
    while idx < len(parts):
        part = parts[idx].strip()
        if heading_pattern.match(part):
            current_section = part.lstrip("#").strip()
            content = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
            if content:
                sections.append((current_section, content))
            idx += 2
        else:
            if part:
                sections.append((current_section, part))
            idx += 1

    if not sections and text.strip():
        sections = [("General", text.strip())]

    # Now chunk any section over ~500 words into ~400 words with 50-word overlap
    for section_name, section_text in sections:
        words = section_text.split()
        if len(words) <= 500:
            chunks.append({
                "file": filename,
                "section": section_name,
                "text": section_text.strip()
            })
        else:
            chunk_size = 400
            overlap = 50
            step = chunk_size - overlap  # 350 words step
            for start_idx in range(0, len(words), step):
                chunk_words = words[start_idx : start_idx + chunk_size]
                if not chunk_words:
                    break
                chunks.append({
                    "file": filename,
                    "section": section_name,
                    "text": " ".join(chunk_words).strip()
                })
                if start_idx + chunk_size >= len(words):
                    break

    return chunks


class RAGService:
    def __init__(self):
        # In-memory vector store: list of dicts with {file, section, text, embedding}
        self.chunks: List[Dict[str, Any]] = []

    def _extract_text_from_file(self, filepath: str) -> str:
        """Extract plain text from .md, .txt, or .pdf files."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in [".md", ".txt"]:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            try:
                reader = PdfReader(filepath)
                text_parts = [page.extract_text() or "" for page in reader.pages]
                return "\n".join(text_parts)
            except Exception as e:
                logger.error(f"Failed to read PDF {filepath}: {e}")
                return ""
        return ""

    async def load(self, force_reload: bool = False):
        """
        Load knowledge base documents, split into chunks, embed and cache.
        If files haven't changed and cache exists, load from cache.
        """
        if not os.path.exists(KB_DIR):
            logger.warning(f"Knowledge base directory '{KB_DIR}' does not exist.")
            return

        supported_exts = {".md", ".txt", ".pdf"}
        kb_files = [
            f for f in os.listdir(KB_DIR)
            if os.path.splitext(f)[1].lower() in supported_exts and not f.startswith(".")
        ]

        if not kb_files:
            logger.warning(
                "Knowledge base folder is empty! No company documents found (.md, .txt, .pdf). "
                "Place documents in backend/knowledge_base/ and call POST /api/kb/reload."
            )
            self.chunks = []
            return

        # Check current file hashes
        current_hashes: Dict[str, str] = {}
        for fname in kb_files:
            fpath = os.path.join(KB_DIR, fname)
            current_hashes[fname] = _calculate_file_hash(fpath)

        # Check cache validity
        cache_valid = False
        if not force_reload and os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                cached_hashes = cache_data.get("file_hashes", {})
                if cached_hashes == current_hashes and "chunks" in cache_data:
                    self.chunks = cache_data["chunks"]
                    logger.info(f"Loaded {len(self.chunks)} RAG chunks from cache ({CACHE_FILE}).")
                    cache_valid = True
            except Exception as e:
                logger.warning(f"Failed to load cache, re-indexing: {e}")

        if cache_valid:
            return

        # Need to re-index and re-embed
        logger.info("Indexing knowledge base files...")
        all_chunks: List[Dict[str, Any]] = []

        for fname in kb_files:
            fpath = os.path.join(KB_DIR, fname)
            raw_text = self._extract_text_from_file(fpath)
            if not raw_text.strip():
                continue
            doc_chunks = _split_into_chunks(raw_text, fname)
            all_chunks.extend(doc_chunks)

        logger.info(f"Generated {len(all_chunks)} chunks across {len(kb_files)} files. Embedding chunks...")

        # Embed each chunk using Gemini embedding model
        embedded_chunks = []
        for i, chunk in enumerate(all_chunks):
            embedding = await llm_service.embed(chunk["text"])
            if embedding is not None:
                chunk["embedding"] = embedding
                embedded_chunks.append(chunk)
            else:
                logger.warning(f"Failed to embed chunk {i+1}/{len(all_chunks)} from {chunk['file']}")

        self.chunks = embedded_chunks

        # Save to cache
        try:
            cache_payload = {
                "file_hashes": current_hashes,
                "chunks": self.chunks
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_payload, f)
            logger.info(f"Cached {len(self.chunks)} chunks to {CACHE_FILE}.")
        except Exception as e:
            logger.error(f"Failed to write cache file: {e}")

    async def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Embed the user query and retrieve top-K chunks by cosine similarity.
        Chunks with similarity < RAG_SIMILARITY_THRESHOLD are dropped.
        """
        if not self.chunks or not query.strip():
            return []

        # 1. Embed user query
        query_vec = await llm_service.embed(query)
        if query_vec is None:
            logger.warning("Could not embed search query. Returning empty RAG results.")
            return []

        q_np = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_np)
        if q_norm == 0:
            return []

        scored_chunks: List[tuple[float, Dict[str, Any]]] = []

        # 2. Compute cosine similarity for each chunk
        for chunk in self.chunks:
            c_vec = chunk.get("embedding")
            if not c_vec:
                continue
            c_np = np.array(c_vec, dtype=np.float32)
            c_norm = np.linalg.norm(c_np)
            if c_norm == 0:
                continue

            similarity = float(np.dot(q_np, c_np) / (q_norm * c_norm))
            
            # 3. Filter by similarity threshold
            if similarity >= RAG_SIMILARITY_THRESHOLD:
                scored_chunks.append((similarity, chunk))

        # 4. Sort descending by similarity
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # 5. Return top K
        results: List[Dict[str, Any]] = []
        for score, chunk in scored_chunks[:RAG_TOP_K]:
            results.append({
                "file": chunk["file"],
                "section": chunk["section"],
                "text": chunk["text"],
                "score": score
            })

        return results


# Global singleton instance
rag_service = RAGService()
