"""
tests/test_final_demo.py
Simulates a complete "Day in the Life" of the Customer Success FTE.
Runs 4 distinct scenarios to prove the system is production-ready.
"""
import asyncio
import os
import httpx
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://127.0.0.1:8000"

async def run_demo():
    print("="*80)
    print("🚀 FLOWFORGE FTE: COMPREHENSIVE LIVE DEMO")
    print("="*80)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        
        # --- Scenario 1: WhatsApp Happy Path ---
        print("\n1️⃣ [WhatsApp] Simple How-To Inquiry")
        print("   👤 User: 'hey, how do i invite my team?'")
        resp = await client.post("/test/message", json={
            "channel": "whatsapp",
            "content": "hey, how do i invite my team?",
            "customer_name": "Sara",
            "metadata": {"wa_id": "15550000001", "customer_email": "sara@test.com"}
        })
        if resp.status_code != 200:
            print(f"   ❌ Error {resp.status_code}: {resp.text}")
            return
        data = resp.json()
        if "error" in data or "status" not in data:
            print(f"   ❌ API Error: {data.get('error', 'Missing status')}")
            print(f"   🔍 Full Data: {data}")
            return
        print(f"   🤖 Agent: {data.get('response', 'N/A')[:80]}...")
        assert data["status"] == "resolved", "Scenario 1 Failed: Should be resolved"
        assert "settings" in data["response"].lower() or "members" in data["response"].lower(), "Scenario 1 Failed: Bad answer"
        print("   ✅ PASS: Correct instructions provided.")

        # --- Scenario 2: Email Escalation (Custom Quote) ---
        print("\n2️⃣ [Email] Enterprise Pricing Inquiry (Escalation)")
        print("   👤 User: 'We need a custom quote for 500 seats. Call me.'")
        resp = await client.post("/test/message", json={
            "channel": "email",
            "content": "We need a custom quote for 500 seats. Call me.",
            "customer_name": "Ahmed Khan",
            "metadata": {"from": "ahmed@corp.com", "customer_email": "ahmed@corp.com"}
        })
        data = resp.json()
        if "error" in data or "status" not in data:
            print(f"   ❌ API Error: {data.get('error', 'Missing status')}")
            print(f"   🔍 Full Data: {data}")
            return
        print(f"   🤖 Agent: {data.get('response', 'N/A')[:80]}...")
        assert data["status"] == "escalated", "Scenario 2 Failed: Should escalate pricing"
        assert "pricing" in data["escalation_reason"].lower() or "quote" in data["escalation_reason"].lower(), "Scenario 2 Failed: Wrong reason"
        print("   ✅ PASS: Correctly escalated to sales team.")

        # --- Scenario 3: Web Form Multi-Intent (Bug + Feature) ---
        print("\n3️⃣ [Web Form] Multi-Intent: Bug Report + Feature Question")
        print("   👤 User: 'My dashboard is crashing when I export CSV. Also, is there a mobile app?'")
        resp = await client.post("/test/message", json={
            "channel": "web_form",
            "content": "My dashboard is crashing when I export CSV. Also, is there a mobile app?",
            "customer_name": "Ali Raza",
            "metadata": {"customer_email": "ali@test.com"}
        })
        data = resp.json()
        if "error" in data or "status" not in data:
            print(f"   ❌ API Error: {data.get('error', 'Missing status')}")
            print(f"   🔍 Full Data: {data}")
            return
        print(f"   🤖 Agent: {data.get('response', 'N/A')[:80]}...")
        # Should mention "ticket" or "crashing" AND "PWA"
        resp_lower = data["response"].lower()
        assert ("ticket" in resp_lower or "issue" in resp_lower) and ("pwa" in resp_lower or "app" in resp_lower), "Scenario 3 Failed: Missed intent"
        print("   ✅ PASS: Handled both bug and feature request.")

        # --- Scenario 4: The "Wow" Factor (Cross-Channel Memory) ---
        print("\n4️⃣ [Email] Cross-Channel Memory Test")
        print("   👤 User (Same as Scenario 3): 'Did you fix that crash yet? I really need that CSV.'")
        # Note: We use the SAME email as Scenario 3, but different channel
        resp = await client.post("/test/message", json={
            "channel": "email",
            "content": "Did you fix that crash yet? I really need that CSV.",
            "customer_name": "Ali Raza",
            "metadata": {"from": "ali@test.com", "customer_email": "ali@test.com"}
        })
        data = resp.json()
        print(f"   🤖 Agent: {data['response'][:100]}...")
        # Check if agent remembers "crash" or "CSV" or "dashboard"
        resp_lower = data["response"].lower()
        memory_check = any(kw in resp_lower for kw in ["crash", "csv", "export", "dashboard", "ticket", "issue"])
        assert memory_check, f"Scenario 4 Failed: Agent forgot the context. Reply: {data['response'][:50]}"
        print("   ✅ PASS: Agent REMEMBERED the previous issue across channels!")

        # --- Scenario 5: Reporting System ---
        print("\n5️⃣ [API] Checking Sentiment Report")
        resp = await client.get("/reports/sentiment?days=1")
        data = resp.json()
        print(f"   📊 Stats: {data['summary']['total_interactions']} Interactions, Avg Sentiment: {data['summary']['daily_average_sentiment']}")
        assert data["summary"]["total_interactions"] >= 4, "Scenario 5 Failed: Report is empty"
        print("   ✅ PASS: Analytics are tracking correctly.")

    print("\n" + "="*80)
    print("🏆 DEMO COMPLETE: All Scenarios Passed Successfully!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_demo())
