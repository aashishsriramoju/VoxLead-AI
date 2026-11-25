import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.rag_service import rag_service, KB_DIR, CACHE_FILE

async def test_full_rag_cycle():
    # 1. Create a sample markdown doc
    test_file = os.path.join(KB_DIR, "pricing_policy.md")
    content = """# NovaCRM Pricing
NovaCRM Starter starts at $29 per user per month.
NovaCRM Growth is $79 per user per month including automated sales workflows.

# Refund Policy
Refunds are available within 14 days of initial subscription purchase.
All cancellation requests must be sent to support@novacrm.com.
"""
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)

    print("Created test file:", test_file)

    try:
        # 2. Reload RAG
        # Note: embedding call to Gemini will return None if API key invalid, which rag_service gracefully handles
        await rag_service.load(force_reload=True)
        print(f"RAG reloaded successfully with test file. Cached chunks: {len(rag_service.chunks)}")
        
        # Verify chunks extraction
        from services.rag_service import _split_into_chunks
        chunks = _split_into_chunks(content, "pricing_policy.md")
        print(f"Verified chunking: {len(chunks)} chunks extracted.")
        for c in chunks:
            print(f" - [{c['file']} > {c['section']}]: {c['text'][:60]}...")

    finally:
        # Clean up test file and cache so knowledge_base is left pristine
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        print("Cleaned up test file and cache. Knowledge base folder left clean.")

if __name__ == "__main__":
    asyncio.run(test_full_rag_cycle())
