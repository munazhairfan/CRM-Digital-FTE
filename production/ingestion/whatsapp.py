# production/ingestion/whatsapp.py
from fastapi import Request
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import os
from twilio.request_validator import RequestValidator

from production.repositories.customer_repo import CustomerRepository
from production.repositories.ticket_repo import TicketRepository
from production.services.agent_service import process_customer_message
from production.clients.kafka_client import kafka_producer
from production.models.schemas import CustomerBase, TicketCreate


class WhatsAppIngestion:
    def __init__(self):
        self.customer_repo = CustomerRepository()
        self.ticket_repo = TicketRepository()
        self.validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN", ""))

    async def validate_webhook(self, request: Request) -> bool:
        """Validate Twilio webhook signature."""
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        form_data = await request.form()
        params = dict(form_data)
        return self.validator.validate(url, params, signature)

    async def process_webhook(self, form_data: Dict[str, Any]) -> dict:
        """Process incoming WhatsApp message and run full agent pipeline."""

        # Extract customer info
        phone = form_data.get("From", "").replace("whatsapp:", "")
        profile_name = form_data.get("ProfileName", "WhatsApp User")
        wa_id = form_data.get("WaId", phone)
        body = form_data.get("Body", "").strip()

        if not body:
            return {
                "customer_phone": phone,
                "ticket_id": None,
                "response": "",
                "status": "ignored",
            }

        # Try DB operations (graceful fallback if DB unavailable)
        ticket_id = None
        try:
            customer_model = CustomerBase(
                email=None,
                phone=phone,
                name=profile_name,
                metadata={"wa_id": wa_id, "num_media": form_data.get("NumMedia", "0")},
            )
            customer = await self.customer_repo.get_or_create(customer_model)

            ticket_model = TicketCreate(
                customer_id=customer["id"],
                conversation_id=None,
                source_channel="whatsapp",
                category="general_inquiry",
                priority="medium",
                content=body,
            )
            ticket = await self.ticket_repo.create(ticket_model)
            ticket_id = ticket["id"]
        except Exception as e:
            print(f"⚠️  DB unavailable, skipping ticket creation: {e}")

        # Run the full production agent OR send to Kafka for async processing
        raw_message = {
            "channel": "whatsapp",
            "content": body,
            "customer_name": profile_name,
            "metadata": {
                "wa_id": wa_id,
                "num_media": form_data.get("NumMedia", "0"),
            },
            "customer_phone": phone,
            "ticket_id": ticket_id,
            "processed": False
        }

        # Publish to Kafka for async processing
        try:
            await kafka_producer.send_message(raw_message)
        except Exception as e:
            print(f"⚠️ Failed to publish to Kafka: {e}")
            # Fallback to sync processing if Kafka is down
            agent_result = await process_customer_message(raw_message)
            return {
                "customer_phone": phone,
                "ticket_id": ticket_id or agent_result.get("ticket_id"),
                "response": agent_result["response"],
                "status": agent_result["status"],
            }
