import asyncio, json, sys
from dotenv import load_dotenv
load_dotenv(override=True)
from production.agents.classifier import classify_message

async def test():
    print("🔍 Classifying 'worst ever' message...", flush=True)
    content = "this product is the worst ever!! nothing works 😡"
    res = await classify_message("whatsapp", content, {})
    print(f"📦 Result: {json.dumps(res, indent=2)}", flush=True)

asyncio.run(test())
