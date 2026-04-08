"""Verify that data is actually being written to PostgreSQL."""
import asyncio, os, json, time
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.agent_service import process_customer_message

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

async def test():
    # Initialize DB
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))

    # Process a message
    print("📤 Sending test message...")
    result = await process_customer_message({
        "channel": "whatsapp",
        "content": "hi test",
        "customer_name": "PersistenceTester",
        "metadata": {"wa_id": TEST_WA_ID}
    })
    
    print(f"✅ Agent responded: {result['status']}")
    print(f"   Ticket ID: {result['ticket_id']}")

    # Check DB directly
    async with DatabaseClient.get_connection() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM customers WHERE name = $1", "PersistenceTester")
        print(f"\n💾 DB Check: Found {count} customer(s) named 'PersistenceTester'")
        
        if count > 0:
            c_id = await conn.fetchval("SELECT id FROM customers WHERE name = $1", "PersistenceTester")
            conv_count = await conn.fetchval("SELECT COUNT(*) FROM conversations WHERE customer_id = $1", c_id)
            msg_count = await conn.fetchval("SELECT COUNT(*) FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE customer_id = $1)", c_id)
            ticket_count = await conn.fetchval("SELECT COUNT(*) FROM tickets WHERE customer_id = $1", c_id)
            
            print(f"   Conversations: {conv_count}")
            print(f"   Messages: {msg_count}")
            print(f"   Tickets: {ticket_count}")
            print("\n✅ PERSISTENCE VERIFIED!")
        else:
            print("\n❌ DATA NOT FOUND IN DB")

asyncio.run(test())
