import asyncio
from production.prompts import process_ticket

test_ticket = {
    "channel": "web_form",
    "content": "Does FlowForge have a mobile app? I need to manage tasks on my phone.",
    "metadata": {"category": "feature_request", "name": "Fahad", "email": "fahad@freelance.dev"},
}

ticket = asyncio.run(process_ticket(test_ticket))

response = ticket.response.lower()

assert ticket.status == "resolved", f"FAIL: Expected 'resolved', got '{ticket.status}'"
assert "mobile app" in response or "mobile" in response, f"FAIL: Response doesn't mention mobile: {ticket.response}"
assert "pwa" in response, f"FAIL: Response doesn't mention PWA as alternative: {ticket.response}"
assert not any(phrase in response for phrase in ["we have a mobile app", "download our app", "available on the app store", "available on google play"]), \
    f"FAIL: Response falsely claims mobile app exists: {ticket.response}"

print("\n✅ ALL ASSERTIONS PASSED")
print(f"   Status: {ticket.status}")
print(f"   Mentions PWA as alternative: True")
print(f"   Does NOT promise mobile app: True")
