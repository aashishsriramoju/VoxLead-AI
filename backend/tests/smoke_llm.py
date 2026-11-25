import asyncio, json, sys
sys.path.insert(0, '.')
from services.llm_service import generate, embed

PROMPT = 'Reply ONLY with valid JSON matching this schema: {"reply": str, "sentiment": "positive|neutral|negative", "lead_fields": null, "action": "none", "requested_slot": null, "language": "en-IN"}'

async def test():
    result = await generate(
        system_prompt=PROMPT,
        history=[],
        user_message='Hi there, tell me about NovaCRM'
    )
    print('RAW:', result[:400] if result else 'None')
    if result:
        try:
            parsed = json.loads(result)
            print('PARSED reply:', parsed.get('reply'))
        except Exception as e:
            print('JSON parse error:', e)

    vec = await embed('What is CRM software')
    print('EMBED dims:', len(vec) if vec else 'FAILED')

asyncio.run(test())
