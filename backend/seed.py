# seed.py – Seed the `slots` table with available appointment slots.
# Called once at startup; safe to run multiple times (skips existing slots).

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Slot
from config import SLOT_HOUR_START, SLOT_HOUR_END

logger = logging.getLogger(__name__)


def _next_calendar_days(n: int) -> list[datetime.date]:
    """Return the next `n` calendar days starting from tomorrow."""
    days = []
    candidate = datetime.utcnow().date() + timedelta(days=1)
    for _ in range(n):
        days.append(candidate)
        candidate += timedelta(days=1)
    return days


def seed_slots():
    """
    Insert hourly slots for the next 14 days (10:00–16:00 UTC).
    Skips any slot that already exists in the DB.
    """
    db: Session = SessionLocal()
    try:
        created = 0
        # Seed tomorrow through next 14 days
        for day in _next_calendar_days(14):
            for hour in range(SLOT_HOUR_START, SLOT_HOUR_END):   # 10, 11, ..., 16
                slot_dt = datetime(day.year, day.month, day.day, hour, 0, 0)
                exists = db.query(Slot).filter(Slot.slot_start == slot_dt).first()
                if not exists:
                    db.add(Slot(slot_start=slot_dt))
                    created += 1
        db.commit()
        logger.info(f"Slots seeded: {created} new slots added")
    except Exception as e:
        db.rollback()
        logger.error(f"Slot seeding failed: {e}")
    finally:
        db.close()

