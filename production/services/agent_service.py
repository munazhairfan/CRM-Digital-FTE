# production/services/agent_service.py
import os
import uuid
from datetime import datetime, timezone
from openai import AsyncOpenAI
from agents import Agent, Runner, set_default_openai_key, set_default_openai_client, set_tracing_disabled
from production.agents.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
)
from production.agents.classifier import classify_message, classify_message_tool
from production.clients.session_store import session_store
from production.repositories.interaction_repo import save_interaction
from production.prompts import generate_empathy_holding
from production.services.memory_service import get_customer_context

# Point OpenAI SDK to Groq's API
groq_key = os.environ.get("GROQ_API_KEY", "")
groq_client = AsyncOpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")

# Override the default client globally so Runner uses Groq
set_default_openai_key(groq_key)
set_default_openai_client(groq_client)
set_tracing_disabled(True)

# Use Chat Completions API (Groq doesn't support Responses API)
from agents import OpenAIChatCompletionsModel
groq_model = OpenAIChatCompletionsModel(
    model="openai/gpt-oss-20b",
    openai_client=groq_client,
)

# Main Production Agent
# Note: Tools are available but Llama 3.3 on Groq has function calling limitations.
# The classifier runs separately and provides structured context.
# The agent responds based on product knowledge in its instructions.
customer_success_agent = Agent(
    name="FlowForge Customer Success FTE",
    instructions=(
        "You are a professional, helpful Customer Success agent for FlowForge. "
        "FlowForge is a project management SaaS for teams of 5-200 people. "
        "Pricing: Free (10 users, 5 boards), Pro ($12/user/month, unlimited boards + AI insights), Enterprise (SSO, SLA). "
        "Key how-tos: invite members (Settings > Members > Invite), create board (sidebar + > New Board), "
        "automations (board > Automations tab), export data (board menu > Export > CSV/JSON), "
        "connect Slack (Integrations page > Connect Slack). "
        "Limitations: no built-in time tracking (use Toggl), no native mobile app (PWA available), "
        "no white-labeling in Pro tier. "
        "Use 'we' and 'you' — never 'I'. "
        "Be friendly but professional. Short responses for WhatsApp, structured for email. "
        "Always end with a clear next step or question. "
        "NEVER say 'As an AI I can't...', competitor names, or 'I'm sorry for the inconvenience'. "
        "If the message is a bug report, acknowledge it and ask for one clarifying detail. "
        "If pricing, refund, compliance, or SSO is mentioned, say 'ESCALATE: <reason>'."
    ),
    model=groq_model,
)


async def process_customer_message(raw_message: dict, start_time: float = None) -> dict:
    """
    Full production pipeline:
    1. Classify
    2. Create ticket (if needed)
    3. Run main agent with tools
    4. Return final response + status
    """
    if start_time is None:
        import time
        start_time = time.time()
    # Step 1: Classify (your logic)
    c = await classify_message(
        channel=raw_message["channel"],
        content=raw_message["content"],
        metadata=raw_message.get("metadata", {})
    )

    # Track session sentiment for consecutive low detection
    customer_id = raw_message.get("metadata", {}).get("wa_id") or raw_message.get("metadata", {}).get("customer_email", raw_message.get("customer_name", "unknown"))
    session = session_store.get_or_create(
        customer_id=customer_id,
        customer_name=raw_message.get("customer_name", "Customer"),
        channel=raw_message["channel"]
    )
    session.sentiment_history.append(c["sentiment"])
    session.updated_at = datetime.now(timezone.utc).isoformat()

    # Check consecutive low sentiment: last 2 scores both ≤ 0.3
    if len(session.sentiment_history) >= 2:
        last_two = session.sentiment_history[-2:]
        if all(s <= 0.3 for s in last_two):
            c["escalation_trigger"] = "consecutive_low_sentiment"
            ticket_context_update = {
                "escalation_reason": "consecutive_low_sentiment",
            }
            c.update(ticket_context_update)

    # Prepare ticket context for the agent
    ticket_context = {
        "id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "channel": raw_message["channel"],
        "customer_id": customer_id,
        "customer_name": raw_message.get("customer_name", "Customer"),
        "content": raw_message["content"],
        "intents": c["intents"],
        "sentiment": c["sentiment"],
        "urgency": c["urgency"],
        "is_follow_up": c["is_follow_up"],
        "escalation_reason": c["escalation_trigger"],
        "metadata": raw_message.get("metadata", {}),
    }

    # Check for pre-triggered escalation (consecutive sentiment, etc.)
    if c["escalation_trigger"]:
        ticket_context["status"] = "escalated"
        ticket_context["response"] = generate_empathy_holding(ticket_context)
        return {
            "ticket_id": "TKT-XXXXXX",
            "response": ticket_context["response"],
            "status": "escalated",
            "escalation_reason": c["escalation_trigger"],
            "sentiment": c["sentiment"],
        }

    # Step 1.5: Fetch Memory Context (Cross-channel history from last 7 days)
    history_context = ""
    if customer_id and customer_id != "unknown":
        history_context = await get_customer_context(customer_id)

    # Step 2: Run the main agent with classification context in the prompt
    channel_hint = ""
    if raw_message["channel"] == "whatsapp":
        channel_hint = " Respond in a short, warm, conversational style (under 300 chars)."
    elif raw_message["channel"] == "email":
        channel_hint = " Respond with a formal greeting, structured body, and professional sign-off."

    prompt = (
        f"Customer: {raw_message.get('customer_name', 'Customer')}\n"
        f"Channel: {raw_message['channel']}\n"
        f"Intents: {', '.join(c['intents'])}\n"
        f"Sentiment: {c['sentiment']}\n"
        f"Urgency: {c['urgency']}\n"
        f"Follow-up: {c['is_follow_up']}\n"
        f"Escalation: {c['escalation_trigger'] or 'None'}\n"
        f"\n{history_context}\n"
        f"{channel_hint}\n\n"
        f"Message: {raw_message['content']}"
    )

    result = await Runner.run(customer_success_agent, prompt)

    # Step 3: If agent decided to escalate
    output = str(result.final_output)
    if "ESCALATE" in output.upper():
        ticket_context["status"] = "escalated"
        ticket_context["response"] = generate_empathy_holding(ticket_context)
    else:
        ticket_context["status"] = "resolved"
        ticket_context["response"] = output

    # Step 4: Persist to Database
    import time
    latency_ms = int((time.time() - start_time) * 1000)
    try:
        db_result = await save_interaction(ticket_context, None, latency_ms)
        ticket_context["db_ticket_number"] = db_result.get("ticket_number")
    except Exception as e:
        print(f"⚠️ DB save failed (non-fatal): {e}")

    return {
        "ticket_id": ticket_context.get("db_ticket_number", "TKT-XXXXXX"),
        "response": ticket_context["response"],
        "status": ticket_context["status"],
        "escalation_reason": ticket_context.get("escalation_reason"),
        "sentiment": c["sentiment"],
    }