# services/booking_service.py – Appointment slot booking, natural language matching & validation
#
# Rules:
# - The LLM NEVER executes SQL or direct DB mutations.
# - The LLM only returns structured action intents ("check_slots", "book_appointment").
# - This service validates slot availability, parses natural user queries (e.g. "Thursday 12 pm",
#   "first one", "tomorrow 2 pm"), updates `slots`, and creates `appointments`.

import re
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

    def format_slot_friendly(self, dt: datetime) -> str:
        """
        Format a datetime into a friendly, spoken-natural string.
        Example: "Thursday at 12:00 PM" (no "UTC", no robotic timezone codes).
        """
        formatted = dt.strftime("%A at %I:%M %p")
        # Clean up leading zeros, e.g. "02:00 PM" -> "2:00 PM"
        formatted = formatted.replace(" at 0", " at ")
        return formatted

    def _parse_strict_datetime(self, slot_str: str) -> Optional[datetime]:
        """Attempt to parse common ISO/standard date-time strings into a datetime object."""
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
        slot_query: str,
        db: Session,
        fallback_user_text: str = "",
    ) -> Optional[Appointment]:
        """
        Intelligently match and book an available slot based on user intent.
        Accepts:
        - ISO datetime strings ("2026-11-26T12:00:00")
        - Natural weekday & time ("Thursday at 12 pm", "Thursday 12", "12 pm")
        - Relative dates ("tomorrow at 2 pm")
        - Ordinals ("the first one", "earliest")
        """
        now = datetime.utcnow()
        available_slots = (
            db.query(Slot)
            .filter(Slot.is_booked == False, Slot.slot_start > now)
            .order_by(Slot.slot_start)
            .all()
        )

        if not available_slots:
            logger.warning("No available future slots found in database.")
            return None

        matched_slot: Optional[Slot] = None
        combined_text = f"{slot_query or ''} {fallback_user_text or ''}".lower()

        # 1. Attempt strict datetime parse
        dt = self._parse_strict_datetime(slot_query)
        if dt:
            window_start = dt - timedelta(minutes=45)
            window_end = dt + timedelta(minutes=45)
            for s in available_slots:
                if window_start <= s.slot_start <= window_end:
                    matched_slot = s
                    break

        # 2. Ordinal selection: "first", "1st", "earliest", "any"
        if not matched_slot:
            if any(term in combined_text for term in ["first", "1st", "earliest", "first one"]):
                matched_slot = available_slots[0]

        # 3. Natural Language Matching (Weekday and/or Hour)
        if not matched_slot:
            # Check for weekday
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            target_weekday = None
            for idx, w in enumerate(weekdays):
                if w in combined_text:
                    target_weekday = idx
                    break

            # Check for "tomorrow"
            target_date = None
            if "tomorrow" in combined_text:
                target_date = (now + timedelta(days=1)).date()

            # Check for target hour (e.g. "12 pm", "2 pm", "10 am", "12", "2")
            target_hour = None
            hour_match = re.search(r'\b(\d{1,2})(?::\d{2})?\s*(am|pm)?\b', combined_text)
            if hour_match:
                raw_hr = int(hour_match.group(1))
                meridiem = hour_match.group(2)
                if meridiem == "pm" and raw_hr < 12:
                    target_hour = raw_hr + 12
                elif meridiem == "am" and raw_hr == 12:
                    target_hour = 0
                elif not meridiem and raw_hr in range(1, 6): # Assume afternoon business hours 1-5 PM
                    target_hour = raw_hr + 12
                else:
                    target_hour = raw_hr

            # Filter candidates
            candidates = available_slots
            if target_weekday is not None:
                candidates = [s for s in candidates if s.slot_start.weekday() == target_weekday]
            elif target_date is not None:
                candidates = [s for s in candidates if s.slot_start.date() == target_date]

            if target_hour is not None:
                # Find slot matching target hour
                hour_filtered = [s for s in candidates if s.slot_start.hour == target_hour]
                if hour_filtered:
                    matched_slot = hour_filtered[0]

            # If weekday or tomorrow matched but specific hour wasn't found or specified, pick first on that day
            if not matched_slot and candidates:
                matched_slot = candidates[0]

        # 4. Fallback if user said "any works", "yes", "book it", "sure", etc.
        if not matched_slot and any(term in combined_text for term in ["any", "works", "sure", "okay", "ok", "yes", "confirm", "fine"]):
            matched_slot = available_slots[0]

        if not matched_slot:
            logger.warning(f"Could not resolve slot from query: '{slot_query}' / '{fallback_user_text}'")
            return None

        # 5. Commit booking to DB
        try:
            matched_slot.is_booked = True
            db.add(matched_slot)

            appointment = Appointment(
                lead_id=lead_id,
                slot_start=matched_slot.slot_start,
                status="confirmed",
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)

            logger.info(f"Successfully booked slot {matched_slot.slot_start} for lead {lead_id}")
            return appointment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit appointment booking: {e}")
            return None


booking_service = BookingService()
