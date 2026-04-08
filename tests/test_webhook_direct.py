import asyncio, os, sys
sys.stdout.reconfigure(line_buffering=True)
from dotenv import load_dotenv
load_dotenv(override=True)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")
TEST_PHONE = f"whatsapp:+{TEST_WA_ID}"
TEST_TO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

async def test():
    print("1. Importing webhook handler...", flush=True)
    from production.ingestion.whatsapp import WhatsAppIngestion
    print("2. Processing webhook...", flush=True)
    wi = WhatsAppIngestion()
    result = await wi.process_webhook({
        'Body': 'hi test',
        'From': TEST_PHONE,
        'ProfileName': 'TestUser',
        'WaId': TEST_WA_ID,
        'To': TEST_TO_NUMBER,
        'NumMedia': '0',
    })
    print(f"3. Result: {result}", flush=True)

print("Starting webhook test...", flush=True)
asyncio.run(test())
print("Done.", flush=True)
