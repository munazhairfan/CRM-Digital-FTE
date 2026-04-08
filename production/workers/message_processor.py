# production/workers/message_processor.py
import asyncio
from production.services.agent_service import process_customer_message
from production.ingestion.whatsapp import WhatsAppIngestion
from production.ingestion.web_form import WebFormIngestion, SupportFormSubmission

whatsapp_ingestion = WhatsAppIngestion()
web_form_ingestion = WebFormIngestion()


async def process_incoming_message(raw_message: dict):
    """
    Main production message processor.
    This is the heart of your 24/7 AI employee.
    """
    print(f"\n📥 Received message from {raw_message['channel']}")

    # Step 1: Run the full agent pipeline (classifier + tools + response)
    result = await process_customer_message(raw_message)

    # Step 2: Log final result
    print(f"✅ Processed → Status: {result['status']}")
    print(f"📝 Response: {result['response'][:300]}..." if len(result['response']) > 300 else f"📝 Response: {result['response']}")

    return result


# ----------------------------------------------------------------------
# Test helpers (you can call these from main.py or tests)
# ----------------------------------------------------------------------
async def test_whatsapp_message():
    """Quick test with a WhatsApp-style message"""
    raw = {
        "channel": "whatsapp",
        "content": "hey, how do i invite team members to a board?",
        "customer_name": "Sara Ahmed",
        "metadata": {"wa_id": "15550000000"}
    }
    return await process_incoming_message(raw)


async def test_web_form():
    """Quick test with Web Form submission"""
    form = SupportFormSubmission(
        name="Ahmed Khan",
        email="ahmed.khan@techcorp.com",
        subject="Cannot export tasks as CSV",
        category="technical",
        message="I tried the steps but still getting an error.",
        priority="high"
    )
    processed = await web_form_ingestion.process_submission(form)
    return await process_incoming_message({
        "channel": "web_form",
        "content": processed["content"],
        "customer_name": form.name,
        "metadata": processed["metadata"]
    })