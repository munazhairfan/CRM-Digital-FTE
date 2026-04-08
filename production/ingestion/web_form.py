# production/ingestion/web_form.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from production.models.schemas import MessageCreate, TicketCreate
from production.repositories.customer_repo import CustomerRepository
from production.repositories.ticket_repo import TicketRepository
from production.clients.kafka_client import kafka_producer

class SupportFormSubmission(BaseModel):
    name: str
    email: EmailStr
    subject: str
    category: str = Field(..., pattern="^(general|technical|billing|feedback|bug_report)$")
    message: str
    priority: Optional[str] = "medium"
    attachments: Optional[List[str]] = Field(default_factory=list)

class WebFormIngestion:
    def __init__(self):
        self.customer_repo = CustomerRepository()
        self.ticket_repo = TicketRepository()

    async def process_submission(self, form: SupportFormSubmission) -> dict:
        """Process standalone web support form submission."""
        
        customer_data = {
            "email": form.email,
            "name": form.name,
            "metadata": {"source": "web_form"}
        }

        customer = await self.customer_repo.get_or_create(customer_data)

        ticket_data = {
            "customer_id": customer["id"],
            "source_channel": "web_form",
            "category": form.category,
            "priority": form.priority,
            "content": f"{form.subject}\n\n{form.message}"
        }

        ticket = await self.ticket_repo.create(ticket_data)

        # Prepare message for Kafka
        kafka_message = {
            "channel": "web_form",
            "content": f"{form.subject}\n\n{form.message}",
            "customer_name": form.name,
            "metadata": {
                "email": form.email,
                "category": form.category,
                "subject": form.subject
            },
            "ticket_id": ticket["id"],
            "processed": False
        }

        # Publish to Kafka
        try:
            await kafka_producer.send_message(kafka_message)
        except Exception as e:
            print(f"⚠️ Failed to publish to Kafka: {e}")

        return {
            "channel": "web_form",
            "channel_message_id": f"web-{ticket['id']}",
            "customer_id": customer["id"],
            "ticket_id": ticket["id"],
            "content": form.message,
            "subject": form.subject,
            "category": form.category,
            "metadata": {
                "name": form.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }