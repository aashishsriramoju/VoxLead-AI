import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import SessionLocal
from models import Slot, Lead, Call, Appointment
from services.booking_service import booking_service

def test_booking_flow():
    db = SessionLocal()
    try:
        # Create a test call and lead
        call = Call(language="en-IN")
        db.add(call)
        db.flush()
        lead = Lead(call_id=call.id, name="Test User", phone="1234567890")
        db.add(lead)
        db.flush()

        # Find an available slot
        slots = booking_service.get_available_slots(db)
        assert len(slots) > 0, "Should have available slots from seed"
        target_slot = slots[0]
        slot_iso = target_slot.slot_start.isoformat()

        # Book the slot
        appointment = booking_service.book_slot(lead.id, slot_iso, db)
        assert appointment is not None, "Booking should succeed"
        assert appointment.lead_id == lead.id
        assert appointment.status == "confirmed"

        # Verify slot is marked booked
        db.refresh(target_slot)
        assert target_slot.is_booked == True

        # Attempt to book the same slot again should fail
        repeat_booking = booking_service.book_slot(lead.id, slot_iso, db)
        assert repeat_booking is None, "Double booking same slot should fail"

        print("Booking service unit test PASSED!")
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    test_booking_flow()
