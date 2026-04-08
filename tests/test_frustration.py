import os
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from production.prompts import process_ticket

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

test_ticket = {
    "channel": "whatsapp",
    "content": "worst ever!! nothing works my whole team cant login!!",
    "metadata": {"wa_id": TEST_WA_ID, "name": "Rabia"},
}

ticket = asyncio.run(process_ticket(test_ticket))

response = ticket.response.lower()

assert ticket.sentiment < 0.3, f"FAIL: Expected sentiment < 0.3, got {ticket.sentiment}"
assert ticket.status == "escalated", f"FAIL: Expected 'escalated', got '{ticket.status}'"
assert "frustrat" in response or "sorry" in response or "disruptive" in response or "hear" in response or "understand" in response, \
    f"FAIL: Response doesn't show empathy first: {ticket.response}"
assert len(ticket.response) < 300, f"FAIL: WhatsApp holding message too long ({len(ticket.response)} chars)"
assert "rabia" in response, f"FAIL: Response doesn't personalize with customer name: {ticket.response}"

print(f"\n✅ ALL ASSERTIONS PASSED")
print(f"   Sentiment: {ticket.sentiment} (< 0.3)")
print(f"   Status: {ticket.status}")
print(f"   Reason: {ticket.escalation_reason}")
print(f"   Response length: {len(ticket.response)} chars")
