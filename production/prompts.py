"""
FlowForge Customer Success Digital FTE — Core Interaction Prototype
Single-file prototype. OpenAI GPT-4o direct calls. In-memory only.
"""

import json
import os
import re
import asyncio
import textwrap
import uuid
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# 0. Configuration
# ---------------------------------------------------------------------------
load_dotenv(override=True)
client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

# ---------------------------------------------------------------------------
# Retry helper for Gemini 503 errors
# ---------------------------------------------------------------------------
async def _llm_with_retry(async_fn, max_retries=3, base_delay=2):
    """Call an async OpenAI API function with exponential backoff on 503."""
    for attempt in range(max_retries):
        try:
            return await async_fn()
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"   ⏳ Gemini 503 — retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise

# ---------------------------------------------------------------------------
# 1. Knowledge Base (embedded from /context files)
# ---------------------------------------------------------------------------
PRODUCT_DOCS = """\
# FlowForge Product Documentation

## Core Features
1. **Boards & Tasks**
   - Drag-and-drop Kanban boards
   - Tasks with subtasks, due dates, assignees, labels, and priorities
   - Custom fields (dropdown, number, date, checkbox)

2. **Automations**
   - When a task is moved to "Done" → notify Slack/Teams/Email
   - Auto-assign tasks based on labels
   - Recurring tasks

3. **AI Insights**
   - Auto-generate project summaries
   - Predict delays using historical data
   - Suggest optimal task order

4. **Integrations**
   - Slack, Microsoft Teams, GitHub, Jira, Figma, Google Drive, Zapier

5. **Reporting**
   - Burn-down charts, velocity reports, workload balance

## Common How-to Questions (Agent must know these)
- How do I create a new board? → Click "+" in sidebar → "New Board"
- How do I invite team members? → Settings → Members → Invite by email
- How do I set up automations? → Open any board → Automations tab
- How do I export data? → Board menu → Export → CSV/JSON
- How do I connect Slack? → Integrations page → Connect Slack

## Pricing Tiers
- Free: 10 users, 5 boards, basic automations
- Pro: Unlimited boards, advanced automations, AI insights
- Enterprise: SSO, advanced permissions, dedicated support, SLA

## Limitations (Never promise these)
- We do not have built-in time tracking (use Toggl integration)
- No native mobile app yet (PWA available)
- No white-labeling in Pro tier
"""

ESCALATION_RULES = """\
# Escalation Rules for Customer Success Agent

## Escalate to Human Immediately When:
- Customer mentions pricing negotiations, discounts, or custom Enterprise quotes
- Refund or billing dispute is requested
- Legal, compliance, or data privacy questions (GDPR, contracts)
- Customer uses strong negative language (angry, swearing, "worst product ever")
- Sentiment score drops below 0.3 for two consecutive messages
- Issue involves account access / security / SSO / data export
- Customer explicitly asks for "human", "manager", or "real person"
- Technical issue cannot be solved after 2 knowledge-base searches
- Feature request that is clearly out of scope (mobile app, white-label, etc.)

## Do NOT Escalate (Handle Yourself):
- How-to questions about existing features
- Bug reports (create ticket + ask for more details)
- General feedback
- Integration setup questions (if covered in docs)
"""

BRAND_VOICE = """\
# Brand Voice & Tone Guidelines

## Core Tone
- Friendly but professional
- Helpful and patient
- Clear and concise
- Slightly warm and encouraging

## Voice Characteristics
- Use "we" and "you" (never "I")
- Short sentences for WhatsApp
- Slightly longer, structured responses for Email
- Always end with a clear next step or question
- Never sound robotic or overly corporate

## Example Good Response (Email):
"Hi Ahmed 👋

Great question! You can invite team members by going to Settings → Members → Invite by email.

Would you like me to walk you through it step-by-step?"

## Example Good Response (WhatsApp):
"Hey Sara! No worries — try refreshing the page or clearing your browser cache. Still stuck? Let me know what you see."

## Things to NEVER say:
- "As an AI I can't..."
- Competitor names
- "I'm sorry for the inconvenience" (sounds scripted)
- Over-promising future features
"""

# ---------------------------------------------------------------------------
# 2. Unified Ticket Schema
# ---------------------------------------------------------------------------
@dataclass
class Ticket:
    id: str
    channel: str                         # email | whatsapp | web_form
    customer_name: str
    customer_id: str                     # email or wa_id
    content: str
    metadata: dict = field(default_factory=dict)
    session_id: str = ""
    timestamp: str = ""
    # --- Classification (filled by pipeline) ---
    intents: list[str] = field(default_factory=list)
    sentiment: float = 0.5               # 0.0 (very negative) – 1.0 (very positive)
    urgency: str = "normal"              # normal | elevated | urgent
    is_follow_up: bool = False
    escalation_reason: str = ""
    status: str = "new"                  # new | escalated | resolved
    response: str = ""
    bug_ticket_id: str = ""              # populated when intent=bug_report


# ---------------------------------------------------------------------------
# 3. Session Store (in-memory)
# ---------------------------------------------------------------------------
@dataclass
class Session:
    customer_id: str
    customer_name: str
    channel: str
    conversation_history: list[dict] = field(default_factory=list)
    # Each entry: {"role": "user"|"assistant", "content": str, "timestamp": str}
    sentiment_history: list[float] = field(default_factory=list)
    resolution_state: str = "open"       # open | escalated | resolved
    ticket_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class SessionStore:
    """In-memory session store keyed by customer_id."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, customer_id: str, customer_name: str, channel: str) -> Session:
        if customer_id in self._sessions:
            session = self._sessions[customer_id]
            session.customer_name = customer_name  # refresh name
            return session
        now = datetime.now(timezone.utc).isoformat()
        session = Session(
            customer_id=customer_id,
            customer_name=customer_name,
            channel=channel,
            created_at=now,
            updated_at=now,
        )
        self._sessions[customer_id] = session
        return session

    def get(self, customer_id: str) -> Session | None:
        return self._sessions.get(customer_id)

    def update(self, session: Session):
        self._sessions[session.customer_id] = session

    def list_all(self) -> dict[str, dict]:
        """Return a summary of all sessions for debugging."""
        result = {}
        for cid, s in self._sessions.items():
            result[cid] = {
                "customer_name": s.customer_name,
                "channel": s.channel,
                "resolution_state": s.resolution_state,
                "ticket_count": s.ticket_count,
                "messages_in_history": len(s.conversation_history),
                "avg_sentiment": round(sum(s.sentiment_history) / len(s.sentiment_history), 2) if s.sentiment_history else None,
            }
        return result


# Global session store instance
session_store = SessionStore()


def normalize(raw: dict) -> Ticket:
    """Convert any channel payload into the unified Ticket schema."""
    channel = raw["channel"]
    meta = raw.get("metadata", {})

    if channel == "email":
        customer_id = raw.get("customer_email") or meta.get("from", "")
        customer_name = raw.get("customer_name") or meta.get("name", customer_id.split("@")[0] if "@" in customer_id else customer_id)
    elif channel == "whatsapp":
        customer_id = meta.get("wa_id", raw.get("customer_phone", ""))
        customer_name = raw.get("customer_name") or meta.get("name", customer_id)
    elif channel == "web_form":
        customer_id = raw.get("customer_email") or meta.get("email", "")
        customer_name = raw.get("customer_name") or meta.get("name", customer_id.split("@")[0] if "@" in customer_id else customer_id)
    else:
        raise ValueError(f"Unknown channel: {channel}")

    return Ticket(
        id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
        channel=channel,
        customer_name=customer_name,
        customer_id=customer_id,
        content=raw["content"],
        metadata=meta,
        session_id=meta.get("session_id", customer_id),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


# ---------------------------------------------------------------------------
# 3. Classification Layer (LLM-powered)
# ---------------------------------------------------------------------------
CLASSIFY_PROMPT_TEMPLATE = """\
You are a classification engine for a customer success AI agent.
Analyze the following customer message and return ONLY a valid JSON object
with these fields — no markdown, no explanation:

{{
  "intents": ["list of applicable intent labels"],
  "sentiment": <float 0.0 to 1.0>,
  "urgency": "<normal|elevated|urgent>",
  "is_follow_up": <boolean>,
  "escalation_trigger": "<rule matched or empty>"
}}

Allowed intent labels (use all that apply):
  how_to, bug_report, feature_request, pricing, refund, appreciation,
  feedback, integration_setup, account_access, compliance, escalation_request,
  general_inquiry

Escalation rules to check:
- Pricing negotiations, discounts, or custom Enterprise quotes
- Refund or billing dispute
- Legal, compliance, or data privacy (GDPR, contracts)
- Strong negative language (angry, swearing, "worst product ever")
- Account access / security / SSO / data export
- Customer explicitly asks for "human", "manager", or "real person"
- Feature request clearly out of scope (mobile app, white-label, time tracking)

**CRITICAL EXCEPTIONS: Do NOT escalate these scenarios (Handle them yourself):**
- General pricing inquiries (e.g., "What is the difference between Pro and Enterprise?")
- Positive feedback or renewals (e.g., "We love the platform! Renewing our subscription.")
- Simple feature questions (e.g., "Is there a way to set priority levels?")
- Integration setup (e.g., "How do I connect Slack?")
**NOTE:** These exceptions ONLY apply if the sentiment is neutral/positive. If the user uses strong negative language ("worst ever"), you MUST escalate.

If ANY rule matches, set escalation_trigger to the matched rule text.
Otherwise set it to "".

Follow-up detection hints:
- "Re:", "Follow-up", "Still can't", "previous ticket", "yesterday",
  "tried the steps you gave", "still no", "still not working"
If detected, set is_follow_up to true.

Sentiment scale:
  0.0-0.2  = extremely negative (rage, threats, swearing)
  0.2-0.4  = negative (frustrated, disappointed, annoyed)
  0.4-0.6  = neutral (informational, polite inquiry)
  0.6-0.8  = positive (grateful, pleased)
  0.8-1.0  = very positive (enthusiastic, appreciative)

Urgency:
  normal   = standard inquiry, no time pressure
  elevated = something is broken or blocked for one user
  urgent   = systemic issue, security concern, or explicit "urgent"

Customer message:
Channel: {{channel}}
Content: {{content}}
Metadata: {{metadata}}
"""


async def classify(ticket: Ticket) -> Ticket:
    """Run LLM classification and attach results to the ticket."""
    prompt = CLASSIFY_PROMPT_TEMPLATE.replace("{{channel}}", ticket.channel)\
                                      .replace("{{content}}", ticket.content)\
                                      .replace("{{metadata}}", json.dumps(ticket.metadata))

    resp = await _llm_with_retry(
        lambda: client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
    )

    result = json.loads(resp.choices[0].message.content.strip())

    ticket.intents = result.get("intents", ["general_inquiry"])
    ticket.sentiment = float(result.get("sentiment", 0.5))
    ticket.urgency = result.get("urgency", "normal")
    ticket.is_follow_up = bool(result.get("is_follow_up", False))
    ticket.escalation_reason = result.get("escalation_trigger", "")

    # If escalation reason was detected but escalation rules say DON'T escalate,
    # clear it (e.g., bug_report, feedback, integration_setup are handled by agent)
    _apply_do_not_escalate_overrides(ticket)

    return ticket


def _apply_do_not_escalate_overrides(ticket: Ticket):
    """
    Some messages match escalation keywords but the rules say DON'T escalate.
    Clear the escalation reason so the agent handles it itself.
    """
    reason = ticket.escalation_reason
    if not reason:
        return

    do_not_escalate_patterns = {
        "bug_report": [
            "strong negative language",
            "sentiment score drops below",
        ],
        "integration_setup": [
            "strong negative language",
            "sentiment score drops below",
        ],
        "feedback": [
            "strong negative language",
        ],
    }

    for intent, override_reasons in do_not_escalate_patterns.items():
        if intent in ticket.intents:
            for r in override_reasons:
                if r.lower() in reason.lower():
                    # Exception: If the user says "worst ever", NEVER clear the escalation.
                    if "worst ever" in ticket.content.lower() or "worst product" in ticket.content.lower():
                        return # Keep escalation reason
                    ticket.escalation_reason = ""
                    return

    # If the ONLY match is a bug_report with mild language, don't escalate
    if ticket.intents == ["bug_report"] and reason.lower() in (
        "sentiment score drops below 0.3 for two consecutive messages",
    ):
        ticket.escalation_reason = ""

    # If the match is "strong negative language" and it's a bug report,
    # usually we handle it, UNLESS the language is extreme.
    if "strong negative language" in reason.lower():
        for intent in ("bug_report", "integration_setup", "feedback"):
            if intent in ticket.intents:
                # If it's just frustration with a feature (e.g. "nothing works"), 
                # we can try to handle it. If it says "worst ever", escalate.
                if "worst ever" not in ticket.content.lower() and "worst product" not in ticket.content.lower():
                    ticket.escalation_reason = ""
                    return

    # Out-of-scope feature requests should be handled gracefully by the agent,
    # not escalated. The agent deflects per brand voice (no over-promising).
    if "feature_request" in ticket.intents and "out of scope" in reason.lower():
        ticket.escalation_reason = ""



# ---------------------------------------------------------------------------
# 4. System Prompt Builder
# ---------------------------------------------------------------------------
def _format_conversation_history(history: list[dict]) -> str:
    """Format conversation history for inclusion in the prompt."""
    lines = []
    for msg in history[-5:]:  # last 5 messages
        role = "Customer" if msg["role"] == "user" else "You (Agent)"
        lines.append(f"  {role}: {msg['content']}")
    return "\n".join(lines) if lines else "  (no prior messages)"


def build_system_prompt(ticket: Ticket, conversation_history: list[dict] | None = None) -> str:
    history_block = _format_conversation_history(conversation_history) if conversation_history else "  (no prior messages)"
    has_history = conversation_history is not None and len(conversation_history) > 1

    history_section = ""
    if has_history:
        history_section = f"""\
        ## Recent Conversation History
        The customer has an active session with prior messages:
{history_block}
        Use this context to understand follow-ups and references to previous messages.
        """

    return textwrap.dedent(f"""\
        You are the FlowForge Customer Success AI agent.

        ## Company Context
        FlowForge is a modern project management SaaS for small-to-medium teams (5-200 people).
        12,400+ active teams. Pricing: Free (up to 10 users), Pro ($12/user/month), Enterprise (custom).
        Mission: Make project management feel effortless and delightful.

        ## Product Knowledge
        {PRODUCT_DOCS}

        ## Escalation Rules
        {ESCALATION_RULES}

        ## Brand Voice & Tone
        {BRAND_VOICE}
{history_section}
        ## Current Customer Message
        Channel: {ticket.channel}
        Customer: {ticket.customer_name}
        Message: {ticket.content}
        Detected Intents: {', '.join(ticket.intents)}
        Sentiment: {ticket.sentiment}
        Urgency: {ticket.urgency}
        Is Follow-up: {ticket.is_follow_up}
        Escalation Reason: {ticket.escalation_reason if ticket.escalation_reason else "None"}

        ## Instructions
        1. If escalation_reason is NOT empty, output ONLY the string "ESCALATE: <reason>" and nothing else.
        2. If the message is primarily an appreciation/thanks, respond warmly and briefly.
        3. If the message contains a bug_report:
           - Acknowledge the issue
           - Ask for ONE clarifying detail (browser, steps to reproduce, screenshot, etc.)
           - Confirm a ticket has been logged
        4. If the message is a how-to question, give clear step-by-step instructions from the product docs.
        5. If the message has MULTIPLE intents, address ALL of them in one response.
        6. If the message asks about an out-of-scope feature (mobile app, time tracking, white-label),
           acknowledge the interest, explain the current limitation honestly, and suggest the closest alternative.
        7. Format the response for the channel:
           - whatsapp: short (under 300 chars), warm, conversational, emoji-OK
           - email: formal greeting + structured body + clear next step/question + professional sign-off
           - web_form: professional, medium length, direct and helpful
        8. Always end with a clear next step or question (unless it's pure appreciation).
        9. NEVER say "As an AI I can't...", competitor names, "I'm sorry for the inconvenience", or over-promise future features.
        10. Use "we" and "you" — never "I".
    """)


# ---------------------------------------------------------------------------
# 5. Response Engine
# ---------------------------------------------------------------------------
def generate_empathy_holding(ticket) -> str:
    """Generate a short empathy-first holding message for escalated tickets."""
    # Handle both Ticket dataclass and dict
    if isinstance(ticket, dict):
        name = ticket.get("customer_name", "Customer")
        channel = ticket.get("channel", "web_form")
        reason = ticket.get("escalation_reason", "")
        content = ticket.get("content", "")
    else:
        name = ticket.customer_name
        channel = ticket.channel
        reason = ticket.escalation_reason
        content = ticket.content

    if channel == "whatsapp":
        if "strong negative language" in reason.lower() or \
           "sentiment" in reason.lower():
            return (
                f"Hey {name}! We hear your frustration and we're really sorry about this. "
                f"We're getting someone from our team to look into this right away. 💙"
            )
        if "account access" in reason.lower() or \
           "login" in content.lower() or "cant login" in content.lower():
            return (
                f"Hey {name}! We know how disruptive login issues are — especially for a whole team. "
                f"We're escalating this to our engineers right now and will get back to you ASAP. 💙"
            )
        return (
            f"Hey {name}! We understand this is frustrating. "
            f"We're getting a specialist to help — hang tight. 💙"
        )

    elif channel == "email":
        if "refund" in reason.lower() or \
           "billing" in reason.lower():
            return (
                f"Hi {name},\n\n"
                f"We hear you, and we understand this is frustrating. We've passed your request "
                f"to our billing team, and they'll be in touch within 24 hours.\n\n"
                f"Best regards,\n"
                f"The FlowForge Team"
            )
        if "pricing" in reason.lower() or \
           "enterprise" in reason.lower():
            return (
                f"Hi {name},\n\n"
                f"Thanks for reaching out. We've connected you with our Enterprise team, "
                f"and they'll be in touch shortly to discuss your requirements.\n\n"
                f"Best regards,\n"
                f"The FlowForge Team"
            )
        return (
            f"Hi {name},\n\n"
            f"We understand this is important, and we're connecting you with the right team "
            f"who can help. They'll be in touch soon.\n\n"
            f"Best regards,\n"
            f"The FlowForge Team"
        )

    else:  # web_form
        return (
            f"Hi {name},\n\n"
            f"We've received your request and connected you with the appropriate team. "
            f"Expect a response within 24 hours.\n\n"
            f"Best regards,\n"
            f"The FlowForge Team"
        )


async def generate_response(ticket: Ticket, conversation_history: list[dict] | None = None) -> Ticket:
    """Generate a channel-formatted response. Handles escalation shortcut."""

    # Quick path: if escalation was already flagged, generate empathy holding message
    if ticket.escalation_reason:
        ticket.status = "escalated"
        ticket.response = generate_empathy_holding(ticket)
        return ticket

    system_prompt = build_system_prompt(ticket, conversation_history)

    resp = await _llm_with_retry(
        lambda: client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ticket.content},
            ],
            temperature=0.7,
            max_tokens=500,
        )
    )

    reply = resp.choices[0].message.content.strip()

    # Check if the LLM itself decided to escalate
    if reply.upper().startswith("ESCALATE:"):
        ticket.status = "escalated"
        ticket.escalation_reason = reply[len("ESCALATE:"):].strip()
        ticket.response = generate_empathy_holding(ticket)
        return ticket

    # Bug report → generate an internal ticket ID
    if "bug_report" in ticket.intents:
        ticket.bug_ticket_id = f"BUG-{uuid.uuid4().hex[:6].upper()}"

    ticket.status = "resolved"
    ticket.response = reply
    return ticket


# ---------------------------------------------------------------------------
# 6. Escalation Store (in-memory for prototype)
# ---------------------------------------------------------------------------
escalation_store: list[dict] = []


def record_escalation(ticket: Ticket):
    escalation_store.append({
        "ticket_id": ticket.id,
        "channel": ticket.channel,
        "customer_name": ticket.customer_name,
        "customer_id": ticket.customer_id,
        "content": ticket.content,
        "escalation_reason": ticket.escalation_reason,
        "sentiment": ticket.sentiment,
        "urgency": ticket.urgency,
        "status": "escalated",
        "timestamp": ticket.timestamp,
    })


# ---------------------------------------------------------------------------
# 7. Main Pipeline
# ---------------------------------------------------------------------------
from production.repositories.interaction_repo import save_interaction

async def process_ticket(raw: dict) -> Ticket:
    """End-to-end pipeline with session memory and DB persistence:
       normalize → session load → classify → sentiment check → respond → escalate → save_interaction."""

    start_time = time.time()

    # Step 1: Normalize
    ticket = normalize(raw)

    # Step 2: Load or create session
    session = session_store.get_or_create(ticket.customer_id, ticket.customer_name, ticket.channel)

    # Step 3: Append incoming message to conversation history
    session.conversation_history.append({
        "role": "user",
        "content": ticket.content,
        "timestamp": ticket.timestamp,
    })
    session.ticket_count += 1
    session.updated_at = datetime.now(timezone.utc).isoformat()

    print(f"{'='*60}")
    print(f"📨 TICKET {ticket.id}")
    print(f"   Channel: {ticket.channel}")
    print(f"   Customer: {ticket.customer_name} ({ticket.customer_id})")
    print(f"   Message: {ticket.content}")
    print(f"   Session: {session.ticket_count} message(s), state={session.resolution_state}")
    print(f"{'='*60}")

    # Step 4: Classify
    print("\n🔍 Classifying...")
    ticket = await classify(ticket)

    # Step 5: Append sentiment to history and check consecutive low sentiment
    session.sentiment_history.append(ticket.sentiment)

    # Check consecutive sentiment rule: last 2 scores both at or below 0.3
    if len(session.sentiment_history) >= 2:
        last_two = session.sentiment_history[-2:]
        if all(s <= 0.3 for s in last_two):
            ticket.escalation_reason = "consecutive_low_sentiment"
            ticket.sentiment = session.sentiment_history[-1]
            print(f"   ⚠️  Consecutive low sentiment detected: {last_two}")

    print(f"   Intents: {ticket.intents}")
    print(f"   Sentiment: {ticket.sentiment}")
    print(f"   Sentiment history: {[round(s, 2) for s in session.sentiment_history]}")
    print(f"   Urgency: {ticket.urgency}")
    print(f"   Follow-up: {ticket.is_follow_up}")
    print(f"   Escalation trigger: {ticket.escalation_reason or 'None'}")

    # Step 6: Generate response (pass conversation history for context)
    history_for_llm = session.conversation_history if len(session.conversation_history) > 1 else None
    print("\n💬 Generating response...")
    ticket = await generate_response(ticket, history_for_llm)

    # Step 7: Append agent response to conversation history
    if ticket.response and not ticket.response.startswith("ESCALATE:"):
        session.conversation_history.append({
            "role": "assistant",
            "content": ticket.response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Step 8: Update resolution state and handle escalation
    if ticket.status == "escalated":
        session.resolution_state = "escalated"
        record_escalation(ticket)
        print(f"\n🚨 ESCALATED — Reason: {ticket.escalation_reason}")
    else:
        session.resolution_state = "resolved"
        print(f"\n✅ RESOLVED (status={ticket.status})")
        if ticket.bug_ticket_id:
            print(f"   🎫 Bug ticket created: {ticket.bug_ticket_id}")

    # Step 9: Persist session
    session_store.update(session)

    # Step 10: Print response
    print(f"\n{'─'*60}")
    print("📝 RESPONSE:")
    print(f"{'─'*60}")
    print(ticket.response)
    print(f"{'─'*60}")

    # Step 11: Summary
    print(f"\n📊 Summary:")
    print(f"   Ticket ID: {ticket.id}")
    print(f"   Status: {ticket.status}")
    print(f"   Escalation reason: {ticket.escalation_reason or 'N/A'}")
    print(f"   Bug ticket: {ticket.bug_ticket_id or 'N/A'}")
    print(f"   Response length: {len(ticket.response)} chars")
    if ticket.channel == "whatsapp" and len(ticket.response) > 300:
        print(f"   ⚠️  WhatsApp response exceeds 300-char guideline!")
    
    # Step 12: Persist to Database
    latency_ms = int((time.time() - start_time) * 1000)
    try:
        db_result = await save_interaction(ticket, session, latency_ms)
        print(f"\n💾 Database: customer_id={db_result['customer_id'][:8]}... "
              f"conversation_id={db_result['conversation_id'][:8]}...")
    except Exception as e:
        print(f"\n⚠️  DB save failed (non-fatal): {e}")

    print(f"\n{'='*60}\n")

    return ticket


# ---------------------------------------------------------------------------
# 8. Conversation Runner
# ---------------------------------------------------------------------------
async def run_conversation(messages: list[dict]):
    """Process a list of message dicts sequentially through the same session.
    Prints results after each turn and a final session summary."""

    print(f"{'#'*60}")
    print(f"  Starting conversation with {len(messages)} message(s)")
    print(f"{'#'*60}\n")

    results = []
    for i, raw_msg in enumerate(messages, 1):
        print(f"\n{'*'*60}")
        print(f"  TURN {i}/{len(messages)}")
        print(f"  Message: {raw_msg['content']}")
        print(f"{'*'*60}\n")

        ticket = await process_ticket(raw_msg)
        results.append(ticket)

    # Final session summary
    customer_id = results[0].customer_id if results else "unknown"
    session = session_store.get(customer_id)

    print(f"\n{'#'*60}")
    print(f"  CONVERSATION COMPLETE")
    print(f"{'#'*60}")
    if session:
        print(f"  Customer: {session.customer_name} ({session.customer_id})")
        print(f"  Channel: {session.channel}")
        print(f"  Total turns: {session.ticket_count}")
        print(f"  Resolution state: {session.resolution_state}")
        print(f"  Sentiment trajectory: {[round(s, 2) for s in session.sentiment_history]}")
        print(f"  Avg sentiment: {round(sum(session.sentiment_history)/len(session.sentiment_history), 2) if session.sentiment_history else 'N/A'}")
    print(f"{'#'*60}\n")

    return results


# ---------------------------------------------------------------------------
# 9. Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Multi-turn conversation test
    conversation = [
        {
            "channel": "whatsapp",
            "content": "hi, how do i set up automations?",
            "metadata": {"wa_id": "15550000000", "name": "Sara"},
        },
        {
            "channel": "whatsapp",
            "content": "i tried that but it still doesnt work :(",
            "metadata": {"wa_id": "15550000000", "name": "Sara"},
        },
        {
            "channel": "whatsapp",
            "content": "nothing is working this is so frustrating!!",
            "metadata": {"wa_id": "15550000000", "name": "Sara"},
        },
    ]

    asyncio.run(run_conversation(conversation))
