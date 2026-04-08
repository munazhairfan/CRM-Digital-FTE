import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.agent_service import process_customer_message

async def test():
    print("1. Sending test message...")
    
    # 1. Send a message
    result = await process_customer_message({
        "channel": "whatsapp",
        "content": "verify if this saves to db",
        "customer_name": "PersistenceTest",
        "metadata": {"wa_id": "999999999"}
    })
    
    print(f"   Agent replied: {result['response'][:50]}...")
    
    # 2. Check DB
    print("2. Checking Database...")
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
    
    async with DatabaseClient.get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.id, c.status, c.sentiment_score 
            FROM conversations c
            JOIN customers u ON u.id = c.customer_id
            WHERE u.name = $1
            ORDER BY c.started_at DESC
            LIMIT 1
            """,
            "PersistenceTest"
        )
        
        if row:
            print(f"   ✅ FOUND in DB!")
            print(f"   - ID: {row['id']}")
            print(f"   - Status: {row['status']}")
            print(f"   - Sentiment: {row['sentiment_score']}")
        else:
            print("   ❌ NOT FOUND in DB")

asyncio.run(test())
