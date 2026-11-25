# services/booking_service.py – Phase 1 stub. Full booking in Phase 4.

import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BookingService:
    def get_available_slots(self, db: Session):
        """Return up to 5 future unbooked slots."""
        from datetime import datetime
        from models import Slot
        return (
            db.query(Slot)
            .filter(Slot.is_booked == False, Slot.slot_start > datetime.utcnow())
            .order_by(Slot.slot_start)
            .limit(5)
            .all()
        )

    def book_slot(self, lead_id: int, slot_start_str: str, db: Session):
        """Phase 1 stub: booking logic added in Phase 4."""
        return None


booking_service = BookingService()
