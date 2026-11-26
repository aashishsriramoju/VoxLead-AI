# services/booking_service.py – Intelligent Appointment slot booking & natural language date/time matching
#
# Rules:
# - The LLM NEVER executes SQL or direct DB mutations.
# - The LLM returns structured action intents ("check_slots", "book_appointment").
# - This service parses complex natural queries (e.g., "in 2 days", "tomorrow at 2 pm", "Saturday 12 pm", "first one"),
#   dynamically ensures future slot availability, and commits bookings.

import re
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Slot, Appointment
from config import SLOT_HOUR_START, SLOT_HOUR_END

logger = logging.getLogger(__name__)

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


class BookingService:

    def parse_target_date(self, text: str, base_date: Optional[date] = None) -> Optional[date]:
        """
        Extract a target calendar date from conversational user text.
        Supports:
        - "in 2 days", "in two days", "in 3 days"
        - "day after tomorrow", "tomorrow", "today"
        - "in a week", "in 2 weeks", "next week"
        - Weekdays: "this Friday", "Saturday", "next Monday"
        - Calendar dates: "November 28", "28th Nov", "28th of November"
        """
        if not text:
            return None
        
        text_lower = text.lower().strip()
        if not base_date:
            base_date = datetime.utcnow().date()

        # 1. "in X days" / "in X day"
        match = re.search(r'\bin\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+days?\b', text_lower)
        if match:
            val = match.group(1)
            days = int(val) if val.isdigit() else WORD_TO_NUM.get(val, 1)
            return base_date + timedelta(days=days)

        # 2. "after X days"
        match = re.search(r'\bafter\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?\b', text_lower)
        if match:
            val = match.group(1)
            days = int(val) if val.isdigit() else WORD_TO_NUM.get(val, 1)
            return base_date + timedelta(days=days)

        # 3. "day after tomorrow"
        if "day after tomorrow" in text_lower:
            return base_date + timedelta(days=2)

        # 4. "tomorrow"
        if "tomorrow" in text_lower:
            return base_date + timedelta(days=1)

        # 5. "today"
        if "today" in text_lower:
            return base_date

        # 6. "in X weeks"
        match = re.search(r'\bin\s+(\d+|one|two|three|four|a|an)\s+weeks?\b', text_lower)
        if match:
            val = match.group(1)
            weeks = int(val) if val.isdigit() else WORD_TO_NUM.get(val, 1)
            return base_date + timedelta(weeks=weeks)

        if "next week" in text_lower:
            return base_date + timedelta(days=7)

        # 7. Calendar dates: "Nov 28", "November 28th", "28th Nov", "28th of November"
        # Match pattern: Day then Month
        match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s*)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', text_lower)
        if match:
            day_num = int(match.group(1))
            month_str = match.group(2)[:3]
            month_num = MONTH_MAP.get(month_str, base_date.month)
            year = base_date.year
            try:
                candidate = date(year, month_num, day_num)
                if candidate < base_date:
                    candidate = date(year + 1, month_num, day_num)
                return candidate
            except ValueError:
                pass

        # Match pattern: Month then Day
        match = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{1,2})(?:st|nd|rd|th)?\b', text_lower)
        if match:
            month_str = match.group(1)[:3]
            day_num = int(match.group(2))
            month_num = MONTH_MAP.get(month_str, base_date.month)
            year = base_date.year
            try:
                candidate = date(year, month_num, day_num)
                if candidate < base_date:
                    candidate = date(year + 1, month_num, day_num)
                return candidate
            except ValueError:
                pass

        # 8. Weekdays: "monday" .. "sunday"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, w in enumerate(weekdays):
            if w in text_lower:
                days_ahead = (idx - base_date.weekday()) % 7
                if days_ahead == 0:
                    if "next" in text_lower or base_date.weekday() == idx:
                        days_ahead = 7
                return base_date + timedelta(days=days_ahead)

        return None

    def parse_target_hour(self, text: str) -> Optional[int]:
        """
        Extract requested hour (0-23) from text.
        Handles: "12 pm", "2 pm", "10 am", "noon", "morning", "afternoon", "at 2", "at 12".
        """
        if not text:
            return None
        text_lower = text.lower().strip()

        # 1. Explicit am/pm meridiem (takes highest precedence)
        m = re.search(r'\b(\d{1,2})(?::\d{2})?\s*(am|pm)\b', text_lower)
        if m:
            raw_hr = int(m.group(1))
            meridiem = m.group(2)
            if meridiem == "pm" and raw_hr < 12:
                return raw_hr + 12
            elif meridiem == "am" and raw_hr == 12:
                return 0
            return raw_hr

        # 2. 'at <hr>' or '<hr>:00' or '<hr> o clock'
        m = (
            re.search(r'(?:\bat\s+|(?<=\b))(\d{1,2}):\d{2}\b', text_lower)
            or re.search(r'\bat\s+(\d{1,2})\b', text_lower)
            or re.search(r'\b(\d{1,2})\s*o\'?clock\b', text_lower)
        )
        if m:
            raw_hr = int(m.group(1))
            if raw_hr in range(1, 6):
                return raw_hr + 12
            if raw_hr in range(9, 13):
                return raw_hr
            return raw_hr

        # 3. Word synonyms
        if re.search(r'\bnoon\b', text_lower) or "midday" in text_lower:
            return 12
        if "morning" in text_lower:
            return 10
        if "afternoon" in text_lower:
            return 14

        # 4. Bare hour not followed by units (days, weeks, months, ordinal suffixes)
        m = re.search(r'\b(\d{1,2})\s*(?!(?:days?|weeks?|months?|st|nd|rd|th))\b', text_lower)
        if m:
            raw_hr = int(m.group(1))
            if raw_hr in range(1, 6):
                return raw_hr + 12
            if raw_hr in range(9, 18):
                return raw_hr

        return None

    def ensure_slots_for_date(self, db: Session, target_date: date):
        """
        Dynamically guarantee that standard hourly business slots exist for target_date.
        """
        try:
            created = 0
            for hour in range(SLOT_HOUR_START, SLOT_HOUR_END):
                slot_dt = datetime(target_date.year, target_date.month, target_date.day, hour, 0, 0)
                exists = db.query(Slot).filter(Slot.slot_start == slot_dt).first()
                if not exists:
                    db.add(Slot(slot_start=slot_dt, is_booked=False))
                    created += 1
            if created > 0:
                db.commit()
                logger.info(f"Dynamically generated {created} slots for {target_date}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to dynamically ensure slots for {target_date}: {e}")

    def get_available_slots(
        self,
        db: Session,
        limit: int = 3,
        query: Optional[str] = None,
        target_date: Optional[date] = None,
    ) -> Tuple[List[Slot], Optional[date]]:
        """
        Query upcoming unbooked slots from the database.
        If a query or target_date is given (e.g. "in 2 days", "Friday"), looks specifically on that date.
        Returns (slots, resolved_target_date).
        """
        now = datetime.utcnow()

        if not target_date and query:
            target_date = self.parse_target_date(query, base_date=now.date())

        if target_date:
            self.ensure_slots_for_date(db, target_date)
            start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
            end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
            
            slots = (
                db.query(Slot)
                .filter(
                    Slot.is_booked == False,
                    Slot.slot_start >= start_dt,
                    Slot.slot_start <= end_dt,
                    Slot.slot_start > now,
                )
                .order_by(Slot.slot_start)
                .limit(limit)
                .all()
            )
            if slots:
                return (slots, target_date)

        # Fallback to general upcoming slots
        slots = (
            db.query(Slot)
            .filter(Slot.is_booked == False, Slot.slot_start > now)
            .order_by(Slot.slot_start)
            .limit(limit)
            .all()
        )
        return (slots, None)

    def format_slot_friendly(self, dt: datetime, include_date: bool = True) -> str:
        """
        Format a datetime into a friendly, spoken-natural string.
        Examples:
        - "Saturday, November 28 at 12:00 PM"
        - "Saturday at 12:00 PM"
        """
        if include_date:
            formatted = dt.strftime("%A, %B %d at %I:%M %p")
            # Replace leading zero in day and hour: e.g. "November 08 at 02:00 PM" -> "November 8 at 2:00 PM"
            formatted = re.sub(r'\b0(\d):', r'\1:', formatted)
            formatted = re.sub(r'([A-Za-z]+)\s+0(\d)\b', r'\1 \2', formatted)
            return formatted
        else:
            formatted = dt.strftime("%A at %I:%M %p")
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
        history: Optional[list] = None,
    ) -> Optional[Appointment]:
        """
        Intelligently match and book an available slot based on user intent and conversational context.
        Accepts:
        - Exact phrases: "in 2 days at 12 pm", "Saturday at 2 pm", "tomorrow 10 am"
        - Follow-up time picks: "12 pm works", "the first one", "10 am please"
        - Strict ISO datetimes
        """
        now = datetime.utcnow()
        combined_text = f"{slot_query or ''} {fallback_user_text or ''}".lower()

        # 1. Resolve target date
        target_date = self.parse_target_date(combined_text, base_date=now.date())

        # If date not in current query, search recent conversation history for date context
        if not target_date and history:
            for msg in reversed(history[-4:]):
                txt = msg.get("text", "")
                parsed_d = self.parse_target_date(txt, base_date=now.date())
                if parsed_d:
                    target_date = parsed_d
                    break

        if target_date:
            self.ensure_slots_for_date(db, target_date)

        # 2. Query available candidate slots
        if target_date:
            start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
            end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
            candidates = (
                db.query(Slot)
                .filter(
                    Slot.is_booked == False,
                    Slot.slot_start >= start_dt,
                    Slot.slot_start <= end_dt,
                    Slot.slot_start > now,
                )
                .order_by(Slot.slot_start)
                .all()
            )
        else:
            candidates = (
                db.query(Slot)
                .filter(Slot.is_booked == False, Slot.slot_start > now)
                .order_by(Slot.slot_start)
                .all()
            )

        if not candidates:
            logger.warning(f"No candidate slots available for target_date={target_date}")
            return None

        matched_slot: Optional[Slot] = None

        # 3. Check strict datetime parse
        dt = self._parse_strict_datetime(slot_query)
        if dt:
            window_start = dt - timedelta(minutes=45)
            window_end = dt + timedelta(minutes=45)
            for s in candidates:
                if window_start <= s.slot_start <= window_end:
                    matched_slot = s
                    break

        # 4. Ordinal selection: "first", "1st", "second", "2nd", "third", "3rd", "earliest"
        if not matched_slot:
            if any(term in combined_text for term in ["first", "1st", "earliest", "first one"]):
                matched_slot = candidates[0]
            elif any(term in combined_text for term in ["second", "2nd", "second one"]) and len(candidates) > 1:
                matched_slot = candidates[1]
            elif any(term in combined_text for term in ["third", "3rd", "third one"]) and len(candidates) > 2:
                matched_slot = candidates[2]

        # 5. Target Hour Matching
        if not matched_slot:
            target_hour = self.parse_target_hour(combined_text)
            if target_hour is not None:
                hour_filtered = [s for s in candidates if s.slot_start.hour == target_hour]
                if hour_filtered:
                    matched_slot = hour_filtered[0]

        # 6. Fallback if user confirmed without specific hour: "any", "works", "yes", "sure", "ok"
        if not matched_slot and any(term in combined_text for term in ["any", "works", "sure", "okay", "ok", "yes", "confirm", "fine"]):
            matched_slot = candidates[0]

        if not matched_slot:
            logger.warning(f"Could not resolve specific slot from query: '{slot_query}' / '{fallback_user_text}'")
            return None

        # 7. Commit booking to DB
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
