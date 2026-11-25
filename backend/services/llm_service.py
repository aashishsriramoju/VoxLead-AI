# services/llm_service.py – Wrapper around the Google Gemini API
#
# This file has ONE job: talk to Gemini.
# Everything else (prompts, memory, lead logic) lives in other services.
#
# Two public functions:
#   generate(prompt, history)  → str (raw text from Gemini)
#   embed(text)                → list[float] (embedding vector)

import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_FLASH_MODEL, GEMINI_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client – created once at module load, reused for every request.
# The google-genai SDK manages HTTP connection pooling internally.
# ---------------------------------------------------------------------------
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

logger.info(f"Gemini client ready  model={GEMINI_FLASH_MODEL}  embed={GEMINI_EMBEDDING_MODEL}")


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

async def generate(
    system_prompt: str,
    history: list[dict],   # [{"role": "user"|"model", "text": "..."}]
    user_message: str,
    temperature: float = 0.3,  # low = more deterministic JSON output
) -> Optional[str]:
    """
    Call Gemini and return the raw response text.
    Returns None on any API error so the caller can fall back gracefully.

    `history` follows the Gemini Content format:
        [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    We convert our simple dict format here.
    """
    try:
        # Build the contents list: past turns + the new user message
        contents: list[types.Content] = []

        for msg in history:
            # Gemini uses "model" not "assistant"
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg["text"])]
                )
            )

        # Append the current user turn
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
        )

        response = gemini_client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                # Force JSON output so we can parse it reliably
                response_mime_type="application/json",
            ),
        )

        return response.text

    except Exception as exc:
        logger.error(f"Gemini generate error: {exc}")
        return None


async def generate_plain(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.4,
) -> Optional[str]:
    """
    Simple one-shot text generation (no history, no JSON mode).
    Used by summary_service for the end-of-call summary.
    """
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[
                types.Content(role="user", parts=[types.Part(text=user_message)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )
        return response.text
    except Exception as exc:
        logger.error(f"Gemini plain generate error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

async def embed(text: str) -> Optional[list[float]]:
    """
    Embed a single string using Gemini's embedding model.
    Returns a list of floats, or None on error.
    Used by rag_service to embed both documents and queries.
    """
    try:
        response = gemini_client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=text,
        )
        # The SDK returns an EmbedContentResponse with .embeddings list
        return response.embeddings[0].values
    except Exception as exc:
        logger.error(f"Gemini embed error: {exc}")
        return None
