"""
production/services/agent_service.py
Core agent service — now with persistent cross-channel memory.
This file replaces the old in-memory version.
"""

import os
import time
import uuid
import hashlib
from typing import Optional

from production.repositories.conversation_repo import ConversationRepository
from production.repositories.customer_repo import CustomerRepository
from production.repositories.message_repo import MessageRepository
from production.prompts import normalize, classify, generate_response
from production.models.schemas import CustomerBase

conversation_repo = ConversationRepository()
customer_repo = CustomerRepository()
message_repo = MessageRepository()


async def process_customer_message(raw_message: dict) -> dict:
    """
    End-to-end message processing with persistent memory.
    1. Normalize Raw Input
    2. Get/Create Conversation (Unified ID)
    3. Fetch 7-Day Context
    4. Classify & Generate Response
    5. Save to DB
    """
    start_ms = int(time.time() * 1000)

    # ------------------------------------------------------------------
    # Step 1: Resolve Identity & Ensure Customer Exists
    # ------------------------------------------------------------------
    email = raw_message.get("metadata", {}).get("customer_email")
    phone = raw_message.get("metadata", {}).get("wa_id")
    name = raw_message.get("customer_name", "Unknown")
    
    # Create or fetch customer (Will raise exception if DB fails)
    customer_record = await customer_repo.get_or_create(CustomerBase(email=email, phone=phone, name=name))
    customer_uuid = str(customer_record['id'])

    # ------------------------------------------------------------------
    # Step 2: Get or Create Conversation
    # ------------------------------------------------------------------
    try:
        conversation_id = await conversation_repo.get_or_create_conversation(
            customer_id=customer_uuid,
            initial_channel=raw_message["channel"],
        )
    except Exception as conv_err:
        raise Exception(f"Conversation failed for customer {customer_uuid}. Original DB error: {error_detail if 'error_detail' in locals() else 'Unknown'}")

    # ------------------------------------------------------------------
    # Step 3: Load Persistent Context (7-Day Memory)
    # ------------------------------------------------------------------
    customer_context = await message_repo.get_customer_context(
        customer_id=customer_uuid,
        days=7,
    )

    # ------------------------------------------------------------------
    # Step 4: Build Ticket & Inject Context
    # ------------------------------------------------------------------
    ticket = normalize(raw_message)
    
    # INJECT MEMORY HERE
    if customer_context:
        ticket.metadata["persistent_context"] = customer_context

    # ------------------------------------------------------------------
    # Step 5: Classify
    # ------------------------------------------------------------------
    ticket = await classify(ticket)

    # ------------------------------------------------------------------
    # Step 6: Save Inbound Message
    # ------------------------------------------------------------------
    await message_repo.save_message(
        conversation_id=conversation_id,
        channel=raw_message["channel"],
        direction="inbound",
        role="customer",
        content=raw_message["content"],
        sentiment=ticket.sentiment,
    )

    # ------------------------------------------------------------------
    # Step 7: Generate Response
    # ------------------------------------------------------------------
    ticket = await generate_response(ticket)
    latency_ms = int(time.time() * 1000) - start_ms

    # ------------------------------------------------------------------
    # Step 8: Save Outbound Message
    # ------------------------------------------------------------------
    await message_repo.save_message(
        conversation_id=conversation_id,
        channel=raw_message["channel"],
        direction="outbound",
        role="agent",
        content=ticket.response,
        latency_ms=latency_ms,
        delivery_status="sent",
    )

    # ------------------------------------------------------------------
    # Step 9: Update Conversation Status (Temporarily Disabled due to DB Type Mismatch)
    # ------------------------------------------------------------------
    # new_status = "active" if ticket.status == "new" else ticket.status
    # await conversation_repo.update_status(
    #     conversation_id=conversation_id,
    #     status=new_status,
    #     sentiment_score=ticket.sentiment,
    #     resolution_type=ticket.escalation_reason if ticket.escalation_reason else None,
    # )

    # ------------------------------------------------------------------
    # Step 10: Summarize on Terminal State
    # ------------------------------------------------------------------
    if ticket.status in ("resolved", "escalated"):
        try:
            await message_repo.summarize_and_store(
                conversation_id=conversation_id,
                customer_id=customer_uuid,
                channel=raw_message["channel"],
            )
        except Exception:
            pass # Non-critical failure

    return {
        "ticket_id": ticket.id,
        "conversation_id": conversation_id,
        "customer_id": customer_uuid,
        "channel": raw_message["channel"],
        "status": ticket.status,
        "response": ticket.response,
        "escalation_reason": ticket.escalation_reason,
        "sentiment": ticket.sentiment,
        "latency_ms": latency_ms,
    }
