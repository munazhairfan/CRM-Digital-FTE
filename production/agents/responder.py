# production/agents/responder.py
from agents import Agent
from production.agents.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response
)
from production.repositories.prompt_builder import build_system_prompt
from prototype import generate_empathy_holding

agent = Agent(
    name="FlowForge Customer Success Agent",
    instructions="You are a helpful, professional Customer Success agent.",
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
    ],
    model="groq/llama3-70b-8192",   # change to your preferred Groq model
)


async def run_agent(raw_message: dict) -> dict:
    """Main entry point for the production agent."""
    # This will be expanded in the next step with ingestion + classifier
    ticket = {
        "channel": raw_message["channel"],
        "customer_name": raw_message.get("customer_name", "Customer"),
        "content": raw_message["content"],
        "intents": [],
        "sentiment": 0.5,
        "urgency": "normal",
        "is_follow_up": False,
        "escalation_reason": "",
    }

    result = await agent.run(
        messages=[{"role": "user", "content": raw_message["content"]}],
        context={"ticket": ticket}
    )

    return {
        "ticket_id": "TKT-XXXXXX",  # will come from create_ticket
        "response": result.output,
        "status": "resolved" if not result.escalated else "escalated",
    }