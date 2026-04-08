"""
production/repositories/interaction_repo.py
Persists customer interactions to PostgreSQL after every ticket is processed.
"""
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Optional

from production.clients.db_client import DatabaseClient


async def save_interaction(ticket, session=None, latency_ms: Optional[int] = None) -> dict:
    """
    Save a fully processed interaction to the database.
    Performs 4 operations in a single transaction:
    1. UPSERT customer
    2. UPSERT conversation
    3. INSERT 2 messages (inbound + outbound)
    4. INSERT ticket
    
    Returns: {"customer_id": uuid, "conversation_id": uuid, "ticket_id": uuid}
    """
    # Helper to safely get attributes from either a Ticket dataclass or a dict
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if obj else default

    # Determine identifiers
    email = None
    phone = None
    wa_id = None
    name = _get(ticket, 'customer_name') or "Unknown"
    customer_id_raw = _get(ticket, 'customer_id') or ""
    channel = _get(ticket, 'channel') or "unknown"
    content = _get(ticket, 'content') or ""
    response = _get(ticket, 'response') or ""
    status = _get(ticket, 'status') or "open"
    sentiment = float(_get(ticket, 'sentiment') or 0.5)
    intents = _get(ticket, 'intents') or []
    urgency = _get(ticket, 'urgency') or "medium"
    escalation_reason = _get(ticket, 'escalation_reason') or ""
    ticket_id_raw = _get(ticket, 'id') or f"TKT-{uuid.uuid4().hex[:8].upper()}"
    meta = _get(ticket, 'metadata') or {}

    # Extract email/phone based on channel
    if channel == "email":
        email = customer_id_raw if "@" in str(customer_id_raw) else meta.get("from")
    elif channel == "whatsapp":
        wa_id = customer_id_raw
        phone = str(customer_id_raw) if not str(customer_id_raw).startswith("+") else None
    elif channel == "web_form":
        email = customer_id_raw if "@" in str(customer_id_raw) else meta.get("email")

    async with DatabaseClient.get_connection() as conn:
        async with conn.transaction():
            # 1. UPSERT Customer
            # Try to find by email or phone first
            existing = await conn.fetchrow(
                "SELECT id, name FROM customers WHERE email = $1 OR phone = $2",
                email, phone
            )

            if existing:
                customer_id = existing["id"]
                # Update name if we now have a better one
                if name and name != "Unknown" and existing["name"] in (None, "Unknown"):
                    await conn.execute(
                        "UPDATE customers SET name = $1 WHERE id = $2",
                        name, customer_id
                    )
            else:
                customer_id = uuid.uuid4()
                await conn.execute(
                    """
                    INSERT INTO customers (id, email, phone, name, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    customer_id, email, phone, name, json.dumps(meta or {})
                )

            # Store cross-channel identifier (wa_id for WhatsApp)
            if wa_id:
                await conn.execute(
                    """
                    INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value)
                    VALUES ($1, 'wa_id', $2)
                    ON CONFLICT (identifier_type, identifier_value) DO NOTHING
                    """,
                    customer_id, wa_id
                )

            # 2. UPSERT Conversation
            # Check if there's an active conversation for this customer
            conv_row = await conn.fetchrow(
                "SELECT id FROM conversations WHERE customer_id = $1 AND status = 'active' LIMIT 1",
                customer_id
            )

            if conv_row:
                conversation_id = conv_row["id"]
                # Update existing conversation
                new_status = "escalated" if status == "escalated" else (
                    "resolved" if status == "resolved" else "active"
                )
                await conn.execute(
                    """
                    UPDATE conversations 
                    SET sentiment_score = $1, status = $2
                    WHERE id = $3
                    """,
                    sentiment, new_status, conversation_id
                )
            else:
                # New conversation
                conversation_id = uuid.uuid4()
                db_status = "escalated" if status == "escalated" else (
                    "resolved" if status == "resolved" else "active"
                )
                await conn.execute(
                    """
                    INSERT INTO conversations (id, customer_id, initial_channel, status, sentiment_score)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    conversation_id, customer_id, channel, db_status, sentiment
                )

            # 3. INSERT Messages (Inbound + Outbound)
            now = datetime.now(timezone.utc)
            
            # Inbound message (Customer)
            await conn.execute(
                """
                INSERT INTO messages (
                    conversation_id, channel, direction, role, content, 
                    created_at, sentiment, latency_ms, tool_calls, channel_message_id
                )
                VALUES ($1, $2, 'inbound', 'customer', $3, $4, $5, NULL, '[]', $6)
                """,
                conversation_id, channel, content, now, sentiment,
                meta.get("wa_id") or meta.get("from") or customer_id_raw
            )

            # Outbound message (Agent) - only if there's a response
            if response and not response.startswith("ESCALATE:"):
                agent_latency = latency_ms or 0
                await conn.execute(
                    """
                    INSERT INTO messages (
                        conversation_id, channel, direction, role, content, 
                        created_at, latency_ms, tool_calls, delivery_status
                    )
                    VALUES ($1, $2, 'outbound', 'agent', $3, $4, $5, '[]', 'sent')
                    """,
                    conversation_id, channel, response, now, agent_latency
                )

            # 4. INSERT Ticket
            ticket_id = uuid.uuid4()
            ticket_number = ticket_id_raw
            category = intents[0] if intents else "general_inquiry"
            priority = urgency
            db_status = "escalated" if status == "escalated" else (
                "resolved" if status == "resolved" else "open"
            )
            
            await conn.execute(
                """
                INSERT INTO tickets (
                    id, conversation_id, customer_id, ticket_number, source_channel,
                    category, priority, status, created_at, escalated_reason
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                ticket_id, conversation_id, customer_id, ticket_number, channel,
                category, priority, db_status, now, escalation_reason
            )

            # Update ticket ID on the ticket object if possible
            if hasattr(ticket, 'id'):
                ticket.id = ticket_number

    return {
        "customer_id": str(customer_id),
        "conversation_id": str(conversation_id),
        "ticket_id": str(ticket_id),
        "ticket_number": ticket_number,
    }
