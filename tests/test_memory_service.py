import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.memory_service import get_customer_context

async def test():
    print("🧪 Testing Memory Service Directly...")

    # 1. Init DB
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
    print("✅ DB Connected")

    # 2. Test with a known customer_id
    cid = os.getenv("TEST_WA_ID", "15550000000")
    print(f"🔍 Fetching history for {cid}...")
    
    ctx = await get_customer_context(cid)
    print(f"📦 Context Received:\n{ctx}")

asyncio.run(test())
