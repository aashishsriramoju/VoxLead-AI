# api/appointments.py – Read-only endpoints for appointment data

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Appointment, Slot
from schemas import AppointmentOut, SlotOut

router = APIRouter()


@router.get("/", response_model=List[AppointmentOut])
def get_appointments(db: Session = Depends(get_db)):
    """Return all confirmed appointments, newest first."""
    return db.query(Appointment).order_by(Appointment.id.desc()).all()


@router.get("/slots", response_model=List[SlotOut])
def get_available_slots(db: Session = Depends(get_db)):
    """Return all future, unbooked slots so the frontend can display them."""
    from datetime import datetime
    return (
        db.query(Slot)
        .filter(Slot.is_booked == False, Slot.slot_start > datetime.utcnow())
        .order_by(Slot.slot_start)
        .all()
    )
