# api/calls_history.py – GET /api/calls for dashboard (past call records)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Call
from schemas import CallOut

router = APIRouter()


@router.get("/", response_model=List[CallOut])
def get_calls(db: Session = Depends(get_db)):
    """Return all past calls, newest first. Used by the Dashboard."""
    return db.query(Call).order_by(Call.started_at.desc()).all()
