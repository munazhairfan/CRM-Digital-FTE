"""Test Gmail webhook end-to-end with real Gmail API."""
import asyncio, os, base64, json
from dotenv import load_dotenv
load_dotenv(override=True)

from production.main import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)

print("=" * 60)
print("GMAIL WEBHOOK TEST — End-to-End")
print("=" * 60)

# Simulate a real Pub/Sub push notification from Gmail
# This mimics what Google Cloud Pub/Sub sends to your webhook
pubsub_payload = {
    "message": {
        "data": base64.b64encode(b'{"emailAddress": "munazhairfan@gmail.com", "historyId": "1"}').decode(),
        "messageId": "12345",
        "publishTime": "2026-04-08T00:00:00Z"
    }
}

print("📨 Sending Pub/Sub notification...")
resp = client.post("/webhook/gmail", json=pubsub_payload)

print(f"HTTP Status: {resp.status_code}")
print(f"Response: {resp.json()}")

if resp.status_code == 200:
    data = resp.json()
    if data.get("messages", 0) > 0:
        print(f"\n✅ Processed {data['messages']} message(s)")
    else:
        print(f"\n⚠️ No new messages found (normal if inbox is already up-to-date)")
else:
    print(f"\n❌ Webhook failed")
