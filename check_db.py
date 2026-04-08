import asyncio
import os
import asyncpg
from dotenv import load_dotenv
load_dotenv(override=True)

async def check():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    # Check total conversations
    count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
    print(f"Total Conversations in DB: {count}")
    
    # Check total customers
    c_count = await conn.fetchval("SELECT COUNT(*) FROM customers")
    print(f"Total Customers in DB: {c_count}")
    
    # Check recent
    recent = await conn.fetch("SELECT * FROM conversations ORDER BY started_at DESC LIMIT 3")
    for r in recent:
        print(f"  - ID: {r['id']}, Channel: {r['initial_channel']}, Sentiment: {r['sentiment_score']}")
        
    await conn.close()

asyncio.run(check())
