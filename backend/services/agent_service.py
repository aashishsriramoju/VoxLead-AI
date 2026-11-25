# services/agent_service.py – Conversation orchestrator
#
# This is the brain of VoxLead AI. It runs one full "turn":
#   1. Load message history from DB (memory)
#   2. Retrieve relevant FAQ chunks (RAG – called here, implemented in Phase 3)
#   3. Build the prompt and call Gemini
#   4. Parse + validate Gemini's JSON response (with retry + fallback)
#   5. Update the lead record with any new qualification fields
#   6. If Gemini requested a slot action, call booking_service
#   7. Store both messages (user + assistant) in DB
#   8. Return the final TurnResponse to the API layer

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import Call, Message, Lead
from schemas import (
    CallStartResponse, TurnResponse, EndCallResponse,
    LLMResponse, LeadFields, LeadOut, AppointmentOut, SourceChunk,
)
from services import llm_service
from services.booking_service import booking_service
from services.lead_service import lead_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt – the agent's personality and strict rules
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Nova, a friendly and concise sales representative for NovaCRM,
a CRM software platform for growing sales teams.

STRICT RULES:
1. Reply in max 2 SHORT sentences — replies will be spoken aloud.
2. Answer product/pricing/policy questions ONLY from the <context> block below.
   If the answer is not in <context>, say: "I'll have a colleague follow up on that."
3. Ask ONE qualification question at a time: team size → budget → timeline → requirements.
4. Collect the customer's NAME and PHONE before attempting to book a demo.
5. NEVER invent prices, features, discounts, or legal commitments.
6. Reply in the SAME LANGUAGE the customer uses (English, Hindi, or Telugu).
7. When answering from a document, mention the source: "According to our [document name]..."

OUTPUT FORMAT — you MUST return ONLY valid JSON, nothing else:
{
  "reply": "<your spoken reply, max 2 sentences>",
  "sentiment": "<positive|neutral|negative>",
  "lead_fields": {
    "name": "<string or null>",
    "phone": "<string or null>",
    "company": "<string or null>",
    "budget": <number in USD/month or null>,
    "team_size": <integer or null>,
    "requirements": "<string or null>",
    "timeline_days": <integer or null>
  },
  "action": "<none|check_slots|book_appointment>",
  "requested_slot": "<ISO datetime string or null>",
  "language": "<BCP-47 code, e.g. en-IN>"
}

Set lead_fields values to null if the customer did not mention them in this turn.
Set action to "check_slots" when the customer asks about availability.
Set action to "book_appointment" only when you have name, phone, AND a confirmed slot.
"""

# Safe fallback reply when Gemini fails or returns unparseable JSON
FALLBACK_REPLY = (
    "I'm sorry, I didn't catch that. Could you please repeat? "
    "I want to make sure I help you correctly."
)

# Greeting for the very first message of a call
GREETING = (
    "Hi! I'm Nova, your NovaCRM assistant. "
    "I'd love to show you how NovaCRM can supercharge your sales team. "
    "Could I start with your name?"
)


class AgentService:

    # -----------------------------------------------------------------------
    # start_call
    # -----------------------------------------------------------------------
    async def start_call(self, db: Session) -> CallStartResponse:
        """
        Create a Call row, a blank Lead row, and store the opening greeting.
        Returns call_id so the frontend can reference this session.
        """
        call = Call(language="en-IN")
        db.add(call)
        db.flush()  # flush to get call.id without committing

        lead = Lead(call_id=call.id)
        db.add(lead)

        # Store the greeting as the first assistant message
        db.add(Message(
            call_id=call.id,
            role="assistant",
            text=GREETING,
            sentiment="positive",
        ))
        db.commit()
        db.refresh(call)
        return CallStartResponse(call_id=call.id, reply=GREETING)

    # -----------------------------------------------------------------------
    # handle_turn – main entry point for each conversation step
    # -----------------------------------------------------------------------
    async def handle_turn(
        self,
        call_id: int,
        user_text: str,
        language: str,
        db: Session,
    ) -> Optional[TurnResponse]:

        # 1. Load the call; return None → 404 in the router
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        # Update the detected language on the call record
        call.language = language
        db.add(call)

        # 2. Load full message history for this call (this IS the memory)
        history_rows = (
            db.query(Message)
            .filter(Message.call_id == call_id)
            .order_by(Message.created_at)
            .all()
        )
        history = [{"role": m.role, "text": m.text} for m in history_rows]

        # 3. Retrieve relevant knowledge-base chunks (Phase 3; stub returns [])
        from services.rag_service import rag_service
        chunks = await rag_service.retrieve(user_text)

        # Build the <context> block injected into the system prompt
        context_block = self._build_context_block(chunks)
        full_system_prompt = SYSTEM_PROMPT + "\n\n" + context_block

        # 4. Call Gemini; get raw JSON string
        raw = await llm_service.generate(
            system_prompt=full_system_prompt,
            history=history,
            user_message=user_text,
        )

        # 5. Parse + validate with Pydantic; retry once on failure
        llm_resp = await self._parse_llm_response(raw, full_system_prompt, history, user_text)

        reply_text   = llm_resp.reply
        sentiment    = llm_resp.sentiment
        action       = llm_resp.action
        lead_fields  = llm_resp.lead_fields

        # 6. Update lead record with any newly extracted fields
        lead = db.query(Lead).filter(Lead.id == call.id).first()
        # Note: we find lead by call_id, not by its own id
        lead = db.query(Lead).filter(Lead.call_id == call_id).first()
        if not lead:
            lead = Lead(call_id=call_id)
            db.add(lead)
            db.flush()

        if lead_fields:
            self._merge_lead_fields(lead, lead_fields)

        # 7. Recompute lead score (deterministic, in lead_service)
        turn_count = len(history) + 1   # +1 for this turn
        lead = lead_service.update_and_score(lead, {}, sentiment, turn_count, db)

        # 8. Handle slot actions requested by the LLM
        appointment_out: Optional[AppointmentOut] = None

        if action == "check_slots":
            slots = booking_service.get_available_slots(db)
            if slots:
                slot_lines = "\n".join(
                    s.slot_start.strftime("• %A %d %b at %I:%M %p UTC") for s in slots[:5]
                )
                reply_text = f"Here are some available demo slots:\n{slot_lines}\nWhich works for you?"
            else:
                reply_text = "I'm sorry, there are no open slots right now. I'll have the team contact you."

        elif action == "book_appointment" and llm_resp.requested_slot:
            appt = booking_service.book_slot(lead.id, llm_resp.requested_slot, db)
            if appt:
                appointment_out = AppointmentOut.model_validate(appt)
                slot_str = appt.slot_start.strftime("%A %d %b at %I:%M %p UTC")
                reply_text = f"Great! Your demo is booked for {slot_str}. We'll send a confirmation shortly."
            else:
                reply_text = "That slot is no longer available. Let me show you other options."
                # Cascade to show slots
                slots = booking_service.get_available_slots(db)
                if slots:
                    slot_lines = "\n".join(
                        s.slot_start.strftime("• %A %d %b at %I:%M %p UTC") for s in slots[:5]
                    )
                    reply_text += f"\n{slot_lines}"

        # 9. Store both messages in DB
        db.add(Message(call_id=call_id, role="user",      text=user_text,   sentiment=sentiment))
        db.add(Message(call_id=call_id, role="assistant", text=reply_text,  sentiment="neutral"))
        db.commit()
        db.refresh(lead)

        # Build source references for the UI (Phase 3 fills these)
        sources = [
            SourceChunk(file=c["file"], section=c["section"], score=round(c["score"], 3))
            for c in chunks
        ]

        return TurnResponse(
            reply=reply_text,
            sentiment=sentiment,
            lead=LeadOut.model_validate(lead),
            score=lead.score,
            appointment=appointment_out,
            sources=sources,
        )

    # -----------------------------------------------------------------------
    # end_call
    # -----------------------------------------------------------------------
    async def end_call(self, call_id: int, db: Session) -> Optional[EndCallResponse]:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        call.ended_at = datetime.utcnow()
        db.commit()

        # Delegate to summary_service (Phase 6 fills this in fully)
        from services.summary_service import summary_service
        result = await summary_service.summarise(call_id, db)

        call.summary           = result["summary"]
        call.insights          = result["insights"]
        call.overall_sentiment = result["overall_sentiment"]
        db.commit()

        return EndCallResponse(
            summary=result["summary"],
            insights=result["insights"],
            overall_sentiment=result["overall_sentiment"],
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _build_context_block(self, chunks: list[dict]) -> str:
        """
        Format retrieved RAG chunks into a <context> block.
        The system prompt tells the LLM to answer only from this block.
        """
        if not chunks:
            return "<context>\nNo relevant company documents found for this query.\n</context>"

        lines = ["<context>"]
        for c in chunks:
            lines.append(f"[Source: {c['file']} > {c['section']}]")
            lines.append(c["text"])
            lines.append("")  # blank line between chunks
        lines.append("</context>")
        return "\n".join(lines)

    async def _parse_llm_response(
        self,
        raw: Optional[str],
        system_prompt: str,
        history: list[dict],
        user_message: str,
    ) -> LLMResponse:
        """
        Try to parse Gemini's raw string as LLMResponse.
        On failure: retry once with an explicit correction message.
        On second failure: return a safe fallback so the call never crashes.
        """
        # Attempt 1: parse the raw output directly
        parsed = self._try_parse(raw)
        if parsed:
            return parsed

        logger.warning("Gemini returned invalid JSON on first attempt; retrying...")

        # Attempt 2: re-call Gemini with an explicit nudge
        correction = (
            f"Your previous response was not valid JSON. "
            f"The original user message was: '{user_message}'. "
            f"Reply ONLY with the JSON object described in the system prompt. No markdown, no explanation."
        )
        raw2 = await llm_service.generate(
            system_prompt=system_prompt,
            history=history,
            user_message=correction,
        )
        parsed2 = self._try_parse(raw2)
        if parsed2:
            return parsed2

        logger.error("Gemini failed twice; using fallback reply")
        return LLMResponse(reply=FALLBACK_REPLY, sentiment="neutral")

    def _try_parse(self, raw: Optional[str]) -> Optional[LLMResponse]:
        """
        Parse and validate the JSON string.
        Returns None on any parse or validation error.
        """
        if not raw:
            return None
        try:
            # Strip markdown code fences if the model wrapped the JSON
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)
            return LLMResponse.model_validate(data)
        except Exception as exc:
            logger.debug(f"JSON parse failed: {exc} | raw={raw[:200]}")
            return None

    def _merge_lead_fields(self, lead: Lead, fields: LeadFields):
        """
        Update lead only when the LLM returned a non-null value.
        We never overwrite a known value with null — the LLM sees partial data
        across turns and may not repeat fields it already collected.
        """
        if fields.name         is not None: lead.name          = fields.name
        if fields.phone        is not None: lead.phone         = fields.phone
        if fields.company      is not None: lead.company       = fields.company
        if fields.budget       is not None: lead.budget        = fields.budget
        if fields.team_size    is not None: lead.team_size     = fields.team_size
        if fields.requirements is not None: lead.requirements  = fields.requirements
        if fields.timeline_days is not None: lead.timeline_days = fields.timeline_days


# Singleton – imported by the router
agent_service = AgentService()
