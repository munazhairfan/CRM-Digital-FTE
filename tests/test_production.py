"""End-to-end test of the production pipeline."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

async def main():
    from production.workers.message_processor import process_incoming_message

    test_message = {
        "channel": "whatsapp",
        "content": "hi pls how do i invite my team??",
        "metadata": {"wa_id": TEST_WA_ID, "name": "Bilal"},
    }

    print("=" * 60)
    print("PRODUCTION END-TO-END TEST")
    print("=" * 60)
    print(f"\n📨 Input: {test_message['content']}")
    print(f"   Channel: {test_message['channel']}")
    print(f"   Customer: {test_message['metadata']['name']}")
    print()

    result = await process_incoming_message(test_message)

    print(f"\n{'─' * 60}")
    print("📝 RESULT:")
    print(f"{'─' * 60}")
    print(f"   Status: {result.get('status')}")
    print(f"   Response: {result.get('response', 'N/A')}")
    print(f"{'─' * 60}")
    print("\n✅ TEST COMPLETE")

asyncio.run(main())
