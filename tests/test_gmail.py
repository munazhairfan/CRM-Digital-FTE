"""Test Gmail webhook with simulated Pub/Sub message."""
import asyncio, os, base64, json
from dotenv import load_dotenv
load_dotenv(override=True)

from production.ingestion.gmail import GmailIngestion
from production.services.agent_service import process_customer_message

async def test():
    gi = GmailIngestion()
    
    # Simulate a realistic email that would come through Gmail
    email_content = """Hi FlowForge team,

I'm having trouble setting up a new board for my team. When I click the "+" button in the sidebar, nothing happens. I've tried refreshing the page and using a different browser (Chrome). 

Could you help me troubleshoot this?

Best,
Ahmed
"""
    
    # Build a message as if it came from Gmail API
    msg = {
        "channel": "email",
        "channel_message_id": "18a1b2c3d4e5f6",
        "customer_email": "ahmed.khan@techcorp.com",
        "customer_name": "Ahmed Khan",
        "subject": "Cannot create new board",
        "content": email_content,
        "thread_id": "thread-abc123",
        "metadata": {
            "from": "ahmed.khan@techcorp.com",
            "name": "Ahmed Khan",
            "headers": {"From": "Ahmed Khan <ahmed.khan@techcorp.com>", "Subject": "Cannot create new board"},
            "labels": ["INBOX", "UNREAD"]
        }
    }
    
    # Run through agent pipeline
    print("=" * 60)
    print("GMAIL TEST: Email → Agent Pipeline")
    print("=" * 60)
    print(f"From: {msg['customer_name']} <{msg['customer_email']}>")
    print(f"Subject: {msg['subject']}")
    print(f"Content: {msg['content'][:100]}...")
    print()
    
    raw_message = {
        "channel": "email",
        "content": msg["content"],
        "customer_name": msg["customer_name"],
        "metadata": msg["metadata"]
    }
    
    agent_result = await process_customer_message(raw_message)
    
    print(f"Agent Status: {agent_result['status']}")
    print(f"Agent Sentiment: {agent_result['sentiment']}")
    print(f"Escalation: {agent_result.get('escalation_reason', 'N/A')}")
    print(f"\n{'─' * 60}")
    print("AGENT RESPONSE:")
    print(f"{'─' * 60}")
    print(agent_result['response'])
    print(f"{'─' * 60}")
    
    # Simulate sending reply
    send_result = await gi.send_reply(
        to_email=msg["customer_email"],
        subject=msg["subject"],
        body=agent_result["response"],
        thread_id=msg.get("thread_id")
    )
    print(f"\nSend result: {send_result}")
    print("\n✅ GMAIL PIPELINE TEST COMPLETE")

asyncio.run(test())
