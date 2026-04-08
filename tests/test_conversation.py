import os
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from production.prompts import run_conversation, session_store

TEST_WA_ID = os.getenv("TEST_WA_ID", "15550000000")

conversation = [
    {
        "channel": "whatsapp",
        "content": "hi how do i set up automations?",
        "metadata": {"wa_id": TEST_WA_ID, "name": "Ayesha"}
    },
    {
        "channel": "whatsapp",
        "content": "still not working, tried what you said",
        "metadata": {"wa_id": TEST_WA_ID, "name": "Ayesha"}
    },
    {
        "channel": "whatsapp",
        "content": "this is useless nothing works!!",
        "metadata": {"wa_id": TEST_WA_ID, "name": "Ayesha"}
    }
]

results = asyncio.run(run_conversation(conversation))

print("=" * 60)
print("  VERIFICATION")
print("=" * 60)

# Check 1: Message 2 response acknowledges she already tried the steps
turn2_response = results[1].response.lower()
acknowledges_prior = any(phrase in turn2_response for phrase in [
    "already tried", "tried", "still not", "again",
    "despite trying", "even after", "you mentioned",
    "i understand", "hear you", "frustrating"
])
print(f"  [1] Turn 2 acknowledges prior attempt: {'✅' if acknowledges_prior else '❌'}")
if not acknowledges_prior:
    print(f"      Response: {results[1].response[:150]}...")

# Check 2: Message 3 triggers consecutive low sentiment escalation
turn3 = results[2]
consecutive_triggered = "consecutive" in turn3.escalation_reason.lower() or \
                        "sentiment" in turn3.escalation_reason.lower()
print(f"  [2] Turn 3 consecutive_low_sentiment escalation: {'✅' if consecutive_triggered else '❌'}")
if not consecutive_triggered:
    print(f"      Reason: {turn3.escalation_reason}")

# Check 3: Sentiment history — at least 2 scores at or below 0.3
session = session_store.get(TEST_WA_ID)
low_sentiment_count = sum(1 for s in session.sentiment_history if s <= 0.3)
print(f"  [3] At least 2 sentiment scores at or below 0.3: {'✅' if low_sentiment_count >= 2 else '❌'}")
print(f"      Full history: {[round(s, 2) for s in session.sentiment_history]}")

# Overall
all_pass = acknowledges_prior and consecutive_triggered and low_sentiment_count >= 2
print(f"\n  {'✅ ALL VERIFICATIONS PASSED' if all_pass else '❌ SOME VERIFICATIONS FAILED'}")
