import asyncio, os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.reporting_service import ReportingService

async def test():
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
    r = ReportingService()
    try:
        res = await r.get_sentiment_report(days=1)
        print("✅ Report:", res)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
