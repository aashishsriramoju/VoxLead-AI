# services/rag_service.py – Phase 1 stub
# Full RAG pipeline (load, embed, retrieve) added in Phase 3.

import logging
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.chunks = []   # list of dicts: {text, file, section, embedding}

    async def load(self, force_reload: bool = False):
        """Phase 1 stub: does nothing yet."""
        logger.info("RAG service stub: no documents loaded yet (Phase 3 will implement this)")

    async def retrieve(self, query: str):
        """Return top-k chunks for the query. Stub returns empty list."""
        return []


rag_service = RAGService()
