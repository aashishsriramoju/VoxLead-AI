# schemas.py – Pydantic models for request/response validation
# FastAPI uses these to auto-validate input and auto-generate OpenAPI docs.
# Keep them close to the domain language so they're easy to explain in interviews.

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Shared / nested ──────────────────────────────────────────────────────────

class SourceChunk(BaseModel):
    """A retrieved RAG chunk reference shown in the UI."""
    file: str
    section: str
    score: float


class LeadFields(BaseModel):
    """
    Fields the LLM can populate inside its JSON reply.
    All are Optional because the LLM fills them incrementally.
    """
    name: Optional[str]          = None
    phone: Optional[str]         = None
    company: Optional[str]       = None
    budget: Optional[float]      = None   # USD/month
    team_size: Optional[int]     = None
    requirements: Optional[str]  = None
    timeline_days: Optional[int] = None


class LLMResponse(BaseModel):
    """
    The EXACT JSON structure Gemini must return for every /turn call.
    Validated with Pydantic; if validation fails we retry once then fall back.
    """
    reply: str
    sentiment: str                            # positive | neutral | negative
    lead_fields: Optional[LeadFields]         = None
    action: str                               = "none"  # none | check_slots | book_appointment
    requested_slot: Optional[str]             = None    # ISO datetime string
    language: str                             = "en-IN"


# ── Call ─────────────────────────────────────────────────────────────────────

class CallStartResponse(BaseModel):
    call_id: int
    reply: str           # greeting message


class TurnRequest(BaseModel):
    text: str            # transcribed speech (or typed text)
    language: str = "en-IN"


class TurnResponse(BaseModel):
    reply: str
    sentiment: str
    lead: Optional[LeadOut]       = None
    score: float                   = 0.0
    appointment: Optional[AppointmentOut] = None
    sources: List[SourceChunk]    = []


class EndCallResponse(BaseModel):
    summary: str
    insights: str        # raw JSON string of key insight categories
    overall_sentiment: str


# ── Lead ─────────────────────────────────────────────────────────────────────

class LeadOut(BaseModel):
    id: int
    call_id: int
    name: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    budget: Optional[float]
    team_size: Optional[int]
    requirements: Optional[str]
    timeline_days: Optional[int]
    sentiment: str
    score: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Appointment ───────────────────────────────────────────────────────────────

class AppointmentOut(BaseModel):
    id: int
    lead_id: int
    slot_start: datetime
    status: str

    model_config = {"from_attributes": True}


# ── Slot ──────────────────────────────────────────────────────────────────────

class SlotOut(BaseModel):
    id: int
    slot_start: datetime
    is_booked: bool

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class CallOut(BaseModel):
    id: int
    started_at: datetime
    ended_at: Optional[datetime]
    language: str
    summary: Optional[str]
    insights: Optional[str]
    overall_sentiment: Optional[str]

    model_config = {"from_attributes": True}


# Forward references resolved (Python 3.9 compat)
TurnResponse.model_rebuild()
