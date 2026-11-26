# services/agent_service.py – Conversation orchestrator with friendly persona, INR pricing, and auto-end call
#
# Key features:
# - Exceptionally warm, friendly, conversational sales persona
# - Quotes and qualification in Indian Rupees (₹ / INR)
# - Natural spoken times (no "UTC", no markdown bullet lists)
# - Intelligent slot booking with natural language matching
# - Automatic call termination and post-call summary generation when the customer says goodbye

import json
import time
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
# System prompt – Warm, friendly personality and Indian context (INR)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Nova, an exceptionally warm, enthusiastic, and friendly sales representative for NovaCRM,
an intuitive CRM platform designed to empower growing sales teams.

CORE CONVERSATIONAL GUIDELINES:
1. TONE: Be delightfully warm, polite, and encouraging! Address the customer by name once you know it.
2. SPOKEN REPLIES: Reply in max 2 SHORT, natural, conversational sentences. Avoid bullet points, symbols, or asterisks.
3. CURRENCY: All pricing, budgets, and quotes MUST be in Indian Rupees (₹ / INR). Never quote in dollars.
4. SPOKEN TIMES: Never say "UTC" or technical timezones. Speak dates naturally, e.g., "Thursday at 12 PM".
5. KNOWLEDGE BOUNDARY: Answer product, pricing, and policy questions ONLY from the <context> block.
   If the answer is not in <context>, warmly say: "I'll have our specialist follow up with you on that!"
6. CONTACT & QUALIFICATION INTAKE:
   - When the customer shares their name (or right after learning their name), immediately ask for their COMPANY NAME and MOBILE NUMBER next.
   - Example: "Wonderful to meet you, [Name]! Which company are you with, and what's the best mobile number to reach you?"
   - Once company name and mobile number are collected, continue qualification: team size → monthly budget (in ₹ INR) → timeline → specific requirements.
   - Always extract and return name, company, and phone into lead_fields whenever provided.
7. DEMO BOOKING & AVAILABILITY:
   - If the customer asks about booking, scheduling, dates, or available slots (e.g., "in 2 days", "what slots do you have", "can I book for tomorrow", "are you free Friday", "schedule a demo"):
     Set action to "check_slots" and requested_slot to the target date/time mentioned (e.g. "in 2 days").
   - If the customer selects, confirms, or asks to book a specific time (e.g., "12 PM works", "the first one", "book at 2 PM in 2 days"):
     Set action to "book_appointment" and requested_slot to the chosen time/slot.
   - Collect customer name, company, and mobile number naturally without blocking slot checking.
8. AUTO-EXIT: If the customer indicates they are done, want to leave, or say goodbye (e.g. "bye", "goodbye", "that's all", "thank you bye"),
   set action to "end_call" and give a cheerful, heartfelt farewell.
9. LANGUAGE: Reply in the same language the customer uses (English, Hindi, or Telugu).

OUTPUT FORMAT — you MUST return ONLY valid JSON:
{
  "reply": "<warm spoken reply, max 2 short sentences>",
  "sentiment": "<positive|neutral|negative>",
  "lead_fields": {
    "name": "<string or null>",
    "phone": "<string or null>",
    "company": "<string or null>",
    "budget": <number in INR / Rupees per month or null>,
    "team_size": <integer or null>,
    "requirements": "<string or null>",
    "timeline_days": <integer or null>
  },
  "action": "<none|check_slots|book_appointment|end_call>",
  "requested_slot": "<natural time string or ISO string, or null>",
  "language": "<en-IN|hi-IN|te-IN>"
}
"""

FALLBACK_REPLY = (
    "I'm so sorry, I didn't quite catch that. Could you please share that with me again? "
    "I'd love to help you!"
)

GREETING = (
    "Hi there! I'm Nova, your friendly NovaCRM assistant. "
    "It's wonderful to connect with you! May I know your name?"
)

# Heuristic list of phrases indicating the customer wants to end the call
EXIT_PHRASES = [
    "bye", "goodbye", "bye bye", "see ya", "end call", "cut the call",
    "hang up", "disconnect", "that's all", "that is all", "that's it",
    "that is it", "all done", "no that's all", "nothing else", "no more questions",
    "thanks bye", "thank you bye", "have a good day", "have a nice day",
    "i am done", "that will be all",
]


class AgentService:

    async def start_call(self, db: Session) -> CallStartResponse:
        call = Call(language="en-IN")
        db.add(call)
        db.flush()

        lead = Lead(call_id=call.id)
        db.add(lead)

        db.add(Message(
            call_id=call.id,
            role="assistant",
            text=GREETING,
            sentiment="positive",
        ))
        db.commit()
        db.refresh(call)
        return CallStartResponse(call_id=call.id, reply=GREETING)

    async def handle_turn(
        self,
        call_id: int,
        user_text: str,
        language: str,
        db: Session,
    ) -> Optional[TurnResponse]:
        turn_start_time = time.perf_counter()

        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        call.language = language
        db.add(call)

        # 1. Check for customer exit intent
        user_lower = user_text.lower().strip()
        user_wants_to_exit = any(phrase in user_lower for phrase in EXIT_PHRASES)

        # 2. Load conversation history
        history_rows = (
            db.query(Message)
            .filter(Message.call_id == call_id)
            .order_by(Message.created_at)
            .all()
        )
        history = [{"role": m.role, "text": m.text} for m in history_rows]

        # 3. Retrieve RAG chunks
        from services.rag_service import rag_service
        chunks = await rag_service.retrieve(user_text)
        context_block = self._build_context_block(chunks)
        full_system_prompt = SYSTEM_PROMPT + "\n\n" + context_block

        # 4. Generate LLM response
        raw = await llm_service.generate(
            system_prompt=full_system_prompt,
            history=history,
            user_message=user_text,
        )

        llm_resp = await self._parse_llm_response(raw, full_system_prompt, history, user_text)

        reply_text  = llm_resp.reply
        sentiment   = llm_resp.sentiment
        action      = llm_resp.action
        lead_fields = llm_resp.lead_fields

        # 5. Update Lead record
        lead = db.query(Lead).filter(Lead.call_id == call_id).first()
        if not lead:
            lead = Lead(call_id=call_id)
            db.add(lead)
            db.flush()

        if lead_fields:
            self._merge_lead_fields(lead, lead_fields, raw_user_text=user_text)
        elif user_text:
            phone_match = re.search(r'(?:\+?91[\s-]?)?([6-9]\d{9})\b', user_text)
            if phone_match and not lead.phone:
                lead.phone = phone_match.group(0).strip()

        # Track unanswered questions if relevant
        is_question = any(kw in user_lower for kw in ["?", "what", "how", "pricing", "cost", "price", "refund", "policy", "sla", "terms", "can you", "do you", "support"])
        if is_question and not chunks:
            try:
                curr_insights = json.loads(call.insights) if call.insights else {}
                unanswered = curr_insights.get("unanswered_questions", [])
                if user_text not in unanswered:
                    unanswered.append(user_text)
                curr_insights["unanswered_questions"] = unanswered
                call.insights = json.dumps(curr_insights)
                db.add(call)
            except Exception as e:
                logger.error(f"Error recording unanswered question: {e}")

        # 6. Recompute score
        turn_count = len(history) + 1
        lead = lead_service.update_and_score(lead, {}, sentiment, turn_count, db)

        # 7. Handle Actions
        appointment_out: Optional[AppointmentOut] = None
        call_ended = False

        # AUTO-END CALL: If user wants to exit or LLM signaled end_call
        if user_wants_to_exit or action == "end_call":
            call_ended = True
            customer_name = lead.name or "there"
            reply_text = f"Thank you so much for chatting with me today, {customer_name}! Have a truly wonderful day ahead, goodbye!"
            
            # Finalize call in database
            call.ended_at = datetime.utcnow()
            db.commit()

            # Trigger automated post-call summary
            from services.summary_service import summary_service
            summary_res = await summary_service.summarise(call_id, db)
            call.summary = summary_res.get("summary")
            call.insights = summary_res.get("insights")
            call.overall_sentiment = summary_res.get("overall_sentiment")
            db.commit()

        elif action == "check_slots":
            query_slot = llm_resp.requested_slot or user_text
            slots, matched_date = booking_service.get_available_slots(db, limit=3, query=query_slot)
            if slots:
                times_spoken = [s.slot_start.strftime("%I:%M %p").lstrip("0") for s in slots]
                if len(times_spoken) > 1:
                    times_str = ", ".join(times_spoken[:-1]) + f", or {times_spoken[-1]}"
                else:
                    times_str = times_spoken[0]

                now_date = datetime.utcnow().date()
                if matched_date:
                    days_diff = (matched_date - now_date).days
                    weekday_name = matched_date.strftime("%A")
                    date_str = matched_date.strftime("%B %d").replace(" 0", " ")

                    if days_diff == 2 or "in 2 days" in user_lower or "in two days" in user_lower:
                        day_prefix = f"In two days on {weekday_name}, {date_str}"
                    elif days_diff == 1 or "tomorrow" in user_lower:
                        day_prefix = f"Tomorrow on {weekday_name}"
                    elif days_diff == 0 or "today" in user_lower:
                        day_prefix = "Today"
                    else:
                        day_prefix = f"On {weekday_name}, {date_str}"

                    reply_text = f"{day_prefix}, we have demo slots open at {times_str}! Which of those times works best for you?"
                else:
                    day_name = slots[0].slot_start.strftime("%A")
                    reply_text = f"We have demo slots open on {day_name} at {times_str}! Which time works best for you?"
            else:
                reply_text = "I'm sorry, our upcoming slots are currently filled. Let me take down your details so our team can contact you directly!"

        elif action == "book_appointment":
            slot_query = llm_resp.requested_slot or user_text
            appt = booking_service.book_slot(
                lead.id,
                slot_query,
                db,
                fallback_user_text=user_text,
                history=history,
            )
            if appt:
                appointment_out = AppointmentOut.model_validate(appt)
                friendly_time = booking_service.format_slot_friendly(appt.slot_start, include_date=True)
                reply_text = f"Wonderful! Your demo is confirmed for {friendly_time}. We're excited to show you NovaCRM!"
            else:
                slots, matched_date = booking_service.get_available_slots(db, limit=3, query=slot_query)
                if slots:
                    times_spoken = [s.slot_start.strftime("%I:%M %p").lstrip("0") for s in slots]
                    times_str = ", ".join(times_spoken[:-1]) + f", or {times_spoken[-1]}"
                    day_prefix = f"on {matched_date.strftime('%A, %B %d')}" if matched_date else "upcoming"
                    reply_text = f"I'd love to book that for you! We have slots open {day_prefix} at {times_str}. Which time works best for you?"
                else:
                    reply_text = "I couldn't quite catch which slot you preferred! Let me know what time works best for you and I'll book it right away."

        # 8. Store messages in DB
        db.add(Message(call_id=call_id, role="user",      text=user_text,   sentiment=sentiment))
        db.add(Message(call_id=call_id, role="assistant", text=reply_text,  sentiment="neutral"))
        db.commit()
        db.refresh(lead)

        sources = [
            SourceChunk(file=c["file"], section=c["section"], score=round(c["score"], 3))
            for c in chunks
        ]

        latency_ms = round((time.perf_counter() - turn_start_time) * 1000, 1)

        return TurnResponse(
            reply=reply_text,
            sentiment=sentiment,
            lead=LeadOut.model_validate(lead),
            score=lead.score,
            appointment=appointment_out,
            sources=sources,
            call_ended=call_ended,
            latency_ms=latency_ms,
        )

    def _build_context_block(self, chunks: list[dict]) -> str:
        if not chunks:
            return "<context>\nNo relevant company documents found for this query.\n</context>"

        lines = ["<context>"]
        for c in chunks:
            lines.append(f"[Source: {c['file']} > {c['section']}]")
            lines.append(c["text"])
            lines.append("")
        lines.append("</context>")
        return "\n".join(lines)

    async def _parse_llm_response(
        self,
        raw: Optional[str],
        system_prompt: str,
        history: list[dict],
        user_message: str,
    ) -> LLMResponse:
        parsed = self._try_parse(raw)
        if parsed:
            return parsed

        logger.warning("Gemini returned invalid JSON on first attempt; retrying...")

        correction = (
            f"Your previous response was not valid JSON. "
            f"The user message was: '{user_message}'. "
            f"Reply ONLY with the valid JSON object described in the system prompt. No markdown."
        )
        raw2 = await llm_service.generate(
            system_prompt=system_prompt,
            history=history,
            user_message=correction,
        )
        parsed2 = self._try_parse(raw2)
        if parsed2:
            return parsed2

        logger.error("Gemini failed twice; using friendly fallback reply")
        return LLMResponse(reply=FALLBACK_REPLY, sentiment="neutral")

    def _try_parse(self, raw: Optional[str]) -> Optional[LLMResponse]:
        if not raw:
            return None
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)
            return LLMResponse.model_validate(data)
        except Exception as exc:
            logger.debug(f"JSON parse failed: {exc}")
            return None

    def _merge_lead_fields(self, lead: Lead, fields: LeadFields, raw_user_text: str = ""):
        if fields.name         is not None: lead.name          = fields.name
        if fields.phone        is not None: lead.phone         = fields.phone
        if fields.company      is not None: lead.company       = fields.company
        if fields.budget       is not None: lead.budget        = fields.budget
        if fields.team_size    is not None: lead.team_size     = fields.team_size
        if fields.requirements is not None: lead.requirements  = fields.requirements
        if fields.timeline_days is not None: lead.timeline_days = fields.timeline_days

        # Regex fallback for mobile number if not extracted
        if not lead.phone and raw_user_text:
            phone_match = re.search(r'(?:\+?91[\s-]?)?([6-9]\d{9})\b', raw_user_text)
            if phone_match:
                lead.phone = phone_match.group(0).strip()

    async def end_call(self, call_id: int, db: Session) -> Optional[EndCallResponse]:
        """
        Finalize the call session, generate executive summary and text insights, and update DB.
        """
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        call.ended_at = datetime.utcnow()
        db.commit()

        from services.summary_service import summary_service
        summary_res = await summary_service.summarise(call_id, db)
        call.summary = summary_res.get("summary")
        call.insights = summary_res.get("insights")
        call.overall_sentiment = summary_res.get("overall_sentiment")
        db.commit()
        db.refresh(call)

        return EndCallResponse(
            summary=call.summary or "Call ended successfully.",
            insights=call.insights or "",
            overall_sentiment=call.overall_sentiment or "neutral",
        )


agent_service = AgentService()
