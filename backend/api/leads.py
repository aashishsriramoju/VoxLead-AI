# api/leads.py – Read-only endpoints for lead data (used by Dashboard)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Lead
from schemas import LeadOut

router = APIRouter()


@router.get("/", response_model=List[LeadOut])
def get_leads(db: Session = Depends(get_db)):
    """Return all leads, newest first."""
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Return a single lead by ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
