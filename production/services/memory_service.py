"""
FlowForge FTE — Memory Service
Retrieves customer history from PostgreSQL to provide context.
"""
import os
import asyncpg
from datetime import datetime, timedelta, timezone
from production.clients.db_client import DatabaseClient


async def get_customer_context(identifier: str) -> str:
    """
    Retrieves the last 5 interactions from the last 7 days for a specific customer.
    
    Args:
        identifier: Can be a raw phone number, email, or name (from the incoming message).
    """
    # 1. Validate ID
    if not identifier or identifier == "unknown":
        return "No history available."
        
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    
    try:
        async with DatabaseClient.get_connection() as conn:
            # Step A: Resolve the raw identifier to a Customer UUID
            # We check email, phone, and name to be robust
            customer_row = await conn.fetchrow(
                """
                SELECT id FROM customers 
                WHERE email = $1 OR phone = $2 OR name = $3
                LIMIT 1
                """,
                identifier if "@" in identifier else None,
                identifier if identifier.isdigit() or identifier.startswith("+") else None,
                identifier
            )

            if not customer_row:
                return "No recent interactions found."

            customer_uuid = customer_row['id']

            # Step B: Fetch history using the actual UUID
            rows = await conn.fetch(
                """
                SELECT 
                    m.content, 
                    m.role, 
                    m.created_at,
                    c.initial_channel
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.customer_id = $1 AND m.created_at > $2
                ORDER BY m.created_at DESC
                LIMIT 5;
                """,
                customer_uuid, cutoff
            )
            
            if not rows:
                return "No recent interactions found."

            history = ["**Recent History:**"]
            for row in rows:
                time_str = row['created_at'].strftime("%H:%M")
                history.append(
                    f"- {time_str} [{row['initial_channel']}] {row['role']}: {row['content'][:50]}..."
                )
            
            return "\n".join(history)

    except Exception:
        # Return a clean fallback so the LLM doesn't get confused by error text
        return ""
