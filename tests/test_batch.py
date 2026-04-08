"""
FlowForge FTE — 52-Ticket Batch Test
Loads all sample tickets and runs them through the production pipeline.
Generates a performance report.
"""
import json
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

from production.clients.db_client import DatabaseClient
from production.services.agent_service import process_customer_message

# ---------------------------------------------------------------------------
# Load Tickets
# ---------------------------------------------------------------------------
with open("context/sample-tickets.json", "r", encoding="utf-8") as f:
    SAMPLE_TICKETS = json.load(f)

print(f"📦 Loaded {len(SAMPLE_TICKETS)} sample tickets.")

# ---------------------------------------------------------------------------
# Expected Ground Truth (based on discovery analysis)
# ---------------------------------------------------------------------------
EXPECTED_ESCALATION_KEYWORDS = {
    "refund": ["refund", "signed up by mistake"],
    "pricing": ["custom", "quote", "enterprise plan", "pricing", "sla", "demo of the enterprise"],
    "compliance": ["compliance", "data export for compliance"],
    "account_access": ["can't access", "session expired", "sso for security"],
    "strong_negative": ["worst ever", "worst product ever"],
    "human_request": ["speak to a real person", "talk to a manager"],
}

EXPECTED_RESOLVE_KEYWORDS = {
    "how_to": ["how do i", "how to", "steps", "option", "can i", "is there a way", "where"],
    "bug_report": ["stuck", "not working", "error", "bug", "crashing", "can't find", "not showing"],
    "feature_request": ["mobile app", "white-label", "time tracking", "suggest", "wish"],
    "appreciation": ["thanks", "thank you", "appreciate", "love the", "super fast"],
    "feedback": ["love the", "wish", "amazing but"],
    "integration_setup": ["connect slack", "connect figma", "integrate with", "microsoft teams"],
}

# ---------------------------------------------------------------------------
# Classification Helper (Rule-based grading since we can't rely on LLM for grading)
# ---------------------------------------------------------------------------
def guess_expected_status(content: str) -> str:
    """Simple heuristic to guess if a ticket should escalate or resolve."""
    content_lower = content.lower()

    # 1. Always Escalate: Refunds/Billing
    if any(kw in content_lower for kw in ["refund", "money back", "cancel subscription", "signed up by mistake"]):
        return "escalated"

    # 2. Always Escalate: Custom Quotes / Enterprise Negotiations
    if any(kw in content_lower for kw in ["give me a quote", "custom contract", "sla for our"]):
        return "escalated"

    # 3. Always Escalate: Extreme Negative Language ("worst ever")
    if any(kw in content_lower for kw in ["worst ever", "worst product ever"]):
        return "escalated"

    # 4. Always Escalate: Account Access / Security / SSO
    if any(kw in content_lower for kw in ["can't access my account", "session expired", "sso", "remove user access", "left the company"]):
        return "escalated"

    # 5. Always Escalate: Compliance / Legal
    if "compliance" in content_lower:
        return "escalated"

    # 6. Out-of-scope features are handled by agent, NOT escalated
    if any(kw in content_lower for kw in ["mobile app", "white-label", "time tracking"]):
        return "resolved"

    # 7. Integration Setup questions (covered in docs) → Do NOT escalate
    if any(kw in content_lower for kw in ["connect slack", "integrate with microsoft teams", "connect figma"]):
        return "resolved"

    # 8. General Pricing Inquiries (difference between plans) → Resolved
    if any(kw in content_lower for kw in ["difference between pro and enterprise", "pricing inquiry"]):
        return "resolved"

    return "resolved"


def guess_expected_sentiment_tone(content: str) -> str:
    """Guess if content is positive, negative, or neutral."""
    content_lower = content.lower()
    if any(kw in content_lower for kw in ["thanks", "thank you", "love", "appreciate", "great support"]):
        return "positive"
    if any(kw in content_lower for kw in ["worst ever", "frustrating", "annoying", "useless", "hate", "stuck", "crashing"]):
        return "negative"
    return "neutral"


# ---------------------------------------------------------------------------
# Run Batch
# ---------------------------------------------------------------------------
async def run_batch():
    # Initialize Database before starting
    await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
    
    results = []
    skipped = 0

    print(f"\n{'='*60}")
    print(f"  RUNNING BATCH TEST: {len(SAMPLE_TICKETS)} TICKETS")
    print(f"{'='*60}\n")

    for i, ticket in enumerate(SAMPLE_TICKETS, 1):
        channel = ticket["channel"]
        content = ticket.get("message", ticket.get("content", ""))
        meta = ticket.get("metadata", {})

        # Build raw message format compatible with pipeline
        if channel == "email":
            raw_msg = {
                "channel": "email",
                "content": content,
                "customer_name": ticket.get("customer_name", ""),
                "metadata": {"from": ticket.get("customer_email", ""), **meta},
            }
        elif channel == "whatsapp":
            raw_msg = {
                "channel": "whatsapp",
                "content": content,
                "customer_name": ticket.get("customer_name", ""),
                "metadata": {"wa_id": meta.get("wa_id", ""), **meta},
            }
        elif channel == "web_form":
            raw_msg = {
                "channel": "web_form",
                "content": content,
                "customer_name": ticket.get("customer_name", ""),
                "metadata": {"customer_email": ticket.get("customer_email", ""), **meta},
            }
        else:
            skipped += 1
            continue

        print(f"[{i}/{len(SAMPLE_TICKETS)}] {channel.upper()}: {content[:50]}...")
        try:
            result = await process_customer_message(raw_msg)
            
            # Grade result
            expected_status = guess_expected_status(content)
            status_correct = (result["status"] == expected_status)
            
            # Check response length for WhatsApp
            length_ok = True
            length_note = ""
            if channel == "whatsapp":
                resp_len = len(result["response"])
                if resp_len > 300:
                    length_ok = False
                    length_note = f" ⚠️ ({resp_len} chars)"

            results.append({
                "index": i,
                "channel": channel,
                "content": content,
                "expected_status": expected_status,
                "actual_status": result["status"],
                "status_correct": status_correct,
                "escalation_reason": result.get("escalation_reason", ""),
                "sentiment": result["sentiment"],
                "response_length": len(result["response"]),
                "length_ok": length_ok,
                "length_note": length_note,
                "response_preview": result["response"][:80] + "...",
            })

            mark = "✅" if status_correct else "❌"
            print(f"   {mark} Status: {result['status']} (Expected: {expected_status}) | Sentiment: {result['sentiment']}")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "index": i,
                "channel": channel,
                "content": content,
                "expected_status": guess_expected_status(content),
                "actual_status": "error",
                "status_correct": False,
                "error": str(e),
            })

    return results, skipped


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_report(results, skipped):
    print(f"\n{'='*60}")
    print(f"  BATCH TEST REPORT")
    print(f"{'='*60}")

    total = len(results)
    correct = sum(1 for r in results if r["status_correct"])
    errors = sum(1 for r in results if r.get("error"))
    
    # Channel breakdown
    channels = {}
    for r in results:
        ch = r["channel"]
        if ch not in channels:
            channels[ch] = {"total": 0, "correct": 0}
        channels[ch]["total"] += 1
        if r["status_correct"]:
            channels[ch]["correct"] += 1

    print(f"\n📊 SUMMARY")
    print(f"   Total Processed: {total}")
    print(f"   Skipped: {skipped}")
    print(f"   Correct Status: {correct}/{total} ({round(correct/total*100) if total else 0}%)")
    print(f"   Errors: {errors}")

    print(f"\n📡 CHANNEL BREAKDOWN")
    for ch, stats in sorted(channels.items()):
        acc = round(stats["correct"]/stats["total"]*100)
        print(f"   {ch}: {stats['correct']}/{stats['total']} ({acc}%)")

    # Failed Cases
    failures = [r for r in results if not r["status_correct"]]
    if failures:
        print(f"\n❌ FAILED CASES ({len(failures)})")
        for f in failures:
            err = f.get("error", f"Got '{f['actual_status']}', expected '{f['expected_status']}'")
            print(f"   - [{f['channel']}] {f['content'][:60]}...")
            print(f"     Reason: {err}")

    # Long WhatsApp Responses
    long_wa = [r for r in results if r["channel"] == "whatsapp" and not r.get("length_ok", True)]
    if long_wa:
        print(f"\n⚠️  LONG WHATSAPP RESPONSES ({len(long_wa)})")
        for r in long_wa:
            print(f"   - {r['content'][:50]}... → {r['response_length']} chars{r.get('length_note', '')}")

    print(f"\n{'='*60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    results, skipped = await run_batch()
    print_report(results, skipped)

if __name__ == "__main__":
    asyncio.run(main())
