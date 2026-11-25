# config.py – Central place for all settings loaded from .env
# Every secret/config value lives here; nothing is hard-coded elsewhere.

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file from the project root

# --- Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Flash model on the free tier (current active model with healthy quota)
GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.5-flash-lite")

# Text-embedding model available on the free tier
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# --- Database ---
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./voxlead.db")

# --- RAG ---
# Minimum cosine similarity to include a retrieved chunk in the prompt
RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.60"))
# How many top chunks to retrieve
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))

# --- Slots ---
SLOT_HOUR_START: int = 10   # 10:00 AM
SLOT_HOUR_END:   int = 17   # up to 17:00 (last slot starts at 16:00)
