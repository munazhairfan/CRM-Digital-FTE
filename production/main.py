# production/main.py
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from twilio.rest import Client
import os
from production.ingestion.gmail import GmailIngestion
from production.clients.db_client import DatabaseClient
from production.clients.kafka_client import kafka_producer
from production.ingestion.web_form import WebFormIngestion, SupportFormSubmission
from production.ingestion.whatsapp import WhatsAppIngestion
from production.services.agent_service import process_customer_message
from production.services.reporting_service import ReportingService
from production.services.daily_report_service import DailyReportService
from production.services.scheduler import start_scheduler, stop_scheduler
from production.workers.message_processor import (
    process_incoming_message,
    test_whatsapp_message,
    test_web_form
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup - try to connect to DB, continue even if it fails
    try:
        await DatabaseClient.initialize(os.getenv("DATABASE_URL"))
        print("✅ Database connected")
    except Exception as e:
        print(f"⚠️  DB unavailable (will use in-memory fallback): {e}")
        
    # 2. Start the Cron Scheduler
    start_scheduler() 
    
    print("🚀 FlowForge Customer Success FTE started")
    yield
    
    # 3. Shutdown
    try:
        await DatabaseClient.close()
    except Exception:
        pass
    
    # 4. Stop the Cron Scheduler
    stop_scheduler()


app = FastAPI(title="FlowForge Customer Success FTE", lifespan=lifespan)

# Singletons
whatsapp_ingestion = WhatsAppIngestion()
web_form_ingestion = WebFormIngestion()
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID", ""),
    os.getenv("TWILIO_AUTH_TOKEN", "")
)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Production Twilio WhatsApp webhook."""

    # 1. Validate signature (TODO: re-enable for production)
    # if not await whatsapp_ingestion.validate_webhook(request):
    #     raise HTTPException(status_code=401, detail="Invalid Twilio signature")

    # 2. Parse form data (validate_webhook already read it — reuse params)
    form_data = await request.form()
    form_dict = dict(form_data)

    # Guard against empty messages
    body = form_dict.get("Body", "").strip()
    if not body:
        return {"status": "ignored", "reason": "empty_message"}

    # 3. Publish to Kafka (Async Processing)
    result = await whatsapp_ingestion.process_webhook(form_dict)

    # If Kafka failed and fallback returned a result, send it.
    # Otherwise, just return 200 OK and let Kafka consumer handle it.
    if result and result.get("response"):
        twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
        if twilio_number and result.get("customer_phone"):
            try:
                message = twilio_client.messages.create(
                    body=result["response"],
                    from_=twilio_number,
                    to=f"whatsapp:{result['customer_phone']}",
                )
                print(f"✅ WhatsApp reply sent | SID: {message.sid}")
                result["twilio_sid"] = message.sid
            except Exception as e:
                error_msg = str(e)
            print(f"⚠️ Failed to send WhatsApp reply: {error_msg}")
            # Log to file for debugging
            with open("whatsapp_errors.log", "a") as f:
                from datetime import datetime
                f.write(f"{datetime.now().isoformat()} | ERROR: {error_msg} | Phone: {result['customer_phone']} | Response: {result['response'][:100]}\n")
            result["twilio_error"] = error_msg
    else:
        missing = []
        if not twilio_number: missing.append("TWILIO_WHATSAPP_NUMBER")
        if not result.get("customer_phone"): missing.append("customer_phone")
        print(f"⚠️ Missing env vars: {', '.join(missing)} — skipping reply")

    return {
        "status": "success",
        "ticket_id": str(result.get("ticket_id", "")),
        "response_status": result.get("status", ""),
    }


@app.post("/support/form")
async def web_support_form(form: SupportFormSubmission):
    result = await web_form_ingestion.process_submission(form)
    return {"status": "ticket_created", "ticket_id": str(result["ticket_id"])}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "crm-digital-fte"}


@app.post("/test/message")
async def test_message(raw: dict):
    """Send any message and see the full agent run"""
    result = await process_incoming_message(raw)
    return result


@app.get("/test/whatsapp")
async def quick_whatsapp_test():
    """One-click test with WhatsApp example"""
    result = await test_whatsapp_message()
    return result


@app.get("/test/webform")
async def quick_webform_test():
    """One-click test with Web Form example"""
    result = await test_web_form()
    return result

gmail_ingestion = GmailIngestion()

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request):
    """Gmail Pub/Sub webhook."""
    pubsub_message = await request.json()
    
    # Parse incoming notification
    messages = await gmail_ingestion.process_notification(pubsub_message)
    
    if not messages:
        return {"status": "no_new_messages"}

    results = []
    for msg in messages:
        # Prepare payload for Kafka
        kafka_payload = {
            "channel": "email",
            "content": msg["content"],
            "customer_name": msg["customer_name"],
            "metadata": msg["metadata"],
            "channel_message_id": msg.get("channel_message_id"),
            "thread_id": msg.get("thread_id"),
            "subject": msg.get("subject"),
            "processed": False
        }
        
        # Publish to Kafka
        try:
            await kafka_producer.send_message(kafka_payload)
        except Exception as e:
            print(f"⚠️ Failed to publish email to Kafka: {e}")
            # Fallback to sync processing
            agent_result = await process_customer_message({
                "channel": "email",
                "content": msg["content"],
                "customer_name": msg["customer_name"],
                "metadata": msg["metadata"]
            })
            results.append({"status": "processed_sync", "email": msg["customer_email"]})
            continue

        results.append({"status": "published_to_kafka", "email": msg["customer_email"]})

    return {"status": "processed", "messages": len(results), "results": results}

reporting = ReportingService()
daily_reporter = DailyReportService()

@app.get("/reports/sentiment")
async def sentiment_report(channel: str = None, days: int = 7):
    """Get sentiment analysis report for the last N days."""
    return await reporting.get_sentiment_report(channel=channel, days=days)

@app.post("/reports/send-daily")
async def send_daily_report(days: int = 1):
    """Generate and email the daily sentiment report to the admin."""
    return await daily_reporter.generate_and_send(days=days)