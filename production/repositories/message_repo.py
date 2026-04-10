"""
production/repositories/message_repo.py
Stores inbound/outbound messages and generates conversation summaries.
"""

import json
import os
import uuid
from typing import Optional, List

from openai import AsyncOpenAI
from production.clients.db_client import DatabaseClient

# Reuse project's LLM client configuration (Groq)
_llm_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
SUMMARY_MODEL = "openai/gpt-oss-20b"


class MessageRepository:
    async def save_message(
        self,
        conversation_id: str,
        channel: str,
        direction: str,
        role: str,
        content: str,
        sentiment: Optional[float] = None,
        latency_ms: Optional[int] = None,
        tool_calls: Optional[list] = None,
        channel_message_id: Optional[str] = None,
        delivery_status: str = "delivered",
    ) -> str:
        """Insert a message row and return its id."""
        message_id = uuid.uuid4()
        async with DatabaseClient.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO messages (
                    id, conversation_id, channel, direction, role,
                    content, sentiment, latency_ms, tool_calls,
                    channel_message_id, delivery_status, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, NOW()
                )
                """,
                message_id,
                uuid.UUID(conversation_id),
                channel,
                direction,
                role,
                content,
                sentiment,
                latency_ms,
                json.dumps(tool_calls or []),
                channel_message_id,
                delivery_status,
            )
        return str(message_id)

    async def get_customer_context(
        self,
        customer_id: str,
        days: int = 7,
    ) -> str:
        """
        Build a context string for prompt injection.
        Pulls summaries and recent messages for the last N days.
        """
        async with DatabaseClient.get_connection() as conn:
            # 1. Customer profile
            customer = await conn.fetchrow(
                """
                SELECT name, email, phone,
                       metadata->>'plan_tier' AS plan_tier
                FROM customers
                WHERE id = $1
                """,
                uuid.UUID(customer_id),
            )

            # 2. Recent conversation summaries (last 7 days)
            summaries = await conn.fetch(
                """
                SELECT summary, channel, created_at
                FROM conversation_summaries
                WHERE customer_id = $1
                  AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 5
                """,
                uuid.UUID(customer_id),
            )

            # 3. Last 5 messages across all recent conversations
            recent_messages = await conn.fetch(
                """
                SELECT m.role, m.content, m.channel, m.created_at,
                       m.sentiment
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.customer_id = $1
                  AND m.created_at > NOW() - INTERVAL '7 days'
                ORDER BY m.created_at DESC
                LIMIT 5
                """,
                uuid.UUID(customer_id),
            )

        # Build context string
        lines = []

        if customer:
            name = customer["name"] or "Unknown"
            plan = customer["plan_tier"] or "unknown"
            lines.append(f"Customer Profile: {name} ({plan} plan)")

        if summaries:
            lines.append("\n### Past Conversation Summaries (last 7 days):")
            for s in summaries:
                date_str = s["created_at"].strftime("%b %d")
                lines.append(f"- [{date_str} via {s['channel']}] {s['summary']}")

        if recent_messages:
            lines.append("\n### Recent Messages:")
            for m in reversed(recent_messages):
                role = "Customer" if m["role"] == "customer" else "Agent"
                date_str = m["created_at"].strftime("%b %d %H:%M")
                content_preview = m["content"][:120]
                if len(m["content"]) > 120:
                    content_preview += "..."
                lines.append(f"- [{date_str}] {role}: {content_preview}")

        return "\n".join(lines)

    async def summarize_and_store(
        self,
        conversation_id: str,
        customer_id: str,
        channel: str,
    ) -> Optional[str]:
        """Generate a summary after resolution/escalation."""
        async with DatabaseClient.get_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                """,
                uuid.UUID(conversation_id),
            )

        if not rows:
            return None

        transcript_lines = [
            f"{'Customer' if r['role'] == 'customer' else 'Agent'}: {r['content'][:300]}"
            for r in rows
        ]
        transcript = "\n".join(transcript_lines)

        try:
            resp = await _llm_client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Summarize this customer support conversation in ONE sentence. "
                            "Include: the main issue, what was tried, and the outcome.\n\n"
                            f"Transcript:\n{transcript}"
                        ),
                    }
                ],
                temperature=0,
                max_tokens=120,
            )
            summary = resp.choices[0].message.content.strip()
        except Exception:
            summary = "Summary unavailable."

        async with DatabaseClient.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_summaries
                    (id, conversation_id, customer_id, channel, summary, created_at)
                VALUES
                    ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (conversation_id) DO UPDATE
                SET summary = EXCLUDED.summary
                """,
                uuid.uuid4(),
                uuid.UUID(conversation_id),
                uuid.UUID(customer_id),
                channel,
                summary,
            )

        return summary
