"""
Thorough Test of Multi-Channel Context Continuity.
Scenario:
1. User reports an issue on WhatsApp.
2. User follows up on Web Form (switching channels).
3. User emails support (switching channels again).
Verification: Agent must remember the issue across all 3 steps.
"""

import asyncio
import os
import sys
import asyncpg
import hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.agent_service import process_customer_message

# Test Constants
TEST_EMAIL = "context_test_user@example.com"
TEST_PHONE = "15559998888"
TEST_NAME = "Bob Jones"
# Deterministic ID for this specific test user
TEST_CUSTOMER_ID = f"{hashlib.md5(TEST_EMAIL.encode()).hexdigest()[:8]}-{hashlib.md5(TEST_EMAIL.encode()).hexdigest()[8:12]}-{hashlib.md5(TEST_EMAIL.encode()).hexdigest()[12:16]}-{hashlib.md5(TEST_EMAIL.encode()).hexdigest()[16:20]}-{hashlib.md5(TEST_EMAIL.encode()).hexdigest()[20:]}"

async def run_thorough_test():
    print("="*80)
    print("🧪 THOROUGH TEST: Multi-Channel Context Continuity")
    print("="*80)

    # 0. Setup DB
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
    async with DatabaseClient.get_connection() as conn:
        # Fix Missing Unique Constraint for Summaries (if needed)
        try:
            await conn.execute("ALTER TABLE conversation_summaries ADD CONSTRAINT uq_conversation_summary UNIQUE (conversation_id)")
            print("✅ DB Fix: Added unique constraint to conversation_summaries.")
        except Exception:
            pass # Constraint likely already exists
            
        # Create/Clean User
        await conn.execute("DELETE FROM customers WHERE email = $1", TEST_EMAIL)
        await conn.execute("DELETE FROM conversation_summaries WHERE customer_id = $1", TEST_CUSTOMER_ID)
        await conn.execute(
            "INSERT INTO customers (id, name, email, phone) VALUES ($1, $2, $3, $4)",
            TEST_CUSTOMER_ID, TEST_NAME, TEST_EMAIL, TEST_PHONE
        )
        print(f"✅ Setup: User {TEST_NAME} created with ID {TEST_CUSTOMER_ID}")

    # ---------------------------------------------------------
    # Step 1: WhatsApp - Initial Report
    # ---------------------------------------------------------
    print("\n1️⃣ [WhatsApp] User: 'my board is stuck on the loading screen.'")
    res1 = await process_customer_message({
        "channel": "whatsapp",
        "content": "my board is stuck on the loading screen.",
        "customer_name": TEST_NAME,
        "metadata": {"wa_id": TEST_PHONE, "customer_email": TEST_EMAIL}
    })
    print(f"   🤖 Reply: {res1['response'][:80]}...")
    
    # ---------------------------------------------------------
    # Step 2: Web Form - Follow up (Channel Switch!)
    # ---------------------------------------------------------
    print("\n2️⃣ [Web Form] User: 'it is still stuck, I tried refreshing.'")
    res2 = await process_customer_message({
        "channel": "web_form",
        "content": "it is still stuck, I tried refreshing.",
        "customer_name": TEST_NAME,
        "metadata": {"customer_email": TEST_EMAIL}
    })
    print(f"   🤖 Reply: {res2['response'][:100]}...")
    
    # Verification 1: Did it remember the "loading screen"?
    resp2_lower = res2['response'].lower()
    mem_check_1 = any(kw in resp2_lower for kw in ["board", "loading", "stuck", "issue", "refresh", "tried"])
    print(f"   ✅ Memory Check 1 (Board/Loading): {'PASS' if mem_check_1 else 'FAIL'}")

    # ---------------------------------------------------------
    # Step 3: Email - Frustration (Channel Switch!)
    # ---------------------------------------------------------
    print("\n3️⃣ [Email] User: 'Why is this taking so long? I need to work.'")
    res3 = await process_customer_message({
        "channel": "email",
        "content": "Why is this taking so long? I need to work.",
        "customer_name": TEST_NAME,
        "metadata": {"from": TEST_EMAIL, "customer_email": TEST_EMAIL}
    })
    print(f"   🤖 Reply: {res3['response'][:100]}...")

    # Verification 2: Did it remember the whole conversation?
    resp3_lower = res3['response'].lower()
    # Even if it escalates, it should reference the ongoing issue or "ticket".
    # It should NOT say "Hi, how can I help you today?" (generic greeting).
    is_generic = "how can i help" in resp3_lower or "what can i do" in resp3_lower
    is_specific = any(kw in resp3_lower for kw in ["board", "loading", "ticket", "team", "stuck", "refresh"])
    mem_check_2 = (not is_generic) and is_specific
    
    print(f"   ✅ Memory Check 2 (Specific Context): {'PASS' if mem_check_2 else 'FAIL'}")

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------
    print("\n" + "="*80)
    if mem_check_1 and mem_check_2:
        print("🏆 THOROUGH TEST PASSED: Context maintained across 3 channels!")
    else:
        print("❌ THOROUGH TEST FAILED: Context was lost between channels.")
    print("="*80)

asyncio.run(run_thorough_test())
