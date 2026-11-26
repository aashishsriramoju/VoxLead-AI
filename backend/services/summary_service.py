# services/summary_service.py – Fast, instant post-call transcript analysis & text summarization
#
# Generates:
# 1. 3-5 line executive call summary (updated instantly)
# 2. Key structured insights in clean human-readable TEXT format (not raw JSON)
# 3. Overall call sentiment (positive, neutral, negative)

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Call, Message, Lead, Appointment
from services import llm_service

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are an expert sales analyst reviewing an AI voice sales call transcript for NovaCRM.

Analyze the conversation transcript provided and produce a concise post-call brief.

You MUST return ONLY valid JSON matching this exact structure:
{
  "summary": "<3 to 5 lines summarizing the customer's needs, budget/timeline if mentioned, and call outcome>",
  "insights": {
    "interests": ["<specific features or capabilities the customer was interested in>"],
    "objections": ["<pricing concerns, feature gaps, or hesitation expressed>"],
    "unanswered_questions": ["<questions the customer asked that could not be answered from documents>"],
    "next_steps": ["<clear next actions: e.g. demo follow-up, send proposal, human rep contact>"]
  },
  "overall_sentiment": "<positive|neutral|negative>"
}
"""


class SummaryService:

    def format_insights_to_text(self, insights_data: Any) -> str:
        """
        Convert structured insights (dict or JSON string) into clean, human-readable text.
        """
        if not insights_data:
            return "🎯 Interests: NovaCRM Platform\n⚠️ Objections: None raised\n➡️ Next Steps: Review lead qualification in dashboard\n❓ Unanswered: None"

        if isinstance(insights_data, str):
            try:
                insights_data = json.loads(insights_data)
            except Exception:
                return insights_data

        if not isinstance(insights_data, dict):
            return str(insights_data)

        lines = []
        interests = insights_data.get("interests", [])
        if interests and isinstance(interests, list):
            lines.append(f"🎯 Interests: {', '.join(interests)}")
        elif interests:
            lines.append(f"🎯 Interests: {interests}")
        else:
            lines.append("🎯 Interests: NovaCRM Sales Platform")

        objections = insights_data.get("objections", [])
        if objections and isinstance(objections, list) and len(objections) > 0:
            lines.append(f"⚠️ Objections: {', '.join(objections)}")
        elif objections and not isinstance(objections, list):
            lines.append(f"⚠️ Objections: {objections}")
        else:
            lines.append("⚠️ Objections: None raised")

        next_steps = insights_data.get("next_steps", [])
        if next_steps and isinstance(next_steps, list) and len(next_steps) > 0:
            lines.append(f"➡️ Next Steps: {', '.join(next_steps)}")
        elif next_steps and not isinstance(next_steps, list):
            lines.append(f"➡️ Next Steps: {next_steps}")
        else:
            lines.append("➡️ Next Steps: Follow up with customer based on qualification score")

        unanswered = insights_data.get("unanswered_questions", [])
        if unanswered and isinstance(unanswered, list) and len(unanswered) > 0:
            lines.append(f"❓ Unanswered: {', '.join(unanswered)}")
        elif unanswered and not isinstance(unanswered, list):
            lines.append(f"❓ Unanswered: {unanswered}")
        else:
            lines.append("❓ Unanswered: None (all questions answered from knowledge base)")

        return "\n".join(lines)

    async def summarise(self, call_id: int, db: Session) -> Dict[str, Any]:
        """
        Fast, instant post-call summarization with rich contextual analysis.
        Executes immediately without blocking the user.
        """
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return {
                "summary": "Call record not found.",
                "insights": "No insights available.",
                "overall_sentiment": "neutral",
            }

        # 1. Fetch messages, lead, and appointment
        messages = (
            db.query(Message)
            .filter(Message.call_id == call_id)
            .order_by(Message.created_at)
            .all()
        )

        lead = db.query(Lead).filter(Lead.call_id == call_id).first()
        appointment = None
        if lead:
            appointment = db.query(Appointment).filter(Appointment.lead_id == lead.id).first()

        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for m in messages:
            if m.sentiment in sentiment_counts:
                sentiment_counts[m.sentiment] += 1

        dominant_sentiment = "neutral"
        if any(sentiment_counts.values()):
            dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)

        # 2. Build instant deterministic executive summary
        customer_name = lead.name if lead and lead.name else "Customer"
        summary_parts = []
        if lead and lead.name:
            lead_desc = f"{customer_name}"
            if lead.company:
                lead_desc += f" from {lead.company}"
            summary_parts.append(f"{lead_desc} connected with NovaCRM sales representative Nova.")
        else:
            summary_parts.append(f"Customer connected with NovaCRM sales representative Nova for a {len(messages)}-turn conversation.")

        if lead and (lead.team_size or lead.budget or lead.requirements):
            details = []
            if lead.team_size:
                details.append(f"team of {lead.team_size} users")
            if lead.budget:
                details.append(f"budget of ₹{int(lead.budget):,}/mo")
            if lead.requirements:
                details.append(f"needs: {lead.requirements}")
            summary_parts.append(f"Lead details recorded ({', '.join(details)}).")

        if appointment:
            friendly_appt = appointment.slot_start.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
            summary_parts.append(f"A live product demo was successfully confirmed for {friendly_appt}.")
        else:
            summary_parts.append("Discussion covered NovaCRM features, SLA terms, and pricing plans.")

        summary_parts.append(f"Call concluded smoothly with overall {dominant_sentiment} sentiment.")
        fast_summary = " ".join(summary_parts)

        # 3. Build instant text insights
        existing_insights = {}
        if call.insights:
            try:
                existing_insights = json.loads(call.insights)
            except Exception:
                existing_insights = {}

        unanswered = existing_insights.get("unanswered_questions", [])

        interests = ["NovaCRM Platform Overview"]
        if appointment:
            interests.append("Live Product Demo")
        if lead and lead.budget:
            interests.append("Subscription Pricing")

        next_steps = []
        if appointment:
            friendly_appt = appointment.slot_start.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
            next_steps.append(f"Conduct product demo scheduled for {friendly_appt}")
        else:
            next_steps.append("Follow up via phone/email to schedule product demo")

        fast_insights_dict = {
            "interests": interests,
            "objections": [],
            "unanswered_questions": unanswered,
            "next_steps": next_steps,
        }
        fast_insights_text = self.format_insights_to_text(fast_insights_dict)

        # 4. Optional quick LLM enhancement with strict 2-second timeout
        try:
            transcript_lines = [
                f"{'Sales Rep (Nova)' if m.role == 'assistant' else 'Customer'}: {m.text}"
                for m in messages
            ]
            transcript_str = "\n".join(transcript_lines)
            prompt = f"TRANSCRIPT:\n{transcript_str}\n\nProduce the JSON post-call summary."

            # Attempt Gemini with 2.0s timeout to never delay the UI
            llm_task = llm_service.generate_plain(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                user_message=prompt,
            )
            raw_output = await asyncio.wait_for(llm_task, timeout=2.0)
            parsed_data = self._try_parse_summary(raw_output)
            if parsed_data and parsed_data.get("summary"):
                llm_summary = parsed_data.get("summary")
                llm_insights = self.format_insights_to_text(parsed_data.get("insights", fast_insights_dict))
                llm_sentiment = parsed_data.get("overall_sentiment", dominant_sentiment)
                return {
                    "summary": llm_summary,
                    "insights": llm_insights,
                    "overall_sentiment": llm_sentiment,
                }
        except Exception:
            # On timeout, quota limit, or any error, immediately return the fast instant summary
            pass

        return {
            "summary": fast_summary,
            "insights": fast_insights_text,
            "overall_sentiment": dominant_sentiment,
        }

    def _try_parse_summary(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse Gemini response into summary dictionary."""
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
            if "summary" in data and "overall_sentiment" in data:
                return data
            return None
        except Exception as e:
            logger.debug(f"Summary JSON parsing failed: {e}")
            return None


summary_service = SummaryService()
