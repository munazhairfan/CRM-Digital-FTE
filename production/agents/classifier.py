# production/agents/classifier.py
"""Improved classifier with few-shot examples and Groq backend."""
from typing import Any
import json
import os
from openai import AsyncOpenAI
from production.prompts import CLASSIFY_PROMPT_TEMPLATE, _apply_do_not_escalate_overrides, _llm_with_retry
from agents import function_tool

# Groq client (OpenAI-compatible endpoint)
_groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1",
)
GROQ_MODEL = "openai/gpt-oss-20b"

# Enhanced prompt with few-shot examples for better accuracy
ENHANCED_PROMPT = CLASSIFY_PROMPT_TEMPLATE + """

Few-shot examples for accuracy:
1. "how do i invite team members?" → intents: ["how_to"], is_follow_up: false, escalation: ""
2. "Still can't invite team members. I tried the steps you gave yesterday." → intents: ["how_to"], is_follow_up: true, escalation: ""
3. "I can't access my account, session expired" → intents: ["account_access"], is_follow_up: false, escalation: "Account access / security / SSO / data export"
4. "this product is the worst ever!! nothing works" → intents: ["bug_report"], sentiment: 0.1, escalation: "" (bug_report with strong language is NOT escalated — agent handles it)
5. "Can I export all my tasks as CSV? Also, how do I set up recurring tasks every Monday?" → intents: ["how_to", "how_to"], is_follow_up: false, escalation: ""
6. "thanks for the help earlier. everything is good now" → intents: ["appreciation"], sentiment: 0.9, is_follow_up: false, escalation: ""
"""


async def classify_message(
    channel: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the classification logic with few-shot examples.
    Returns structured output for the main agent.
    """
    if metadata is None:
        metadata = {}

    prompt = ENHANCED_PROMPT.replace("{{channel}}", channel)\
                            .replace("{{content}}", content)\
                            .replace("{{metadata}}", json.dumps(metadata))

    resp = await _llm_with_retry(
        lambda: _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
    )

    result = json.loads(resp.choices[0].message.content.strip())

    intents = result.get("intents", ["general_inquiry"])
    escalation_trigger = result.get("escalation_trigger", "")

    # Apply your override logic
    class _FakeTicket:
        def __init__(self, i, r, c=""):
            self.intents = i
            self.escalation_reason = r
            self.content = c  # Pass content so override logic can check for extreme keywords

    fake_ticket = _FakeTicket(intents, escalation_trigger, content)
    _apply_do_not_escalate_overrides(fake_ticket)
    escalation_trigger = fake_ticket.escalation_reason

    return {
        "intents": intents,
        "sentiment": float(result.get("sentiment", 0.5)),
        "urgency": result.get("urgency", "normal"),
        "is_follow_up": bool(result.get("is_follow_up", False)),
        "escalation_trigger": escalation_trigger,
    }


# Wrapped version for use as an agent tool (string return avoids strict schema issues)
@function_tool
async def classify_message_tool(
    channel: str,
    content: str,
    metadata_json: str = "",
) -> str:
    """Classify a customer message. Returns JSON string."""
    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
    except (json.JSONDecodeError, TypeError):
        metadata = {}

    result = await classify_message(channel, content, metadata)
    return json.dumps(result)
