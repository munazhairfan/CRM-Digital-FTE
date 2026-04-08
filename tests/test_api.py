"""Test the /test/message endpoint in-process (no server needed)."""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.testclient import TestClient
from production.main import app

client = TestClient(app)

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

payload = {
    "channel": "whatsapp",
    "content": "my board is stuck loading, nothing works!!",
    "customer_name": "Sara",
    "metadata": {"wa_id": TEST_WA_ID}
}

print("=" * 60)
print("POST /test/message")
print("=" * 60)
print(f"\n📨 Payload:")
print(f"   Channel: {payload['channel']}")
print(f"   Customer: {payload['customer_name']}")
print(f"   Message: {payload['content']}")
print()

response = client.post("/test/message", json=payload)

print(f"HTTP Status: {response.status_code}")
print(f"\n📝 Response JSON:")
for k, v in response.json().items():
    print(f"   {k}: {v}")
