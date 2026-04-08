"""
FlowForge Customer Success Digital FTE — MCP Server
Exposes agent capabilities as tools via Model Context Protocol.
Transport: stdio (standard for Claude Code integration)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Import shared state from prototype
# ---------------------------------------------------------------------------
# SessionStore and escalation_store live in prototype.py.
# We import them so this server shares the same in-memory state.
try:
    from prototype import session_store, escalation_store, PRODUCT_DOCS
except ImportError:
    # Fallback for standalone testing — replicate minimal state
    session_store: dict = {}
    escalation_store: list = []
    PRODUCT_DOCS = """\
    # FlowForge Product Documentation

    ## Core Features
    1. Boards & Tasks — Drag-and-drop Kanban, subtasks, due dates, assignees
    2. Automations — Recurring tasks, Slack/Teams/Email notifications, auto-assign
    3. AI Insights — Project summaries, delay prediction, task ordering
    4. Integrations — Slack, Teams, GitHub, Jira, Figma, Google Drive, Zapier
    5. Reporting — Burn-down charts, velocity reports, workload balance

    ## Common How-to Questions
    - Create a new board → Click "+" in sidebar → "New Board"
    - Invite team members → Settings → Members → Invite by email
    - Set up automations → Open any board → Automations tab
    - Export data → Board menu → Export → CSV/JSON
    - Connect Slack → Integrations page → Connect Slack

    ## Pricing Tiers
    - Free: 10 users, 5 boards, basic automations
    - Pro: Unlimited boards, advanced automations, AI insights
    - Enterprise: SSO, advanced permissions, dedicated support, SLA

    ## Limitations
    - No built-in time tracking (use Toggl integration)
    - No native mobile app yet (PWA available)
    - No white-labeling in Pro tier
    """

# ---------------------------------------------------------------------------
# In-memory ticket store (prototype scope — PostgreSQL in Stage 2)
# ---------------------------------------------------------------------------
ticket_store: dict[str, dict] = {}

VALID_CHANNELS = {"email", "whatsapp", "web_form"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP("flowforge-customer-success-fte")


# ---------------------------------------------------------------------------
# Tool 1: search_knowledge_base
# ---------------------------------------------------------------------------
@mcp.tool()
async def search_knowledge_base(query: str, max_results: int = 3) -> str:
    """
    Search the FlowForge product knowledge base for relevant information.

    When to use:
        Call this whenever a customer asks a question about product features,
        how-to steps, integrations, pricing tiers, or known limitations.
        Always search before answering product questions.

    Args:
        query: The customer's question or keywords to search for.
        max_results: Maximum number of matching sections to return (default 3).

    Returns:
        Formatted string of matching knowledge base sections with relevance
        context. Returns a "not found" message if no sections match.

    Constraints:
        - Uses keyword matching (prototype). Stage 2 uses pgvector similarity.
        - max_results is capped at 5 to keep context size manageable.
    """
    max_results = min(max_results, 5)
    query_lower = query.lower()
    query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 2]

    # Split docs into sections by "##" headings
    sections = []
    current_section = []
    for line in PRODUCT_DOCS.splitlines():
        if line.startswith("## ") and current_section:
            sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    if current_section:
        sections.append("\n".join(current_section))

    # Score each section by term frequency
    scored = []
    for section in sections:
        section_lower = section.lower()
        score = sum(section_lower.count(term) for term in query_terms)
        if score > 0:
            scored.append((score, section.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_results]

    if not top:
        return (
            "No relevant documentation found for your query. "
            "Consider escalating to human support if the question is outside "
            "the product scope."
        )

    results = []
    for i, (score, section) in enumerate(top, 1):
        # Truncate very long sections
        preview = section if len(section) <= 600 else section[:597] + "..."
        results.append(f"[Result {i}]\n{preview}")

    return "\n\n---\n\n".join(results)


# ---------------------------------------------------------------------------
# Tool 2: create_ticket
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    channel: str,
) -> str:
    """
    Create a support ticket in the ticket management system.

    When to use:
        Call this at the START of every customer interaction before generating
        a response. Also call for bug reports and escalations. Include the
        source channel so interactions are tracked per-channel.

    Args:
        customer_id: Unique customer identifier — email address or WhatsApp
                     wa_id (e.g. "923001234567").
        issue: Brief description of the customer's issue or request.
        priority: Severity level — one of: low | medium | high | urgent
        channel: Source channel — one of: email | whatsapp | web_form

    Returns:
        Ticket ID string in the format TKT-XXXXXXXX.

    Constraints:
        - channel must be one of: email, whatsapp, web_form
        - priority must be one of: low, medium, high, urgent
        - Raises ValueError for invalid inputs.
    """
    channel = channel.lower().strip()
    priority = priority.lower().strip()

    if channel not in VALID_CHANNELS:
        raise ValueError(
            f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}"
        )
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"
        )

    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    ticket_store[ticket_id] = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "priority": priority,
        "channel": channel,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "response": None,
        "delivered_at": None,
    }

    return ticket_id


# ---------------------------------------------------------------------------
# Tool 3: get_customer_history
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_customer_history(customer_id: str) -> str:
    """
    Retrieve a customer's interaction history across all channels.

    When to use:
        Call this early in every conversation to check for prior context.
        Especially important for follow-up detection — if the customer says
        "still not working" or "tried what you said", their history explains
        what was already attempted.

    Args:
        customer_id: Unique customer identifier — email or WhatsApp wa_id.

    Returns:
        Formatted string of the last 10 messages from the customer's session,
        including role (customer/agent), channel, sentiment, and timestamp.
        Returns "No previous interactions found." if no history exists.

    Constraints:
        - Returns at most 10 messages to keep context size manageable.
        - History is session-scoped in the prototype (Stage 2: PostgreSQL).
    """
    session = session_store.get(customer_id)

    if not session or not session.get("history"):
        return "No previous interactions found."

    history = session["history"]
    last_10 = history[-10:]

    lines = [
        f"Customer History for {customer_id}",
        f"Session state: {session.get('resolution_state', 'unknown')}",
        f"Total turns: {session.get('ticket_count', len(last_10))}",
        f"Sentiment trajectory: {session.get('sentiment_history', [])}",
        f"Original channel: {session.get('original_channel', 'unknown')}",
        "─" * 40,
    ]

    for msg in last_10:
        role = msg.get("role", "unknown").upper()
        channel = msg.get("channel", "")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        sentiment = msg.get("sentiment", "")

        # Truncate long messages for readability
        if len(content) > 200:
            content = content[:197] + "..."

        sentiment_str = f" | sentiment={sentiment}" if sentiment != "" else ""
        channel_str = f" [{channel}]" if channel else ""
        time_str = f" @ {timestamp[:19]}" if timestamp else ""

        lines.append(f"{role}{channel_str}{time_str}{sentiment_str}")
        lines.append(f"  {content}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: escalate_to_human
# ---------------------------------------------------------------------------
@mcp.tool()
async def escalate_to_human(
    ticket_id: str,
    reason: str,
    urgency: str = "normal",
) -> str:
    """
    Escalate a ticket to a human support agent.

    When to use:
        Call this when any escalation rule is triggered:
        - Pricing negotiations or custom Enterprise quotes
        - Refund or billing disputes
        - Legal, compliance, or data privacy questions
        - Strong negative language or sentiment below 0.3 (consecutive)
        - Account access, security, or SSO issues
        - Customer explicitly requests a human agent
        - Cannot resolve after 2 knowledge base searches
        - Out-of-scope feature requests (mobile app, white-label, etc.)

    Args:
        ticket_id: The TKT-XXXXXXXX ID from create_ticket.
        reason: Human-readable reason for escalation (e.g. "refund_request",
                "consecutive_low_sentiment", "pricing_inquiry").
        urgency: One of: normal | elevated | urgent (default: normal)

    Returns:
        Confirmation string with a unique escalation ID (ESC-XXXXXXXX)
        and a timestamp.

    Constraints:
        - ticket_id should exist in ticket_store (warns if not found).
        - Always call send_response AFTER this tool to deliver an empathy
          holding message to the customer.
    """
    urgency = urgency.lower().strip()
    if urgency not in {"normal", "elevated", "urgent"}:
        urgency = "normal"

    escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Update ticket status if it exists
    if ticket_id in ticket_store:
        ticket_store[ticket_id]["status"] = "escalated"
        ticket_store[ticket_id]["escalation_reason"] = reason
        ticket_store[ticket_id]["escalated_at"] = timestamp
    else:
        # Ticket not found — still record escalation but warn
        print(f"⚠️  Warning: ticket_id '{ticket_id}' not found in ticket_store.")

    # Write to shared escalation store
    escalation_store.append({
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "urgency": urgency,
        "status": "pending_human",
        "created_at": timestamp,
    })

    return (
        f"Escalation recorded.\n"
        f"Escalation ID: {escalation_id}\n"
        f"Ticket: {ticket_id}\n"
        f"Reason: {reason}\n"
        f"Urgency: {urgency}\n"
        f"Timestamp: {timestamp}\n"
        f"Status: pending_human"
    )


# ---------------------------------------------------------------------------
# Tool 5: send_response
# ---------------------------------------------------------------------------
@mcp.tool()
async def send_response(
    ticket_id: str,
    message: str,
    channel: str,
) -> str:
    """
    Send a response to the customer via their channel.

    When to use:
        Call this as the FINAL step of every interaction — after all other
        tools have been called. NEVER respond to a customer without calling
        this tool. It ensures responses are logged and channel-validated.

    Args:
        ticket_id: The TKT-XXXXXXXX ID from create_ticket.
        message: The full response text to send to the customer.
                 Should already be formatted for the channel.
        channel: Target channel — one of: email | whatsapp | web_form

    Returns:
        Delivery status string with timestamp and channel confirmation.
        Format: "delivered | channel=<channel> | ticket=<id> | at=<timestamp>"

    Constraints:
        - channel must be one of: email, whatsapp, web_form
        - WhatsApp messages over 1600 chars will be flagged (not blocked).
        - For prototype: stores response in ticket_store. Stage 2 sends
          via Gmail API / Twilio / API response.
    """
    channel = channel.lower().strip()

    if channel not in VALID_CHANNELS:
        raise ValueError(
            f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}"
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    warning = ""

    # WhatsApp length advisory
    if channel == "whatsapp" and len(message) > 1600:
        warning = f" | ⚠️ message length {len(message)} exceeds WhatsApp 1600-char limit"

    # Store response against ticket
    if ticket_id in ticket_store:
        ticket_store[ticket_id]["response"] = message
        ticket_store[ticket_id]["delivered_at"] = timestamp
        ticket_store[ticket_id]["status"] = ticket_store[ticket_id].get(
            "status", "open"
        ) if ticket_store[ticket_id].get("status") == "escalated" else "resolved"
    else:
        print(f"⚠️  Warning: ticket_id '{ticket_id}' not found in ticket_store.")

    return (
        f"delivered | channel={channel} | ticket={ticket_id} | at={timestamp}{warning}"
    )


# ---------------------------------------------------------------------------
# Standalone test block
# ---------------------------------------------------------------------------
async def _run_tests():
    print("=" * 60)
    print("MCP TOOL TESTS")
    print("=" * 60)

    # 1. Knowledge base search
    print("\n[1] search_knowledge_base('how to invite team members')")
    result = await search_knowledge_base("how to invite team members")
    print(result)

    # 2. Create ticket
    print("\n[2] create_ticket(...)")
    ticket_id = await create_ticket(
        customer_id="test@example.com",
        issue="Cannot export CSV",
        priority="high",
        channel="email",
    )
    print(f"Ticket created: {ticket_id}")

    # 3. Customer history — empty case
    print("\n[3] get_customer_history('test@example.com') — empty")
    history = await get_customer_history("test@example.com")
    print(history)

    # 4. Escalate
    print("\n[4] escalate_to_human(...)")
    esc = await escalate_to_human(
        ticket_id=ticket_id,
        reason="billing_dispute",
        urgency="normal",
    )
    print(esc)

    # 5. Send response
    print("\n[5] send_response(...)")
    status = await send_response(
        ticket_id=ticket_id,
        message="Hi, we have received your request and our billing team will be in touch within 24 hours.",
        channel="email",
    )
    print(status)

    # 6. Invalid channel — should raise ValueError
    print("\n[6] send_response with invalid channel — expect ValueError")
    try:
        await send_response(ticket_id=ticket_id, message="test", channel="fax")
    except ValueError as e:
        print(f"✅ ValueError raised correctly: {e}")

    # 7. Ticket store state
    print("\n[7] ticket_store final state:")
    import json as _json
    print(_json.dumps(ticket_store, indent=2))

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(_run_tests())
    else:
        # Start MCP server on stdio transport
        mcp.run(transport="stdio")