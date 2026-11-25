import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.rag_service import rag_service

async def main():
    print("Testing startup RAG loading...")
    await rag_service.load()
    print(f"Chunks loaded: {len(rag_service.chunks)}")

if __name__ == "__main__":
    asyncio.run(main())
