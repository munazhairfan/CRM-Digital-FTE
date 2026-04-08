"""Test Gmail pipeline by processing the latest real inbox message."""
import asyncio, os, base64, re
from dotenv import load_dotenv
load_dotenv(override=True)

from production.ingestion.gmail import GmailIngestion
from production.services.agent_service import process_customer_message

async def test():
    gi = GmailIngestion()
    
    print("=" * 60)
    print("GMAIL REAL INBOX TEST")
    print("=" * 60)
    
    # Get the latest 3 messages from inbox
    print("\n📬 Fetching latest inbox messages...")
    results = gi.service.users().messages().list(
        userId="me",
        maxResults=3,
        labelIds=["INBOX"]
    ).execute()
    
    messages = results.get("messages", [])
    print(f"   Found {len(messages)} recent messages")
    
    for i, msg_summary in enumerate(messages, 1):
        msg_id = msg_summary["id"]
        print(f"\n{'─' * 60}")
        print(f"  Message {i}/{len(messages)}: {msg_id}")
        
        # Fetch full message
        msg = await gi.get_message(msg_id)
        if not msg:
            print("  ⏭️ Skipped (no body or empty)")
            continue
        
        print(f"  From: {msg['customer_name']} <{msg['customer_email']}>")
        print(f"  Subject: {msg['subject']}")
        print(f"  Content: {msg['content'][:120]}...")
        
        # Run through agent
        print(f"  🤖 Processing with AI agent...")
        raw_message = {
            "channel": "email",
            "content": msg["content"],
            "customer_name": msg["customer_name"],
            "metadata": msg["metadata"]
        }
        agent_result = await process_customer_message(raw_message)
        
        print(f"  Status: {agent_result['status']}")
        print(f"  Sentiment: {agent_result['sentiment']}")
        print(f"  Response length: {len(agent_result['response'])} chars")
        print(f"\n  📝 Response preview:")
        print(f"  {agent_result['response'][:200]}...")
        
        # Send reply
        print(f"  📤 Sending reply...")
        send_result = await gi.send_reply(
            to_email=msg["customer_email"],
            subject=msg["subject"],
            body=agent_result["response"],
            thread_id=msg.get("thread_id")
        )
        print(f"  ✅ Send result: {send_result['delivery_status']}")
    
    print(f"\n{'=' * 60}")
    print("✅ ALL MESSAGES PROCESSED")
    print(f"{'=' * 60}")

asyncio.run(test())
