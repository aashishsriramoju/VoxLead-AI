# main.py – FastAPI application entry point
# Responsibilities: create the app, wire routers, run startup tasks (init DB, seed slots, load RAG).

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from seed import seed_slots  # seeds available appointment slots

# API route modules (thin wrappers that call service layer)
from api import call, leads, appointments, kb, calls_history

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup before the first request is served.
    - Creates DB tables
    - Seeds time slots for the next 5 working days
    - Loads and embeds the knowledge base (RAG)
    """
    logger.info("=== VoxLead AI starting up ===")
    init_db()
    logger.info("Database initialised")

    seed_slots()
    logger.info("Slots seeded")

    # Import here so RAG embedding only happens once
    from services.rag_service import rag_service
    await rag_service.load()
    logger.info("RAG service ready")

    yield  # <-- app runs here

    logger.info("=== VoxLead AI shutting down ===")


app = FastAPI(
    title="VoxLead AI",
    description="Autonomous AI sales voice agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Vite dev server (port 5173) to call the backend (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers – each maps a path prefix to a module in api/
app.include_router(call.router,          prefix="/api/call",         tags=["Call"])
app.include_router(leads.router,         prefix="/api/leads",        tags=["Leads"])
app.include_router(appointments.router,  prefix="/api/appointments",  tags=["Appointments"])
app.include_router(calls_history.router, prefix="/api/calls",         tags=["Calls History"])
app.include_router(kb.router,            prefix="/api/kb",            tags=["Knowledge Base"])


@app.get("/health", tags=["Health"])
def health():
    """Simple liveness check – confirm the server is running."""
    return {"status": "ok", "service": "VoxLead AI"}
