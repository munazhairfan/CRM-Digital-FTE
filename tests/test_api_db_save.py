import httpx
import asyncio
import os
import asyncpg
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    print("1. Sending message via Local Server API...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8000/test/message",
            json={
                "channel": "whatsapp",
                "content": "verify if THIS saves to db via api",
                "customer_name": "ApiTestUser"
            },
            timeout=30.0
        )
        print(f"   Server Response: {resp.status_code}")

    print("2. Checking Database directly...")
    try:
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        row = await conn.fetchrow(
            """
            SELECT c.id, c.status, c.sentiment_score 
            FROM conversations c
            JOIN customers u ON u.id = c.customer_id
            WHERE u.name = $1
            ORDER BY c.started_at DESC
            LIMIT 1
            """,
            "ApiTestUser"
        )
        
        if row:
            print(f"   ✅ FOUND in DB!")
            print(f"   - ID: {row['id']}")
            print(f"   - Status: {row['status']}")
        else:
            print("   ❌ NOT FOUND in DB")
        await conn.close()
    except Exception as e:
        print(f"   ⚠️ DB Error: {e}")

asyncio.run(test())
