import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import SessionLocal
from models import Call, Message
from services.summary_service import summary_service

async def test_summary_flow():
    db = SessionLocal()
    try:
        call = Call(language="en-IN")
        db.add(call)
        db.flush()

        db.add(Message(call_id=call.id, role="assistant", text="Hi, I am Nova! What is your name?", sentiment="positive"))
        db.add(Message(call_id=call.id, role="user", text="I am Alex, looking for CRM software for 10 users.", sentiment="positive"))
        db.add(Message(call_id=call.id, role="assistant", text="NovaCRM supports up to 100 users on Growth plan. What is your timeline?", sentiment="neutral"))
        db.add(Message(call_id=call.id, role="user", text="We want to buy within 2 weeks.", sentiment="positive"))
        db.commit()

        # Run summary service
        result = await summary_service.summarise(call.id, db)
        print("Summary Result:")
        print(" - Summary:", result["summary"])
        print(" - Sentiment:", result["overall_sentiment"])
        print(" - Insights:", result["insights"])

        assert len(result["summary"]) > 0
        assert result["overall_sentiment"] in ["positive", "neutral", "negative"]
        print("Summary service test PASSED!")
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    asyncio.run(test_summary_flow())
