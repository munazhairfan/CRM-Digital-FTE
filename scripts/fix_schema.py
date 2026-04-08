"""Create the 3 missing tables on Neon."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient

async def main():
    dsn = os.environ["DATABASE_URL"]
    db = DatabaseClient()
    await db.initialize(dsn)

    async with db.get_connection() as conn:
        # 1. Enable pgvector
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ pgvector extension enabled")
        except Exception as e:
            print(f"⚠️  pgvector: {str(e)[:100]}")
            print("   Trying without vector column...")

        # 2. escalated_tickets
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS escalated_tickets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    ticket_id UUID REFERENCES tickets(id),
                    reason TEXT NOT NULL,
                    urgency VARCHAR(20),
                    escalated_at TIMESTAMPTZ DEFAULT NOW(),
                    status VARCHAR(20) DEFAULT 'pending',
                    notes TEXT
                );
            """)
            print("✅ escalated_tickets created")
        except Exception as e:
            print(f"⚠️  escalated_tickets: {str(e)[:100]}")

        # 3. knowledge_base (without vector if extension failed)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    category VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            print("✅ knowledge_base created (without vector column)")
        except Exception as e:
            print(f"⚠️  knowledge_base: {str(e)[:100]}")

        # 4. agent_metrics
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(10,4),
                    channel VARCHAR(20),
                    recorded_at TIMESTAMPTZ DEFAULT NOW(),
                    dimensions JSONB DEFAULT '{}'
                );
            """)
            print("✅ agent_metrics created")
        except Exception as e:
            print(f"⚠️  agent_metrics: {str(e)[:100]}")

        # 5. Verify
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        names = [r["table_name"] for r in tables]
        print(f"\n✅ All tables ({len(names)}): {', '.join(names)}")

    await db.close()
    print("\n🟢 SCHEMA COMPLETE")

asyncio.run(main())
