"""Verify Neon PostgreSQL connection and schema."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient

async def main():
    dsn = os.environ["DATABASE_URL"]
    db = DatabaseClient()

    print("🔗 Connecting to Neon PostgreSQL...")
    await db.initialize(dsn)

    async with db.get_connection() as conn:
        # 1. Check connection
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Connected — {version[:50]}...")

        # 2. Check tables exist
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        table_names = [r["table_name"] for r in tables]
        print(f"✅ Found {len(table_names)} tables: {', '.join(table_names)}")

        # 3. Verify expected tables
        expected = [
            "customers", "customer_identifiers", "conversations",
            "messages", "tickets", "knowledge_base",
            "escalated_tickets", "agent_metrics"
        ]
        missing = [t for t in expected if t not in table_names]
        if missing:
            print(f"❌ Missing tables: {missing}")
        else:
            print(f"✅ All 8 expected tables present")

        # 4. Check row counts
        for table in expected:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"   {table}: {count} rows")

    await db.close()
    print("\n🟢 DATABASE VERIFICATION COMPLETE")

asyncio.run(main())
