"""Simulate the exact Twilio webhook payload to find the 500 error."""
import os, asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.testclient import TestClient
from production.main import app

client = TestClient(app, raise_server_exceptions=True)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")
TEST_PHONE = f"whatsapp:+{TEST_WA_ID}"
TEST_TO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
TEST_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")

# Exact data Twilio sends (simulated)
form_data = {
    "Body": "hi",
    "From": TEST_PHONE,
    "ProfileName": "TestUser",
    "WaId": TEST_WA_ID,
    "To": TEST_TO_NUMBER,
    "SmsSid": "SMtest123",
    "SmsStatus": "received",
    "NumMedia": "0",
    "AccountSid": TEST_ACCOUNT_SID,
    "ChannelMetadata": f'{{"type":"whatsapp","data":{{"context":{{"ProfileName":"TestUser","WaId":"{TEST_WA_ID}"}}}}}}',
}

# Skip Twilio signature validation for local testing
from production.ingestion import whatsapp as wa_mod
original_validate = wa_mod.WhatsAppIngestion.validate_webhook
async def mock_validate(self, request):
    return True  # always pass for testing
wa_mod.WhatsAppIngestion.validate_webhook = mock_validate

print("📨 Simulating Twilio webhook...")
print(f"   Body: {form_data['Body']}")
print(f"   From: {form_data['From']}")
print()

resp = client.post("/webhook/whatsapp", data=form_data)

print(f"HTTP Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
