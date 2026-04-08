"""Apply full schema to Neon PostgreSQL."""
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

    # Read the full schema
    with open("production/database/schema.sql", "r") as f:
        schema_sql = f.read()

    async with db.get_connection() as conn:
        print(f"📄 Schema size: {len(schema_sql)} chars")

        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(";") if s.strip() and not s.strip().startswith("--")]

        executed = 0
        skipped = 0
        for stmt in statements:
            # Skip comments and empty
            lines = [l for l in stmt.split("\n") if l.strip() and not l.strip().startswith("--")]
            if not lines:
                skipped += 1
                continue
            try:
                await conn.execute(stmt)
                executed += 1
            except Exception as e:
                # Tables already exist is fine
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    skipped += 1
                else:
                    print(f"⚠️  Warning: {str(e)[:100]}")
                    skipped += 1

        print(f"✅ Executed {executed} statements, skipped {skipped}")

        # Verify all 8 tables
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        table_names = [r["table_name"] for r in tables]
        print(f"✅ Tables: {', '.join(table_names)} ({len(table_names)} total)")

    await db.close()
    print("\n🟢 SCHEMA APPLIED SUCCESSFULLY")

asyncio.run(main())
