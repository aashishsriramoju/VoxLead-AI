# VoxLead AI – Architecture & System Design Document

## 1. Executive Architecture Overview

VoxLead AI is an autonomous, real-time AI sales voice agent designed to qualify customer inbound enquiries, answer company product and policy questions strictly from verified documentation, schedule demo appointments into live calendar slots, and generate post-call CRM summaries.

The system is constructed as a **modular monolith** adhering strictly to separation of concerns:
- **Presentation Layer (Frontend)**: React (Vite) utilizing native browser Web Speech API for Client-Side STT (Speech-to-Text) and TTS (Text-to-Speech). No external UI component frameworks.
- **API Layer (Transport)**: FastAPI exposing asynchronous REST endpoints (`/api/call`, `/api/leads`, `/api/appointments`, `/api/kb`). Routers are thin controllers that do not contain business logic.
- **Domain & Service Layer**: Specialized Python service singletons (`agent_service`, `rag_service`, `llm_service`, `lead_service`, `booking_service`, `summary_service`).
- **Data Layer**: SQLAlchemy 2.0 ORM with SQLite (zero-config, swappable to PostgreSQL via `DATABASE_URL`).
- **Foundation AI Models**: Google Gemini 2.0 Flash (LLM) and `text-embedding-004` via the official `google-genai` SDK.

---

## 2. System Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Client Browser (React + Web Speech API)"]
        UI["React UI (Vite)"]
        STT["Web Speech Recognition (STT)<br/>en-IN / hi-IN / te-IN"]
        TTS["Web Speech Synthesis (TTS)<br/>Auto-mic Mute Prevention"]
        UI -->|Spoken Voice| STT
        STT -->|Transcribed Text| UI
        TTS -->|Spoken Audio| UI
    end

    subgraph API["FastAPI Application (Port 8000)"]
        RouterCall["api/call.py<br/>/start, /{id}/turn, /{id}/end"]
        RouterLeads["api/leads.py<br/>/leads"]
        RouterAppt["api/appointments.py<br/>/appointments, /slots"]
        RouterKB["api/kb.py<br/>/kb/reload"]
    end

    subgraph Services["Core Service Layer"]
        Agent["agent_service.py<br/>Turn Orchestration & Prompting"]
        RAG["rag_service.py<br/>Heading Chunking & Cosine Sim"]
        LLM["llm_service.py<br/>Gemini 2.0 Flash Client"]
        LeadSvc["lead_service.py<br/>Deterministic 100-pt Scoring"]
        BookSvc["booking_service.py<br/>Slot Validation & Booking"]
        SummSvc["summary_service.py<br/>Transcript Analysis"]
    end

    subgraph External["Google Gemini AI"]
        GeminiFlash["Gemini 2.0 Flash<br/>JSON Extraction & Dialogue"]
        GeminiEmbed["text-embedding-004<br/>768-dim Vector Embeddings"]
    end

    subgraph Storage["Persistence & Knowledge Base"]
        DB[("SQLite Database<br/>calls, messages, leads,<br/>appointments, slots")]
        KBFiles["Knowledge Base Docs<br/>(.md, .txt, .pdf)"]
        KBCache[("knowledge_base/.cache.json<br/>SHA-256 Hashes & Vectors")]
    end

    UI -->|POST /turn {text}| RouterCall
    RouterCall --> Agent
    Agent -->|1. Load History| DB
    Agent -->|2. Query Search| RAG
    RAG -->|Read Docs| KBFiles
    RAG -->|Read/Write Vectors| KBCache
    RAG -->|Embed Query| GeminiEmbed
    Agent -->|3. Generate JSON Reply| LLM
    LLM --> GeminiFlash
    Agent -->|4. Update & Score Lead| LeadSvc
    LeadSvc -->|Save Lead & Score| DB
    Agent -->|5. Action Intent| BookSvc
    BookSvc -->|Update Slots / Appts| DB
    Agent -->|6. Save Messages| DB
    Agent -->|Return Response| RouterCall
    RouterCall -->|JSON Reply + Citations| UI
    UI -->|Spoken Reply| TTS

    RouterCall -->|POST /end| SummSvc
    SummSvc --> GeminiFlash
    SummSvc -->|Save Summary & Insights| DB
```

---

## 3. Detailed Data Flow & Execution Lifecycle

### Step 1: Call Initialization (`POST /api/call/start`)
1. User clicks **"Start Call with Nova"** on the React interface.
2. The endpoint creates a new `Call` row with timestamp and language.
3. A blank `Lead` record is created associated with `call_id`.
4. The initial greeting is stored as the first message (`role: assistant`) in the `messages` table.
5. The frontend receives `{call_id, reply}` and the browser speaks the greeting via `speechSynthesis`.

### Step 2: Conversation Turn (`POST /api/call/{id}/turn`)
1. **Voice Capture**: Browser's `SpeechRecognition` transcribes spoken speech into text (e.g., *"Hi, I'm Rahul from Acme Corp, we need CRM for 20 reps, what are your pricing plans?"*).
2. **Context Retrieval (RAG)**:
   - `rag_service.retrieve(query)` embeds the query via Gemini `text-embedding-004`.
   - Computes cosine similarity with in-memory cached vectors using `numpy`.
   - Drops any chunks below `RAG_SIMILARITY_THRESHOLD` (0.60).
   - Returns top 4 chunks with metadata `{file, section, score}`.
3. **Prompt Composition**:
   - Compiles system prompt with strict rules (max 2 short sentences, answer policy ONLY from context, cite sources, ask 1 qualification question).
   - Injects the `<context>` block.
   - Appends full multi-turn DB conversation history to maintain contextual memory.
4. **Structured LLM Inference**:
   - Calls Gemini 2.0 Flash with `response_mime_type="application/json"`.
   - Returns typed schema: `reply`, `sentiment`, `lead_fields`, `action`, `requested_slot`, `language`.
   - If invalid JSON is returned, retries once with an explicit correction nudge. If second attempt fails, returns a safe fallback message without crashing.
5. **Deterministic Lead Qualification**:
   - Extracts newly discovered fields (`name`, `phone`, `budget`, `team_size`, `timeline_days`, `requirements`).
   - `lead_service.calculate_lead_score` executes a 100-point deterministic evaluation:
     - Budget: up to 25 pts
     - Timeline: up to 25 pts
     - Requirements: up to 25 pts
     - Engagement: up to 25 pts
   - Status tagged as `hot` (>=70), `warm` (40-69), or `cold` (<40).
6. **Backend Action Execution**:
   - If `action == "check_slots"`: queries future unbooked rows from `slots` table.
   - If `action == "book_appointment"`: validates requested timestamp, marks `slot.is_booked = True`, creates `Appointment`.
7. **Storage & UI Update**:
   - Stores user and assistant messages with sentiment in `messages` table.
   - Returns `{reply, sentiment, lead, score, appointment, sources}` to frontend.
   - Browser speaks the reply while temporarily disabling the microphone to prevent echo/feedback loops.

### Step 3: Call Termination & Summary (`POST /api/call/{id}/end`)
1. Updates `call.ended_at`.
2. `summary_service` formats the entire transcript and instructs Gemini to generate:
   - 3-5 line executive summary.
   - Key structured insights: customer interests, objections, unanswered questions, and next steps.
   - Overall conversation sentiment.
3. Saves results to `calls` table and updates the CRM Dashboard.

---

## 4. Key Architectural Decisions & Interview Defense

### 1. Why REST instead of WebSockets?
- **Decision**: Used standard HTTP POST `/turn` requests rather than full-duplex WebSockets.
- **Justification**: Since audio processing (STT and TTS) occurs on the client via the browser's Web Speech API, only text payloads are transmitted over the wire. REST provides automatic idempotency, simpler stateless horizontal scaling behind load balancers, direct compatibility with OpenAPI/Swagger, and easier debugging without persistent socket connection leaks.

### 2. Why No LangChain or ChromaDB?
- **Decision**: Built a custom 120-line RAG service using pure Python, `pypdf`, and `numpy`.
- **Justification**: Heavy frameworks like LangChain introduce massive dependency bloat, frequent breaking changes, opaque abstractions, and latency overhead. A custom RAG service using SHA-256 file hashing, heading-aware chunking, and numpy cosine similarity runs in < 5ms locally, has zero external server dependencies, and is 100% understandable and defensible in an interview.

### 3. Why Rule-Based Lead Scoring Instead of LLM Scoring?
- **Decision**: Scoring is calculated deterministically in `lead_service.py`, never by the LLM.
- **Justification**: LLMs suffer from non-deterministic evaluation, hallucinations, and score drift across conversation turns. Business sales pipelines require predictable, auditable scoring rules (e.g. Budget >= $1,000 always yields 25 pts; Timeline <= 14 days always yields 25 pts). Rule-based scoring allows writing deterministic unit tests that execute in milliseconds.

### 4. Audio Feedback Prevention
- **Decision**: Frontend explicitly stops `SpeechRecognition` when `speechSynthesis` begins speaking (`utterance.onstart`), and only resumes when `utterance.onend` fires.
- **Justification**: Solves the classic browser voice agent acoustic loop where the microphone picks up the computer's speakers and transcribes the agent's own output as customer speech.
