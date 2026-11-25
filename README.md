# VoxLead AI 🎙️

**Autonomous AI sales voice agent** — talks to customers by voice, answers questions from company docs, qualifies leads, books demos, and summarises calls.

Built for a technical interview MVP in 6 hours using **Python + FastAPI + Gemini + React**.

---

## Quick Start

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp ../.env.example .env          # fill in your GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for the interactive API (Swagger UI).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### Run tests

```bash
cd backend
pytest tests/ -v
```

---

## Project Structure

```
VoxLead-AI/
├── backend/
│   ├── main.py          # FastAPI app + startup
│   ├── config.py        # All env vars in one place
│   ├── database.py      # SQLAlchemy engine + session
│   ├── models.py        # DB tables (Call, Message, Lead, Appointment, Slot)
│   ├── schemas.py       # Pydantic request/response models
│   ├── seed.py          # Seeds time slots on startup
│   ├── api/             # Thin HTTP route handlers (no business logic)
│   ├── services/        # All AI and business logic
│   │   ├── llm_service.py    # Gemini client
│   │   ├── agent_service.py  # Conversation orchestrator
│   │   ├── rag_service.py    # Document loading + embedding + retrieval
│   │   ├── lead_service.py   # Deterministic lead scoring
│   │   ├── booking_service.py# Slot checking and booking
│   │   └── summary_service.py# End-of-call summary
│   ├── knowledge_base/  # Drop your .md, .txt, .pdf files here
│   └── tests/           # 3 pytest tests for lead scoring
├── frontend/src/
│   ├── App.jsx
│   ├── components/
│   │   ├── VoiceInterface.jsx   # Mic button, STT/TTS, language picker
│   │   ├── ChatWindow.jsx       # Message bubbles with sentiment badges
│   │   └── Dashboard.jsx        # Leads + Appointments + Call history
│   └── services/api.js          # Axios wrappers for the backend
├── docs/
│   ├── architecture.md   # Mermaid diagram + design decisions
│   └── project-report.md # Problem, implementation, scalability, security
└── .env.example
```

---

## Knowledge Base

Drop any `.md`, `.txt`, or `.pdf` files into `backend/knowledge_base/` and call:

```
POST /api/kb/reload
```

The agent will answer questions **only** from these documents.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google AI Studio key |
| `GEMINI_FLASH_MODEL` | Default: `gemini-2.0-flash` |
| `GEMINI_EMBEDDING_MODEL` | Default: `text-embedding-004` |
| `RAG_SIMILARITY_THRESHOLD` | Min cosine similarity to use a chunk (default: 0.60) |
| `RAG_TOP_K` | Number of chunks to retrieve (default: 4) |

---

*Built by Aashish – VoxLead AI MVP, 2024*
