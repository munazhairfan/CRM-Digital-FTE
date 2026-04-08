import os
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from production.prompts import process_ticket, session_store

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

# Test: appreciation message that says "thanks" + implies no follow-up needed
test_ticket = {
    "channel": "whatsapp",
    "content": "thanks for the help earlier. everything is good now ❤️",
    "metadata": {"wa_id": TEST_WA_ID, "name": "Saima"},
}

ticket = asyncio.run(process_ticket(test_ticket))

response_lower = ticket.response.lower()

assert ticket.status == "resolved", f"FAIL: Expected resolved, got '{ticket.status}'"
assert "❤️" in response_lower or "great" in response_lower or "glad" in response_lower or "happy" in response_lower or "wonderful" in response_lower, \
    f"FAIL: Response doesn't warmly acknowledge appreciation: {ticket.response}"
assert len(ticket.response) < 300, f"FAIL: WhatsApp response exceeds 300 chars: {len(ticket.response)}"
assert ticket.intents == ["appreciation"], f"FAIL: Expected ['appreciation'], got {ticket.intents}"
assert ticket.sentiment >= 0.7, f"FAIL: Expected sentiment >= 0.7 for appreciation, got {ticket.sentiment}"

print(f"\n✅ ALL ASSERTIONS PASSED")
print(f"   Intent: {ticket.intents}")
print(f"   Sentiment: {ticket.sentiment}")
print(f"   Status: {ticket.status}")
print(f"   Response length: {len(ticket.response)} chars")
