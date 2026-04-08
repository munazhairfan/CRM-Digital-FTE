import asyncio
from production.prompts import process_ticket

test_ticket = {
    "channel": "email",
    "content": "I need a refund for my Pro subscription. This is very frustrating.",
    "metadata": {"subject": "Refund request", "from": "khalid@startup.io", "name": "Khalid"},
}

ticket = asyncio.run(process_ticket(test_ticket))

assert ticket.status == "escalated", f"FAIL: Expected status='escalated', got '{ticket.status}'"
assert ticket.escalation_reason.lower().find("refund") != -1, f"FAIL: Expected refund in reason, got '{ticket.escalation_reason}'"
# Escalated tickets now get empathy-first holding messages instead of raw "ESCALATE:" text
assert "billing" in ticket.response.lower() or "refund" in ticket.response.lower() or "frustrat" in ticket.response.lower() or "understand" in ticket.response.lower(), \
    f"FAIL: Expected empathy holding message, got: {ticket.response}"

print("\n✅ ALL ASSERTIONS PASSED")
print(f"   Status: {ticket.status}")
print(f"   Reason: {ticket.escalation_reason}")
