import asyncio, os, sys
sys.stdout.reconfigure(line_buffering=True)
from dotenv import load_dotenv
load_dotenv(override=True)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

async def test():
    print("1. Importing agent service...", flush=True)
    from production.services.agent_service import process_customer_message
    print("2. Calling agent...", flush=True)
    result = await process_customer_message({
        'channel': 'whatsapp',
        'content': 'hi test',
        'customer_name': 'TestUser',
        'metadata': {'wa_id': TEST_WA_ID},
    })
    print(f"3. Result: {result}", flush=True)

print("Starting...", flush=True)
asyncio.run(test())
print("Done.", flush=True)
