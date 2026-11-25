# services/agent_service.py – Phase 1 stub
# Orchestrates a full conversation turn. Full logic added in Phase 2.

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from models import Call, Lead, Message
from schemas import CallStartResponse, TurnResponse, EndCallResponse

logger = logging.getLogger(__name__)

GREETING = (
    "Hi! I'm Nova, your NovaCRM assistant. "
    "I'd love to help you discover how NovaCRM can streamline your sales. "
    "May I know your name?"
)


class AgentService:
    async def start_call(self, db: Session) -> CallStartResponse:
        call = Call(language="en-IN")
        db.add(call)
        db.flush()

        # Create a blank lead record immediately so other services can update it
        lead = Lead(call_id=call.id)
        db.add(lead)

        # Store the greeting as the first assistant message
        db.add(Message(call_id=call.id, role="assistant", text=GREETING, sentiment="positive"))
        db.commit()
        db.refresh(call)

        return CallStartResponse(call_id=call.id, reply=GREETING)

    async def handle_turn(self, call_id: int, text: str, language: str, db: Session):
        """Stub – returns a placeholder until Phase 2."""
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None
        reply = "Thanks! Full conversation logic coming in Phase 2."
        return TurnResponse(reply=reply, sentiment="neutral", sources=[])

    async def end_call(self, call_id: int, db: Session):
        """Stub – returns a placeholder until Phase 6."""
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None
        call.ended_at = datetime.utcnow()
        db.commit()
        return EndCallResponse(
            summary="Call ended. Full summary in Phase 6.",
            insights="{}",
            overall_sentiment="neutral",
        )


agent_service = AgentService()
