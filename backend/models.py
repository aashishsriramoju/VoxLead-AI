# models.py – SQLAlchemy ORM table definitions
# Each class maps directly to one database table.
# Keep this file as the single source of truth for the DB schema.

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Call(Base):
    """One call session with a customer."""
    __tablename__ = "calls"

    id            = Column(Integer, primary_key=True, index=True)
    started_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at      = Column(DateTime, nullable=True)
    language      = Column(String(10), default="en-IN")   # BCP-47 code
    summary       = Column(Text, nullable=True)           # filled by /end
    insights      = Column(Text, nullable=True)           # JSON string
    overall_sentiment = Column(String(10), nullable=True) # positive/neutral/negative

    # Relationships – lazy='select' is SQLAlchemy default; keeps queries simple
    messages = relationship("Message", back_populates="call", cascade="all, delete-orphan")
    lead     = relationship("Lead",    back_populates="call", uselist=False, cascade="all, delete-orphan")


class Message(Base):
    """One turn in the conversation (role: 'user' or 'assistant')."""
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    call_id    = Column(Integer, ForeignKey("calls.id"), nullable=False)
    role       = Column(String(10), nullable=False)   # "user" | "assistant"
    text       = Column(Text, nullable=False)
    sentiment  = Column(String(10), nullable=True)    # positive/neutral/negative
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    call = relationship("Call", back_populates="messages")


class Lead(Base):
    """
    Qualification data collected during the call.
    One lead per call; fields are filled incrementally across turns.
    """
    __tablename__ = "leads"

    id           = Column(Integer, primary_key=True, index=True)
    call_id      = Column(Integer, ForeignKey("calls.id"), unique=True, nullable=False)

    # Contact info – collected by the agent
    name         = Column(String(200), nullable=True)
    phone        = Column(String(50),  nullable=True)
    company      = Column(String(200), nullable=True)

    # Qualification fields
    budget        = Column(Float, nullable=True)          # in USD/month
    team_size     = Column(Integer, nullable=True)
    requirements  = Column(Text, nullable=True)
    timeline_days = Column(Integer, nullable=True)        # days to decision

    # Computed by lead_service, NOT by the LLM
    sentiment  = Column(String(10), default="neutral")
    score      = Column(Float, default=0.0)               # 0-100
    status     = Column(String(10), default="cold")       # hot/warm/cold
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    call         = relationship("Call", back_populates="lead")
    appointments = relationship("Appointment", back_populates="lead", cascade="all, delete-orphan")


class Appointment(Base):
    """A booked demo slot linked to a lead."""
    __tablename__ = "appointments"

    id         = Column(Integer, primary_key=True, index=True)
    lead_id    = Column(Integer, ForeignKey("leads.id"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    status     = Column(String(20), default="confirmed")  # confirmed/cancelled

    lead = relationship("Lead", back_populates="appointments")


class Slot(Base):
    """
    Pre-seeded available time slots.
    Seeded at startup for the next 5 working days, 10:00-16:00 hourly.
    booking_service marks is_booked=True when a slot is taken.
    """
    __tablename__ = "slots"

    id         = Column(Integer, primary_key=True, index=True)
    slot_start = Column(DateTime, unique=True, nullable=False, index=True)
    is_booked  = Column(Boolean, default=False, nullable=False)
