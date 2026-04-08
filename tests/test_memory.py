"""
Test Memory Persistence and Retrieval.
"""
import os
import httpx
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

async def test_memory():
    base_url = "http://127.0.0.1:8000/test/message"

    # 1. Send first message
    print("1️⃣ Sending Message 1: 'My board is stuck loading'")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp1 = await client.post(base_url, json={
            "channel": "whatsapp",
            "content": "My board is stuck loading",
            "customer_name": "MemoryTestUser",
            "metadata": {"wa_id": TEST_WA_ID}
        })
        print(f"   Response: {resp1.json()['response'][:50]}...")

    # 2. Send second message referencing the first
    print("\n2️⃣ Sending Message 2: 'Is it fixed yet?'")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp2 = await client.post(base_url, json={
            "channel": "whatsapp",
            "content": "Is it fixed yet?",
            "customer_name": "MemoryTestUser",
            "metadata": {"wa_id": TEST_WA_ID}
        })
        reply = resp2.json()['response']
        print(f"   Response: {reply}")
        
        # 3. Check if response references previous context
        if "board" in reply.lower() or "stuck" in reply.lower() or "still" in reply.lower():
            print("\n✅ SUCCESS: Agent remembered the board issue!")
        else:
            print("\n❌ FAIL: Agent did not mention the board issue.")

asyncio.run(test_memory())
