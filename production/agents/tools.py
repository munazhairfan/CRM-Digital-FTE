# production/agents/tools.py
from agents import function_tool
from typing import Any
from uuid import UUID
import uuid
import json
from datetime import datetime

from production.clients.db_client import DatabaseClient
from production.repositories.customer_repo import CustomerRepository
from production.repositories.ticket_repo import TicketRepository
from production.repositories.escalation_repo import EscalationRepository
from production.models.schemas import CustomerBase, TicketCreate

# ----------------------------------------------------------------------
# Tool 1: search_knowledge_base (keyword search for now)
# ----------------------------------------------------------------------
@function_tool
async def search_knowledge_base(query: str, max_results: int = 3) -> str:
    """Search the FlowForge product knowledge base."""
    # For Stage 2 we will replace with pgvector. Keeping your keyword logic for now.
    # (You can paste your full PRODUCT_DOCS here or load from file)
    from prototype import PRODUCT_DOCS  # reuse your embedded docs

    max_results = min(max_results, 5)
    query_lower = query.lower()
    query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 2]

    sections = []
    current = []
    for line in PRODUCT_DOCS.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    scored = []
    for section in sections:
        score = sum(section.lower().count(term) for term in query_terms)
        if score > 0:
            scored.append((score, section.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_results]

    if not top:
        return "No relevant documentation found. Consider escalating to human support if needed."

    results = []
    for i, (_, section) in enumerate(top, 1):
        preview = section if len(section) <= 600 else section[:597] + "..."
        results.append(f"[Result {i}]\n{preview}")

    return "\n\n---\n\n".join(results)


# ----------------------------------------------------------------------
# Tool 2: create_ticket
# ----------------------------------------------------------------------
@function_tool
async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str = "medium",
    channel: str = "email",
) -> str:
    """Create a support ticket. ALWAYS call this first."""
    customer_repo = CustomerRepository()
    ticket_repo = TicketRepository()

    # Get or create customer
    customer_data = CustomerBase(
        email=customer_id if "@" in customer_id else None,
        phone=customer_id if customer_id.startswith("+") else None,
        metadata={"source": channel}
    )
    customer = await customer_repo.get_or_create(customer_data)

    ticket_data = TicketCreate(
        customer_id=customer["id"],
        conversation_id=None,  # will be linked later
        source_channel=channel,
        category="general_inquiry",  # classifier will refine
        priority=priority,
        content=issue
    )

    ticket = await ticket_repo.create(ticket_data)
    return f"TKT-{ticket['id'].hex[:8].upper()}"


# ----------------------------------------------------------------------
# Tool 3: get_customer_history
# ----------------------------------------------------------------------
@function_tool
async def get_customer_history(customer_id: str) -> str:
    """Get full customer history across channels."""
    # For now we return a simple message. In full production we would query messages table.
    # You can expand this later with a MessageRepository.
    return (
        f"Customer history for {customer_id}:\n"
        "• No previous interactions in this session (Stage 2 will use PostgreSQL messages table)."
    )


# ----------------------------------------------------------------------
# Tool 4: escalate_to_human
# ----------------------------------------------------------------------
@function_tool
async def escalate_to_human(
    ticket_id: str,
    reason: str,
    urgency: str = "normal",
) -> str:
    """Escalate ticket to human support."""
    escalation_repo = EscalationRepository()
    ticket_repo = TicketRepository()

    # Mark ticket as escalated
    await ticket_repo.mark_escalated(UUID(ticket_id), reason)

    # Record escalation
    await escalation_repo.create(
        ticket_id=UUID(ticket_id),
        reason=reason,
        urgency=urgency
    )

    return f"ESC-{uuid.uuid4().hex[:8].upper()} | Reason: {reason} | Urgency: {urgency}"


# ----------------------------------------------------------------------
# Tool 5: send_response
# ----------------------------------------------------------------------
@function_tool
async def send_response(
    ticket_id: str,
    message: str,
    channel: str,
) -> str:
    """Send final response to customer. ALWAYS call this last."""
    # In production this will call Gmail/Twilio/Webhook.
    # For now we just log it.
    timestamp = datetime.utcnow().isoformat()
    print(f"📤 RESPONSE SENT → Channel: {channel} | Ticket: {ticket_id}")
    return f"delivered | channel={channel} | ticket={ticket_id} | at={timestamp}"