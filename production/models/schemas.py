from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class CustomerBase(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TicketCreate(BaseModel):
    customer_id: UUID
    conversation_id: Optional[UUID] = None
    source_channel: str
    category: str
    priority: str = "medium"
    content: str

class MessageCreate(BaseModel):
    conversation_id: UUID
    channel: str
    direction: str
    role: str
    content: str
    sentiment: Optional[float] = None
    channel_message_id: Optional[str] = None

class EscalationCreate(BaseModel):
    ticket_id: UUID
    reason: str
    urgency: str
    notes: Optional[str] = None