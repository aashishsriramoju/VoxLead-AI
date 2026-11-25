import sys
sys.path.insert(0, '.')
from services.agent_service import AgentService
agent = AgentService()

# Test 1: _try_parse with valid JSON
valid_json = '{"reply": "Hello! How can I help?", "sentiment": "positive", "lead_fields": null, "action": "none", "requested_slot": null, "language": "en-IN"}'
result = agent._try_parse(valid_json)
assert result is not None, "Should parse valid JSON"
assert result.reply == "Hello! How can I help?"
print("PASS: valid JSON parsed correctly")

# Test 2: _try_parse with invalid JSON returns None
result2 = agent._try_parse("not json at all {{")
assert result2 is None, "Should return None for bad JSON"
print("PASS: bad JSON returns None (graceful)")

# Test 3: _try_parse with markdown-wrapped JSON (LLM sometimes adds backticks)
wrapped = '```json\n{"reply": "Hi!", "sentiment": "neutral", "lead_fields": null, "action": "none", "requested_slot": null, "language": "en-IN"}\n```'
result3 = agent._try_parse(wrapped)
assert result3 is not None, "Should handle markdown-wrapped JSON"
print("PASS: markdown-wrapped JSON handled")

# Test 4: _merge_lead_fields
from models import Lead
from schemas import LeadFields
lead = Lead()
fields = LeadFields(name="Alice", phone="9876543210", budget=500.0, team_size=None)
agent._merge_lead_fields(lead, fields)
assert lead.name == "Alice"
assert lead.phone == "9876543210"
assert lead.budget == 500.0
assert lead.team_size is None   # null fields are NOT merged
print("PASS: lead fields merged, nulls skipped")

# Test 5: _build_context_block with no chunks
ctx = agent._build_context_block([])
assert "No relevant" in ctx
print("PASS: empty context block generated")

print("\nAll agent_service offline tests PASSED")
