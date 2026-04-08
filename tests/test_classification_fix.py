import asyncio, os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from production.agents.classifier import classify_message

cases = [
    {"content": "Hi team, I would like to know the difference between Pro and Enterprise plans.", "channel": "email"},
    {"content": "We are very happy with the platform. Just renewing our Pro subscription for another year.", "channel": "email"},
    {"content": "this product is the worst ever!! nothing works 😡", "channel": "whatsapp"},
]

async def main():
    for c in cases:
        result = await classify_message(c["channel"], c["content"], {})
        status = "✅ PASS" if not result["escalation_trigger"] else "⚠️ ESCALATED"
        if "worst ever" in c["content"] and result["escalation_trigger"]:
            status = "✅ PASS (Correctly Escalated)"
        print(f"{status}: {c['content'][:60]}...")
        print(f"   Escalation: {result['escalation_trigger'] or 'None'}")
        print()

asyncio.run(main())
