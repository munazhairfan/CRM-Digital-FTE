"""Run Tests 1, 2, 4 via in-process FastAPI TestClient."""
import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.testclient import TestClient
from production.main import app

client = TestClient(app)

tests = {
    "Test 1: Bug report with frustration (should NOT escalate)": {
        "channel": "whatsapp",
        "content": "my board is stuck loading again, this is so frustrating!!",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": "923001234567"}
    },
    "Test 2: Pricing inquiry (should escalate)": {
        "channel": "email",
        "content": "Can you give me a custom Enterprise quote? We need 50 seats.",
        "customer_name": "Ahmed Khan",
        "metadata": {"customer_email": "ahmed.khan@techcorp.com"}
    },
    "Test 4: Appreciation / Thanks (should be warm & short)": {
        "channel": "whatsapp",
        "content": "thanks for the help earlier. everything is good now ❤️",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": "923001234567"}
    }
}

for label, payload in tests.items():
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Input: {payload['content'][:80]}")
    print(f"  Channel: {payload['channel']}")
    print(f"  Customer: {payload['customer_name']}")
    print(f"{'-'*60}")
    resp = client.post("/test/message", json=payload)
    print(f"  Status: {resp.status_code}")
    print(f"  Response JSON:")
    print(json.dumps(resp.json(), indent=4))
