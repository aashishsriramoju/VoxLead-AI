# services/booking_service.py – Appointment slot booking and validation
#
# Rules:
# - The LLM NEVER executes SQL or direct DB mutations.
# - The LLM only returns structured action intents ("check_slots", "book_appointment").
# - This service validates slot availability, updates `slots`, and creates `appointments`.

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Slot, Appointment

logger = logging.getLogger(__name__)


class BookingService:
    def get_available_slots(self, db: Session, limit: int = 5) -> List[Slot]:
        """
        Query upcoming unbooked slots from the database.
        """
        now = datetime.utcnow()
        return (
            db.query(Slot)
            .filter(Slot.is_booked == False, Slot.slot_start > now)
            .order_by(Slot.slot_start)
            .limit(limit)
            .all()
        )

    def _parse_datetime(self, slot_str: str) -> Optional[datetime]:
        """Attempt to parse common date-time strings into a datetime object."""
        if not slot_str:
            return None
            
        slot_clean = slot_str.strip().replace("Z", "").replace("+00:00", "")
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(slot_clean, fmt)
            except ValueError:
                continue
        return None

    def book_slot(
        self,
        lead_id: int,
        slot_start_str: str,
        db: Session,
    ) -> Optional[Appointment]:
        """
        Validate slot availability and book the appointment.
        Returns the created Appointment object or None if booking failed.
        """
        dt = self._parse_datetime(slot_start_str)
        if not dt:
            logger.warning(f"Could not parse requested slot timestamp: '{slot_start_str}'")
            return None

        # Look for a slot within +/- 30 minutes of requested time to be forgiving of user phrasing
        window_start = dt - timedelta(minutes=30)
        window_end = dt + timedelta(minutes=30)

        slot = (
            db.query(Slot)
            .filter(
                Slot.is_booked == False,
                Slot.slot_start >= window_start,
                Slot.slot_start <= window_end,
            )
            .first()
        )

        if not slot:
            # If no exact match in window, see if there is any exact matching slot
            slot = (
                db.query(Slot)
                .filter(
                    Slot.is_booked == False,
                    Slot.slot_start == dt,
                )
                .first()
            )

        if not slot:
            logger.warning(f"No available slot matching {slot_start_str}")
            return None

        try:
            # 1. Mark slot as booked
            slot.is_booked = True
            db.add(slot)

            # 2. Create appointment record
            appointment = Appointment(
                lead_id=lead_id,
                slot_start=slot.slot_start,
                status="confirmed",
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)

            logger.info(f"Successfully booked slot {slot.slot_start} for lead {lead_id}")
            return appointment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit appointment booking: {e}")
            return None


booking_service = BookingService()
