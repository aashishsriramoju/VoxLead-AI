# VoxLead AI 🎙️

**Autonomous AI Sales Voice Agent** — talks to customers by voice, answers questions strictly from company documents, qualifies leads deterministically, schedules demos into live calendar slots, and generates post-call CRM summaries.

Built as a technical interview MVP with **Python + FastAPI + Google Gemini + React (Vite)**.

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt
cp ../.env.example .env
```

Edit `.env` and set your `GEMINI_API_KEY`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_FLASH_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
DATABASE_URL=sqlite:///./voxlead.db
RAG_SIMILARITY_THRESHOLD=0.60
RAG_TOP_K=4
```

Start the FastAPI backend:
```bash
python -m uvicorn main:app --reload --port 8000
```
- Interactive API Docs (Swagger): **http://localhost:8000/docs**
- Health Check: **http://localhost:8000/health**

---

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in Google Chrome or Microsoft Edge (recommended for Web Speech API support).

---

## 🧪 Running Automated Tests

Run the deterministic lead-scoring unit test suite:
```bash
cd backend
python -m pytest tests/test_lead_scoring.py -v
```

Run RAG cosine similarity and chunking tests:
```bash
cd backend
python tests/test_rag.py
```

Run slot booking verification:
```bash
cd backend
python tests/test_booking.py
```

---

## 📁 Repository Structure

```
VoxLead-AI/
├── backend/
│   ├── main.py                  # FastAPI application entry point & CORS
│   ├── config.py                # Environment configurations (single source of truth)
│   ├── database.py              # SQLAlchemy engine, session maker & Base
│   ├── models.py                # ORM models (Call, Message, Lead, Appointment, Slot)
│   ├── schemas.py               # Pydantic request & response validation schemas
│   ├── seed.py                  # Automatic 5-day slot generator (10:00-17:00 UTC)
│   ├── api/                     # Thin HTTP route handlers (No business logic)
│   │   ├── call.py              # POST /start, POST /{id}/turn, POST /{id}/end
│   │   ├── leads.py             # GET /api/leads
│   │   ├── appointments.py      # GET /api/appointments, GET /api/appointments/slots
│   │   ├── calls_history.py     # GET /api/calls
│   │   └── kb.py                # POST /api/kb/reload
│   ├── services/                # All AI and Business Logic
│   │   ├── llm_service.py       # Official google-genai client wrapper
│   │   ├── agent_service.py     # Multi-turn conversation orchestrator & memory
│   │   ├── rag_service.py       # Custom RAG (pypdf, heading chunker, SHA-256 cache, numpy cosine)
│   │   ├── lead_service.py      # Deterministic 100-pt rule-based lead qualification
│   │   ├── booking_service.py   # Calendar slot validation & appointment confirmation
│   │   └── summary_service.py   # Post-call transcript analysis & CRM summary
│   ├── knowledge_base/          # Drop company docs (.md, .txt, .pdf) here
│   └── tests/                   # Pytest unit tests
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main shell with view switcher (Voice Agent & Dashboard)
│   │   ├── App.css              # Custom responsive stylesheet (zero external UI libraries)
│   │   ├── components/
│   │   │   ├── VoiceInterface.jsx  # Web Speech STT/TTS & audio loop prevention
│   │   │   ├── ChatWindow.jsx      # Message log with sentiment badges & RAG citations
│   │   │   ├── Sidebar.jsx         # Live lead card, progress bar & appointment confirmation
│   │   │   └── Dashboard.jsx       # Tabbed CRM analytics for leads, appts, and calls
│   │   └── services/
│   │       └── api.js           # Native fetch REST client
├── docs/
│   ├── architecture.md          # Full architectural design document with Mermaid diagram
│   └── project-report.md        # Technical, commercial, scalability & security report
├── .env.example
├── .gitignore
└── README.md
```

---

## 📚 Knowledge Base (RAG) Usage

1. Place your company documents (`.md`, `.txt`, or `.pdf`) inside `backend/knowledge_base/` (e.g. `services_pricing.md`, `refund_policy.md`, `terms_of_service.md`).
2. Trigger the reload endpoint to index and embed them:
```bash
curl -X POST http://localhost:8000/api/kb/reload
```
3. VoxLead AI will now answer questions **strictly** from these documents, citing the exact document and section under every response.

---

## 🔗 Linking to GitHub (Public Repository)

To push this project to your GitHub account:

1. Create a new public repository on GitHub named `VoxLead-AI` at [github.com/new](https://github.com/new).
2. Run the following commands in your terminal:

```bash
cd C:\Users\AASHISH\Documents\SEM7\VoxLead-AI
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/VoxLead-AI.git
git branch -M main
git push -u origin main
```
