# services/summary_service.py – Phase 1 stub. Full summary in Phase 6.

import logging
logger = logging.getLogger(__name__)


class SummaryService:
    async def summarise(self, call_id: int, db) -> dict:
        """Phase 1 stub."""
        return {"summary": "", "insights": "{}", "overall_sentiment": "neutral"}


summary_service = SummaryService()
