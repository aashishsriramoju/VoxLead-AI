# services/lead_service.py – Deterministic, rule-based lead qualification & scoring
#
# Rule: Lead score is computed via pure business rules, NEVER hallucinated by an LLM.
# 100 points maximum:
# 1. Budget (up to 25 pts): Scaled by monthly budget amount ($/mo)
# 2. Timeline (up to 25 pts): <=14 days = 25, <=30 days = 15, >30 days = 5, unknown = 0
# 3. Requirements (up to 25 pts): Quality/depth of stated requirements
# 4. Engagement (up to 25 pts): Call turns (up to 10) + sentiment (up to 15)
#
# Qualification status:
#   Score >= 70  -> "hot"
#   Score 40-69  -> "warm"
#   Score < 40   -> "cold"

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models import Lead

logger = logging.getLogger(__name__)


def calculate_lead_score(
    budget: Optional[float] = None,
    timeline_days: Optional[int] = None,
    requirements: Optional[str] = None,
    sentiment: Optional[str] = "neutral",
    turn_count: int = 1,
) -> Tuple[float, str]:
    """
    Pure deterministic scoring function.
    Contains no database or LLM dependencies, making it 100% testable via pytest.
    Returns: (score: float, status: str)
    """
    # 1. Budget Score (0 to 25 points)
    budget_score = 0.0
    if budget is not None and budget > 0:
        if budget >= 1000:
            budget_score = 25.0
        elif budget >= 500:
            budget_score = 20.0
        elif budget >= 200:
            budget_score = 15.0
        else:
            budget_score = 10.0

    # 2. Timeline Score (0 to 25 points)
    timeline_score = 0.0
    if timeline_days is not None:
        if timeline_days <= 14:
            timeline_score = 25.0
        elif timeline_days <= 30:
            timeline_score = 15.0
        else:
            timeline_score = 5.0

    # 3. Requirements Score (0 to 25 points)
    requirements_score = 0.0
    if requirements and requirements.strip():
        req_clean = requirements.strip()
        word_count = len(req_clean.split())
        if word_count >= 10 or len(req_clean) >= 50:
            requirements_score = 25.0
        elif word_count >= 4:
            requirements_score = 15.0
        else:
            requirements_score = 10.0

    # 4. Engagement Score (0 to 25 points)
    # Sentiment component (up to 15 points)
    sentiment_lower = (sentiment or "neutral").lower()
    if sentiment_lower == "positive":
        sentiment_score = 15.0
    elif sentiment_lower == "negative":
        sentiment_score = 0.0
    else:  # neutral
        sentiment_score = 8.0

    # Turn count component (up to 10 points)
    if turn_count >= 4:
        turns_score = 10.0
    elif turn_count >= 2:
        turns_score = 6.0
    else:
        turns_score = 3.0

    engagement_score = min(25.0, sentiment_score + turns_score)

    # Total Score (0 to 100)
    total_score = round(budget_score + timeline_score + requirements_score + engagement_score, 1)
    total_score = min(100.0, max(0.0, total_score))

    # Qualification Status
    if total_score >= 70.0:
        status = "hot"
    elif total_score >= 40.0:
        status = "warm"
    else:
        status = "cold"

    return total_score, status


class LeadService:
    def update_and_score(
        self,
        lead: Lead,
        fields: dict,
        sentiment: str,
        turn_count: int,
        db: Session,
    ) -> Lead:
        """
        Recompute lead score and update lead model attributes in SQLite.
        """
        # Apply any direct dictionary fields if provided
        for k, v in fields.items():
            if hasattr(lead, k) and v is not None:
                setattr(lead, k, v)

        if sentiment:
            lead.sentiment = sentiment

        # Deterministic scoring calculation
        score, status = calculate_lead_score(
            budget=lead.budget,
            timeline_days=lead.timeline_days,
            requirements=lead.requirements,
            sentiment=lead.sentiment,
            turn_count=turn_count,
        )

        lead.score = score
        lead.status = status
        db.add(lead)
        db.commit()
        db.refresh(lead)

        logger.info(f"Lead {lead.id} scored: {score} ({status})")
        return lead


lead_service = LeadService()
