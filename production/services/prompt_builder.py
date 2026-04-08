# production/services/prompt_builder.py
import textwrap
from production.agents.tools import search_knowledge_base  # for future RAG

from prototype import (
    CLASSIFY_PROMPT_TEMPLATE,
    PRODUCT_DOCS,
    ESCALATION_RULES,
    BRAND_VOICE,
    _format_conversation_history,
    _apply_do_not_escalate_overrides
)

def build_system_prompt(ticket: dict, conversation_history: list | None = None) -> str:
    """Reuses your exact prompt logic from prototype.py"""
    history_block = _format_conversation_history(conversation_history) if conversation_history else "  (no prior messages)"
    has_history = conversation_history is not None and len(conversation_history) > 1

    history_section = ""
    if has_history:
        history_section = f"""\
## Recent Conversation History
The customer has an active session with prior messages:
{history_block}
Use this context to understand follow-ups.
"""

    return textwrap.dedent(f"""\
You are the FlowForge Customer Success AI agent.

## Company Context
FlowForge is a modern project management SaaS...

## Product Knowledge
{PRODUCT_DOCS}

## Escalation Rules
{ESCALATION_RULES}

## Brand Voice & Tone
{BRAND_VOICE}
{history_section}

## Current Customer Message
Channel: {ticket.get('channel')}
Customer: {ticket.get('customer_name')}
Message: {ticket.get('content')}
Detected Intents: {', '.join(ticket.get('intents', []))}
Sentiment: {ticket.get('sentiment', 0.5)}
Urgency: {ticket.get('urgency', 'normal')}
Is Follow-up: {ticket.get('is_follow_up', False)}
Escalation Reason: {ticket.get('escalation_reason') or 'None'}

## Instructions
1. If escalation_reason is NOT empty, output ONLY "ESCALATE: <reason>"
2. ... (rest of your 10 instructions from prototype.py)
""")