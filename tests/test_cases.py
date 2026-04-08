"""
Test runner — runs multiple sample tickets from sample-tickets.json through the prototype pipeline.
"""
import os
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from production.prompts import process_ticket

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

test_cases = [
    # 1. WhatsApp - how-to (already tested, baseline)
    {
        "channel": "whatsapp",
        "content": "hi pls how do i invite my team??",
        "metadata": {"wa_id": TEST_WA_ID, "name": "Bilal"},
    },
    # 2. WhatsApp - escalation (strong negative language)
    {
        "channel": "whatsapp",
        "content": "this product is the worst ever!! nothing works 😡",
        "metadata": {"wa_id": "15550000002", "name": "Rabia Ahmed"},
    },
    # 3. Email - pricing (escalation)
    {
        "channel": "email",
        "content": "We are considering the Enterprise plan. Can someone call me to discuss custom pricing?",
        "metadata": {"subject": "Enterprise pricing discussion"},
        "customer_email": "sana@consulting.pk",
        "customer_name": "Sana Bukhari",
    },
    # 4. Web form - bug report (clarify + create ticket)
    {
        "channel": "web_form",
        "content": "The AI insights are not showing any predictions for my project. Is there a bug?",
        "metadata": {"category": "bug_report"},
        "customer_email": "bilal@freelance.dev",
        "customer_name": "Bilal Ahmed",
    },
    # 5. WhatsApp - appreciation (warm response needed)
    {
        "channel": "whatsapp",
        "content": "thanks! it worked after i refreshed 👍",
        "metadata": {"wa_id": "15550000003", "name": "Bilal Hassan"},
    },
    # 6. Email - follow-up (unresolved previous ticket)
    {
        "channel": "email",
        "content": "Follow-up: Still can't invite team members. I tried the steps you gave yesterday.",
        "metadata": {"subject": "Re: Team invitation issue"},
        "customer_email": "ayesha@tech.pk",
        "customer_name": "Ayesha Siddiqui",
    },
    # 7. Email - refund (escalation)
    {
        "channel": "email",
        "content": "Please refund my last month's Pro subscription. I no longer need it.",
        "metadata": {"subject": "Refund request"},
        "customer_email": "khalid@agency.com",
        "customer_name": "Khalid Mehmood",
    },
    # 8. WhatsApp - out-of-scope feature request (escalation)
    {
        "channel": "whatsapp",
        "content": "how much does enterprise cost? can u give me a quote?",
        "metadata": {"wa_id": "15550000004", "name": "Daniyal Ahmed"},
    },
    # 9. Email - multi-intent (export + recurring tasks)
    {
        "channel": "email",
        "content": "Can I export all my tasks as CSV? Also, is there a way to schedule recurring tasks every Monday?",
        "metadata": {"subject": "Export and recurring tasks"},
        "customer_email": "usman@startup.io",
        "customer_name": "Usman Farooq",
    },
    # 10. Web form - SSO (escalation: security/account access)
    {
        "channel": "web_form",
        "content": "How do I set up SSO for my team? We need it for security compliance.",
        "metadata": {"category": "technical"},
        "customer_email": "farah@startup.com",
        "customer_name": "Farah Naz",
    },
]


async def main():
    print(f"{'#'*60}")
    print(f"  Running {len(test_cases)} test cases through the pipeline")
    print(f"{'#'*60}\n")

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"  TEST CASE {i}/{len(test_cases)}")
        print(f"  Channel: {tc['channel']}")
        print(f"  Message: {tc['content']}")
        print(f"{'='*60}")
        ticket = await process_ticket(tc)
        print(f"  RESULT: {ticket.status}")
        if ticket.escalation_reason:
            print(f"  REASON: {ticket.escalation_reason}")
        print()

    print(f"\n{'#'*60}")
    print("  All test cases completed")
    print(f"{'#'*60}")


if __name__ == "__main__":
    asyncio.run(main())
