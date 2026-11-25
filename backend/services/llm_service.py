# services/llm_service.py – Wrapper around the Google Gemini API
# Phase 1 stub: contains only the client initialisation.
# Full implementation added in Phase 2.

import logging
from config import GEMINI_API_KEY, GEMINI_FLASH_MODEL, GEMINI_EMBEDDING_MODEL
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Initialise the official google-genai client once at module load.
# All service modules import `gemini_client` from here.
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

logger.info(f"Gemini client initialised (model={GEMINI_FLASH_MODEL})")
