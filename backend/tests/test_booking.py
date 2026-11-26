# backend/tests/test_booking.py – Comprehensive unit tests for appointment booking & natural date parsing

import os
import sys
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import SessionLocal, init_db
from models import Slot, Lead, Call, Appointment
from services.booking_service import booking_service


def test_natural_date_parsing():
    """Verify natural relative and calendar date parsing."""
    base = date(2026, 11, 26)  # Thursday

    # Relative days
    assert booking_service.parse_target_date("in 2 days", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("in two days", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("can we book in 2 days?", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("tomorrow", base) == date(2026, 11, 27)
    assert booking_service.parse_target_date("day after tomorrow", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("in 3 days", base) == date(2026, 11, 29)
    assert booking_service.parse_target_date("in a week", base) == date(2026, 12, 3)

    # Weekdays
    assert booking_service.parse_target_date("this Friday", base) == date(2026, 11, 27)
    assert booking_service.parse_target_date("Saturday", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("next Monday", base) == date(2026, 11, 30)

    # Explicit calendar dates
    assert booking_service.parse_target_date("November 28", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("28th Nov", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("28th of November", base) == date(2026, 11, 28)
    assert booking_service.parse_target_date("Dec 2", base) == date(2026, 12, 2)

    print("✓ Natural date parsing passed (12/12 cases)")


def test_target_hour_parsing():
    """Verify 12-hour and keyword hour extraction."""
    assert booking_service.parse_target_hour("at 12 pm") == 12
    assert booking_service.parse_target_hour("12:00 PM") == 12
    assert booking_service.parse_target_hour("2 pm") == 14
    assert booking_service.parse_target_hour("10 am") == 10
    assert booking_service.parse_target_hour("noon") == 12
    assert booking_service.parse_target_hour("afternoon") == 14
    assert booking_service.parse_target_hour("morning") == 10

    print("✓ Target hour parsing passed (7/7 cases)")


def test_get_slots_in_two_days():
    """Verify querying slots for 'in 2 days' returns 3 available slots for that exact target date."""
    init_db()
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expected_date = now.date() + timedelta(days=2)

        slots, target_d = booking_service.get_available_slots(db, limit=3, query="in 2 days")
        assert len(slots) == 3, f"Expected 3 slots, got {len(slots)}"
        assert target_d == expected_date, f"Expected {expected_date}, got {target_d}"
        for s in slots:
            assert s.slot_start.date() == expected_date
            assert not s.is_booked

        print("✓ Get available slots for 'in 2 days' returned exact 3 slots for target date!")
    finally:
        db.close()


def test_book_slot_in_two_days():
    """Verify single-turn and multi-turn booking in 2 days."""
    init_db()
    db = SessionLocal()
    try:
        call = Call(language="en-IN")
        db.add(call)
        db.flush()
        lead = Lead(call_id=call.id, name="Ashish", phone="9876543210")
        db.add(lead)
        db.flush()

        now = datetime.utcnow()
        expected_date = now.date() + timedelta(days=2)

        # Ensure test slots on target date are unbooked for test repeatability
        db.query(Slot).filter(
            Slot.slot_start >= datetime(expected_date.year, expected_date.month, expected_date.day, 0, 0, 0),
            Slot.slot_start <= datetime(expected_date.year, expected_date.month, expected_date.day, 23, 59, 59)
        ).update({"is_booked": False})
        db.commit()

        # 1. Direct single-turn booking: "in 2 days at 12 pm"
        appt = booking_service.book_slot(lead.id, "in 2 days at 12 pm", db)
        assert appt is not None, "Appointment should be confirmed"
        assert appt.slot_start.date() == expected_date
        assert appt.slot_start.hour == 12
        assert appt.status == "confirmed"

        # 2. Multi-turn booking using history: user picked "the first one" after slots were presented
        mock_history = [
            {"role": "user", "text": "What slots are available in 2 days?"},
            {"role": "assistant", "text": f"In two days on {expected_date.strftime('%A')}, we have demo slots open at 10:00 AM, 11:00 AM, or 2:00 PM!"}
        ]
        appt2 = booking_service.book_slot(lead.id, "the first one", db, history=mock_history)
        assert appt2 is not None
        assert appt2.slot_start.date() == expected_date
        assert appt2.slot_start.hour == 10

        print("✓ Single-turn and multi-turn slot booking in 2 days passed!")
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_natural_date_parsing()
    test_target_hour_parsing()
    test_get_slots_in_two_days()
    test_book_slot_in_two_days()
    print("\nALL BOOKING TESTS PASSED PERFECTLY!")
