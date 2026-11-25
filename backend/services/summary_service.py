# services/summary_service.py – Post-call transcript analysis & summarization
#
# Generates:
# 1. 3-5 line executive call summary
# 2. Key structured insights: objections, customer interests, next steps, unanswered questions
# 3. Overall call sentiment (positive, neutral, negative)

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Call, Message
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
    async def summarise(self, call_id: int, db: Session) -> Dict[str, Any]:
        """
        Analyze call transcript with Gemini and return summary, insights, and sentiment.
        Includes robust rule-based fallback if LLM is unavailable.
        """
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return {
                "summary": "Call not found.",
                "insights": "{}",
                "overall_sentiment": "neutral",
            }

        # 1. Fetch message history
        messages = (
            db.query(Message)
            .filter(Message.call_id == call_id)
            .order_by(Message.created_at)
            .all()
        )

        if not messages or len(messages) <= 1:
            default_summary = "Call initiated but ended before substantive conversation took place."
            return {
                "summary": default_summary,
                "insights": json.dumps({
                    "interests": [],
                    "objections": [],
                    "unanswered_questions": [],
                    "next_steps": ["Follow up via email if contact info available"],
                }),
                "overall_sentiment": "neutral",
            }

        # 2. Format transcript for analysis
        transcript_lines = []
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}

        for m in messages:
            role_label = "Sales Rep (Nova)" if m.role == "assistant" else "Customer"
            transcript_lines.append(f"{role_label}: {m.text}")
            if m.sentiment in sentiment_counts:
                sentiment_counts[m.sentiment] += 1

        transcript_str = "\n".join(transcript_lines)

        # 3. Call Gemini to analyze
        prompt = f"TRANSCRIPT:\n{transcript_str}\n\nProduce the JSON post-call summary."
        raw_output = await llm_service.generate_plain(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_message=prompt,
        )

        parsed_data = self._try_parse_summary(raw_output)

        if parsed_data:
            insights_str = (
                json.dumps(parsed_data.get("insights", {}))
                if isinstance(parsed_data.get("insights"), dict)
                else "{}"
            )
            return {
                "summary": parsed_data.get("summary", "Call completed successfully."),
                "insights": insights_str,
                "overall_sentiment": parsed_data.get("overall_sentiment", "neutral"),
            }

        # 4. Fallback if Gemini fails or returns unparseable JSON
        logger.warning(f"Using rule-based summary fallback for call {call_id}")
        
        # Determine dominant sentiment from message history
        dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        # Check existing unanswered questions stored on call
        existing_insights = {}
        if call.insights:
            try:
                existing_insights = json.loads(call.insights)
            except Exception:
                existing_insights = {}

        unanswered = existing_insights.get("unanswered_questions", [])

        fallback_summary = (
            f"Customer engaged in a {len(messages)}-turn conversation with NovaCRM sales agent. "
            f"Overall dialogue tone was {dominant_sentiment}. "
            f"Call concluded with automated qualification logging."
        )

        fallback_insights = {
            "interests": ["NovaCRM Sales Platform"],
            "objections": [],
            "unanswered_questions": unanswered,
            "next_steps": ["Review lead qualification score in dashboard and assign sales rep follow-up."],
        }

        return {
            "summary": fallback_summary,
            "insights": json.dumps(fallback_insights),
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
