# api/kb.py – Knowledge-base management endpoints

from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/reload")
async def reload_knowledge_base():
    """
    Re-index the knowledge base after adding or changing files.
    Call this after dropping new .md, .txt, or .pdf files into knowledge_base/.
    """
    from services.rag_service import rag_service
    await rag_service.load(force_reload=True)
    return {"status": "reloaded", "chunks": len(rag_service.chunks)}
