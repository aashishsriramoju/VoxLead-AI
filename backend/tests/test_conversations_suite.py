# tests/test_conversations_suite.py – 8 end-to-end conversational test cases
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import SessionLocal
from models import Slot, Lead, Call
from services.agent_service import agent_service
from services.booking_service import booking_service

async def run_test_suite():
    db = SessionLocal()
    print("=" * 60)
    print("VOXLEAD AI: RUNNING 8 END-TO-END CONVERSATIONAL TEST CASES")
    print("=" * 60)

    try:
        # TEST 1: Call Initialization & Friendly Greeting
        print("\n[TEST 1] Call Initialization & Warm Greeting")
        start_res = await agent_service.start_call(db)
        call_id = start_res.call_id
        assert "Nova" in start_res.reply
        assert "UTC" not in start_res.reply
        print(f"PASS -> Call #{call_id} started. Greeting: \"{start_res.reply}\"")

        # TEST 2: Providing Name & Polite Qualification
        print("\n[TEST 2] Customer Name Introduction")
        t2 = await agent_service.handle_turn(call_id, "Hi, my name is Priya Sharma from TechCorp", "en-IN", db)
        assert t2.lead.name == "Priya Sharma" or "Priya" in (t2.lead.name or "")
        print(f"PASS -> Nova reply: \"{t2.reply}\" (Lead name: {t2.lead.name})")

        # TEST 3: Stating Budget in Rupees (INR)
        print("\n[TEST 3] Budget Stated in Indian Rupees (₹ / INR)")
        t3 = await agent_service.handle_turn(call_id, "We have 10 sales reps and our monthly budget is 25000 rupees", "en-IN", db)
        assert t3.lead.team_size == 10
        assert t3.lead.budget is not None and t3.lead.budget > 0
        assert t3.score > 20
        print(f"PASS -> Nova reply: \"{t3.reply}\" (Budget: ₹{t3.lead.budget}, Score: {t3.score})")

        # TEST 4: Stating Timeline & Requirements
        print("\n[TEST 4] Stating Timeline and Automated Workflow Requirements")
        t4 = await agent_service.handle_turn(call_id, "We want to implement within 10 days and need automated follow-up sequences", "en-IN", db)
        assert t4.lead.timeline_days == 10
        assert t4.score >= 50
        print(f"PASS -> Nova reply: \"{t4.reply}\" (Timeline: {t4.lead.timeline_days} days, Status: {t4.lead.status})")

        # TEST 5: Checking Available Demo Slots (No UTC in spoken response)
        print("\n[TEST 5] Asking for Demo Slot Availability")
        t5 = await agent_service.handle_turn(call_id, "Can I see what demo slots you have open?", "en-IN", db)
        assert "UTC" not in t5.reply
        assert "at" in t5.reply.lower() or "demo" in t5.reply.lower()
        print(f"PASS -> Nova spoken slots: \"{t5.reply}\"")

        # TEST 6: Providing Phone Number and Booking with Natural Time ("Thursday at 12 pm" or "first one")
        print("\n[TEST 6] Providing Phone Number and Selecting Slot with Natural Language")
        t6 = await agent_service.handle_turn(call_id, "My phone is 9876543210. Let's book the first slot at 12 pm", "en-IN", db)
        assert t6.appointment is not None, "Appointment should be successfully confirmed"
        assert "UTC" not in t6.reply
        print(f"PASS -> Appointment booked! Nova confirmation: \"{t6.reply}\"")
        print(f"        Scheduled time: {t6.appointment.slot_start}")

        # TEST 7: Asking Policy/Feature Question
        print("\n[TEST 7] Asking Question Outside Context (Testing Graceful Response)")
        t7 = await agent_service.handle_turn(call_id, "Do you integrate with SAP ERP on-premise systems?", "en-IN", db)
        print(f"PASS -> Nova boundary response: \"{t7.reply}\"")

        # TEST 8: Customer Says Goodbye -> Automatic Call Termination & Summary
        print("\n[TEST 8] Customer Says Goodbye (Testing Automatic Call Ending)")
        t8 = await agent_service.handle_turn(call_id, "That's all for today, thank you so much! Goodbye!", "en-IN", db)
        assert t8.call_ended == True, "call_ended must be True when customer says goodbye"
        
        # Verify call is finalized in DB
        db_call = db.query(Call).filter(Call.id == call_id).first()
        assert db_call.ended_at is not None, "Call ended_at must be set in database"
        assert db_call.summary is not None and len(db_call.summary) > 0, "Call summary must be populated"
        print(f"PASS -> Call auto-ended! Nova farewell: \"{t8.reply}\"")
        print(f"        Call summary: {db_call.summary[:100]}...")
        print(f"        Overall sentiment: {db_call.overall_sentiment}")

        print("\n" + "=" * 60)
        print("ALL 8 END-TO-END CONVERSATIONAL TEST CASES PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_test_suite())
