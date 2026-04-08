"""Run Tests 7, 8, 9, 10 via in-process FastAPI TestClient."""
import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.testclient import TestClient
from production.main import app

client = TestClient(app, raise_server_exceptions=False)
TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

tests = [
    ("Test 7: Multi-intent (CSV export + recurring tasks)", {
        "channel": "web_form",
        "content": "Can I export all my tasks as CSV? Also, how do I set up recurring tasks every Monday?",
        "customer_name": "Usman Farooq",
        "metadata": {"customer_email": "usman@startup.io"}
    }),
    ("Test 8: Follow-up (same session)", {
        "channel": "whatsapp",
        "content": "Still can't invite team members. I tried the steps you gave yesterday.",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": TEST_WA_ID}
    }),
    ("Test 9: Out-of-scope feature (mobile app - should NOT escalate)", {
        "channel": "whatsapp",
        "content": "Does FlowForge have a native mobile app yet?",
        "customer_name": "Ali Raza",
        "metadata": {"wa_id": "15550000002"}
    }),
    ("Test 10a: Low sentiment message 1 (same customer Sara)", {
        "channel": "whatsapp",
        "content": "this is really annoying, nothing works",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": TEST_WA_ID}
    }),
    ("Test 10b: Low sentiment message 2 (should trigger consecutive escalation)", {
        "channel": "whatsapp",
        "content": "I hate this, worst product ever",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": TEST_WA_ID}
    }),
]

for label, payload in tests:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Channel: {payload['channel']}")
    print(f"  Message: {payload['content'][:70]}")
    print(f"{'-'*60}")
    resp = client.post("/test/message", json=payload)
    print(f"  HTTP Status: {resp.status_code}")
    print(f"  Response JSON:")
    print(json.dumps(resp.json(), indent=4))
    print()
