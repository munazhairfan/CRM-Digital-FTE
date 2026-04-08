import asyncio
from production.prompts import process_ticket

test_ticket = {
    "channel": "email",
    "content": "Hi, I've been trying to export our project data as CSV but can't find the option. Also, does FlowForge support recurring tasks?",
    "metadata": {"subject": "CSV export + recurring tasks", "from": "usman@techcorp.com", "name": "Usman"},
}

asyncio.run(process_ticket(test_ticket))
