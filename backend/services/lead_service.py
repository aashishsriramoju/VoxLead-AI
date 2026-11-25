# services/lead_service.py – Phase 1 stub. Full scoring in Phase 4.

import logging
from sqlalchemy.orm import Session
from models import Lead

logger = logging.getLogger(__name__)


class LeadService:
    def update_and_score(self, lead: Lead, fields: dict, sentiment: str, turn_count: int, db: Session) -> Lead:
        """Stub: returns lead unchanged until Phase 4."""
        return lead


lead_service = LeadService()
