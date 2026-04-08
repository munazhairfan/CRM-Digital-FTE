import asyncio
import os
import asyncpg
from dotenv import load_dotenv
load_dotenv(override=True)

async def check():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    # Check customers
    customers = await conn.fetch("SELECT name, email, phone FROM customers ORDER BY created_at DESC LIMIT 5")
    for c in customers:
        print(f"  - Name: {c['name']}, Email: {c['email']}, Phone: {c['phone']}")
        
    await conn.close()

asyncio.run(check())
