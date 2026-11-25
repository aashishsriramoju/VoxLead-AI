# api/call.py – HTTP endpoints for call lifecycle
# Rule: only receives requests and delegates to services. No business logic here.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import CallStartResponse, TurnRequest, TurnResponse, EndCallResponse
from services.agent_service import agent_service

router = APIRouter()


@router.post("/start", response_model=CallStartResponse)
async def start_call(db: Session = Depends(get_db)):
    """
    Create a new call session and return the agent's opening greeting.
    The frontend stores call_id and uses it for all subsequent /turn calls.
    """
    result = await agent_service.start_call(db)
    return result


@router.post("/{call_id}/turn", response_model=TurnResponse)
async def conversation_turn(
    call_id: int,
    body: TurnRequest,
    db: Session = Depends(get_db),
):
    """
    Process one conversation turn:
    user speaks → STT in browser → text sent here → LLM reply → TTS in browser.
    """
    result = await agent_service.handle_turn(call_id, body.text, body.language, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return result


@router.post("/{call_id}/end", response_model=EndCallResponse)
async def end_call(call_id: int, db: Session = Depends(get_db)):
    """
    End the call: generate and store a summary + insights via Gemini.
    """
    result = await agent_service.end_call(call_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return result
