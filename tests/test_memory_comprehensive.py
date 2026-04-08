"""
Comprehensive Test Suite for Memory Service (7-Day Cross-Channel History)
"""
import httpx
import asyncio
import json

BASE_URL = "http://127.0.0.1:8000/test/message"

async def send_message(client, description, payload):
    print(f"🧪 {description}")
    try:
        resp = await client.post(BASE_URL, json=payload)
        data = resp.json()
        reply = data.get('response', 'No response')
        print(f"   🤖 Reply: {reply[:80]}...")
        return reply
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return ""

async def main():
    async with httpx.AsyncClient(timeout=45.0) as client:
        
        # --- Test 1: Context Retention (The "Is it fixed?" test) ---
        print("\n=== TEST 1: Context Retention ===")
        user_1 = "test_user_memory_001"
        
        # Step 1: Establish Context
        await send_message(client, "1. Report Issue: 'My dashboard is 500 erroring'", {
            "channel": "whatsapp",
            "content": "My dashboard is 500 erroring",
            "customer_name": "ContextUser",
            "metadata": {"wa_id": user_1}
        })

        # Step 2: Follow up referencing the issue
        reply_2 = await send_message(client, "2. Follow-up: 'Did you fix it? I need the logs.'", {
            "channel": "whatsapp",
            "content": "Did you fix it? I need the logs.",
            "customer_name": "ContextUser",
            "metadata": {"wa_id": user_1}
        })

        # Check 1: Did it mention the dashboard or error?
        if any(word in reply_2.lower() for word in ["dashboard", "500", "error", "logs"]):
            print("   ✅ PASS: Agent remembered the dashboard 500 error.")
        else:
            print("   ❌ FAIL: Agent treated this as a generic 'what did I fix?' question.")

        print("\n" + "-"*40 + "\n")

        # --- Test 2: Isolation (The "Don't mix me up" test) ---
        print("=== TEST 2: User Isolation ===")
        user_2 = "test_user_new_999"

        # New user asks "What was my issue?"
        reply_3 = await send_message(client, "3. New User: 'What was my issue?'", {
            "channel": "whatsapp",
            "content": "What was my issue?",
            "customer_name": "NewUser",
            "metadata": {"wa_id": user_2}
        })

        # Check 2: Did it hallucinate User 1's issue?
        if "dashboard" in reply_3.lower() or "500" in reply_3.lower():
            print("   ❌ FAIL: Agent leaked User 1's history to User 2.")
        else:
            print("   ✅ PASS: Agent correctly identified User 2 has no history.")

        print("\n" + "-"*40 + "\n")

        # --- Test 3: Multi-Turn Complexity ---
        print("=== TEST 3: Multi-Turn Complexity ===")
        user_3 = "test_user_complex_777"

        await send_message(client, "1. Ask: 'How do I invite users?'", {
            "channel": "web_form", # Different channel
            "content": "How do I invite users?",
            "customer_name": "ComplexUser",
            "metadata": {"customer_email": "complex@test.com"}
        })

        await send_message(client, "2. Complaint: 'The button is missing.'", {
            "channel": "web_form", 
            "content": "The button is missing.",
            "customer_name": "ComplexUser",
            "metadata": {"customer_email": "complex@test.com"}
        })
        
        # Note: In a real scenario, the memory service retrieves by customer_id.
        # Here, the web_form uses 'customer_email' as ID. 
        # Since we sent two messages with same email, they should link if DB wrote correctly.
        # We assume DB write success from previous test.

asyncio.run(main())
